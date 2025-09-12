from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "changeme"

# بيانات مؤقتة
products = []
users = {"admin": {"password": "admin123"}}
cart = []

@app.route("/")
def home():
    return render_template("index.html", products=products)

@app.route("/product/<int:pid>")
def product(pid):
    p = next((x for x in products if x["id"] == pid), None)
    return render_template("product.html", product=p)

@app.route("/cart")
def view_cart():
    return render_template("cart.html", cart=cart)

@app.route("/add_to_cart/<int:pid>")
def add_to_cart(pid):
    p = next((x for x in products if x["id"] == pid), None)
    if p:
        cart.append(p)
        flash("✅ تمت إضافة المنتج إلى السلة")
    return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        if u in users and users[u]["password"] == p:
            flash("تم تسجيل الدخول بنجاح ✅")
            return redirect(url_for("admin"))
        else:
            flash("❌ اسم المستخدم أو كلمة المرور غير صحيحة")
    return render_template("login.html")

@app.route("/admin")
def admin():
    return render_template("admin.html", products=products)

@app.route("/admin/add", methods=["POST"])
def add_product():
    name = request.form.get("name")
    price = request.form.get("price")
    desc = request.form.get("description")

    products.append({
        "id": len(products) + 1,
        "name": name,
        "price": price,
        "desc": desc,
        "image": "/static/placeholder.png"
    })
    flash("✅ تمت إضافة المنتج بنجاح")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
