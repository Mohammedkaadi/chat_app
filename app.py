import os, sqlite3, secrets
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
from datetime import datetime

BASE = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE, "shop.db")
UPLOAD_FOLDER = os.path.join(BASE, "static", "uploads")
ALLOWED = {"png","jpg","jpeg","webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
bcrypt = Bcrypt(app)

ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE, password TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY, title TEXT, description TEXT, price REAL, qty INTEGER, image TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY, user_id INTEGER, total REAL, address TEXT, created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, qty INTEGER, price REAL
    )""")
    conn.commit()
    conn.close()

init_db()

def query_db(q, args=(), one=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(q, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def allowed_file(fn):
    return "." in fn and fn.rsplit(".",1)[1].lower() in ALLOWED

@app.route("/")
def index():
    prods = query_db("SELECT id,title,description,price,qty,image FROM products")
    return render_template("index.html", products=prods)

@app.route("/product/<int:pid>")
def product(pid):
    p = query_db("SELECT id,title,description,price,qty,image FROM products WHERE id=?", (pid,), one=True)
    if not p:
        flash("المنتج غير موجود")
        return redirect(url_for("index"))
    return render_template("product.html", p=p)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        u = request.form["username"].strip()
        e = request.form["email"].strip()
        pw = request.form["password"]
        pw_hash = bcrypt.generate_password_hash(pw).decode("utf-8")
        try:
            query_db("INSERT INTO users (username,email,password) VALUES (?,?,?)", (u,e,pw_hash))
            flash("تم التسجيل بنجاح. يمكنك تسجيل الدخول.")
            return redirect(url_for("login"))
        except Exception:
            flash("اسم المستخدم أو الإيميل مستخدم سابقاً.")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"].strip()
        pw = request.form["password"]
        row = query_db("SELECT id,password FROM users WHERE username=?", (u,), one=True)
        if row and bcrypt.check_password_hash(row[1], pw):
            session["user_id"] = row[0]
            session["username"] = u
            flash("تم تسجيل الدخول")
            return redirect(url_for("index"))
        flash("اسم المستخدم أو كلمة المرور خاطئة")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("تم تسجيل الخروج.")
    return redirect(url_for("index"))

@app.route("/cart")
def cart():
    cart = session.get("cart", {})
    items = []
    total = 0
    for pid, qty in cart.items():
        p = query_db("SELECT id,title,price,image FROM products WHERE id=?", (pid,), one=True)
        if not p: continue
        subtotal = p[2] * qty
        total += subtotal
        items.append({"id":p[0], "title":p[1], "price":p[2], "image":p[3], "qty":qty, "subtotal":subtotal})
    return render_template("cart.html", items=items, total=total)

@app.route("/cart/add/<int:pid>", methods=["POST"])
def add_cart(pid):
    qty = int(request.form.get("qty", 1))
    cart = session.get("cart", {})
    cart[str(pid)] = cart.get(str(pid), 0) + qty
    session["cart"] = cart
    flash("تمت الإضافة إلى السلة")
    return redirect(request.referrer or url_for("index"))

@app.route("/cart/remove/<int:pid>", methods=["POST"])
def remove_cart(pid):
    cart = session.get("cart", {})
    cart.pop(str(pid), None)
    session["cart"] = cart
    flash("تمت الإزالة من السلة")
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET","POST"])
def checkout():
    if "user_id" not in session:
        flash("سجّل الدخول أولاً لإكمال الطلب")
        return redirect(url_for("login"))
    if request.method == "POST":
        addr = request.form.get("address")
        cart = session.get("cart", {})
        if not cart:
            flash("السلة فارغة")
            return redirect(url_for("cart"))
        total = 0
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        created = datetime.utcnow().isoformat()
        cur.execute("INSERT INTO orders (user_id,total,address,created_at) VALUES (?,?,?,?)",
                    (session["user_id"], 0.0, addr, created))
        order_id = cur.lastrowid
        for pid_str, qty in cart.items():
            pid_i = int(pid_str)
            p = query_db("SELECT price,qty FROM products WHERE id=?", (pid_i,), one=True)
            if not p: continue
            price = p[0]
            subtotal = price * qty
            total += subtotal
            cur.execute("INSERT INTO order_items (order_id,product_id,qty,price) VALUES (?,?,?,?)",
                        (order_id, pid_i, qty, price))
            cur.execute("UPDATE products SET qty = qty - ? WHERE id=?", (qty, pid_i))
        cur.execute("UPDATE orders SET total=? WHERE id=?", (total, order_id))
        conn.commit()
        conn.close()
        session["cart"] = {}
        flash("تم إنشاء الطلب بنجاح — خيار الدفع عند التسليم")
        return redirect(url_for("index"))
    return render_template("checkout.html")

@app.route("/admin", methods=["GET","POST"])
def admin_panel():
    # simple admin protection using ADMIN_PASS env var
    if request.method == "POST" and "adminpass" in request.form and request.form.get("adminpass") != os.environ.get("ADMIN_PASS","admin123"):
        flash("كلمة مرور المدير خاطئة")
        return redirect(url_for("admin_panel"))
    if request.method == "POST" and request.form.get("adminpass") == os.environ.get("ADMIN_PASS","admin123") and request.form.get("add_product"):            title = request.form.get("title")
        desc = request.form.get("description")
        price = float(request.form.get("price",0))
        qty = int(request.form.get("qty",0))
        imgfile = request.files.get("image")
        imgname = None
        if imgfile and allowed_file(imgfile.filename):
            fn = secure_filename(imgfile.filename)
            imgname = f"{secrets.token_hex(6)}_{fn}"
            imgfile.save(os.path.join(app.config["UPLOAD_FOLDER"], imgname))
        query_db("INSERT INTO products (title,description,price,qty,image) VALUES (?,?,?,?,?)", (title,desc,price,qty,imgname))
        flash("تم إضافة المنتج") 
        return redirect(url_for("admin_panel"))
    prods = query_db("SELECT id,title,price,qty FROM products")
    return render_template("admin.html", prods=prods)

@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
