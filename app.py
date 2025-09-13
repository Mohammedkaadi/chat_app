from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, join_room, send
import sqlite3, os

app = Flask(__name__)
app.secret_key = "secret123"
socketio = SocketIO(app)

DB = "chat.db"

def init_db():
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            password TEXT,
            role TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            created_by TEXT
        )""")
        conn.commit()
init_db()

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        if "login_admin" in request.form:
            email = request.form["email"]
            password = request.form["password"]
            with sqlite3.connect(DB) as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE email=? AND password=? AND role='admin'", (email, password))
                admin = c.fetchone()
                if admin:
                    session["user"] = admin[1]
                    session["role"] = "admin"
                    return redirect(url_for("admin"))
        elif "login_user" in request.form:
            name = request.form["name"]
            session["user"] = name
            session["role"] = "user"
            return redirect(url_for("rooms"))
        elif "register_admin" in request.form:
            name = request.form["name"]
            email = request.form["email"]
            password = request.form["password"]
            with sqlite3.connect(DB) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                          (name,email,password,"admin"))
                conn.commit()
            return "تم تسجيل المدير، ارجع وسجل دخولك."
    return render_template("index.html")

@app.route("/admin", methods=["GET","POST"])
def admin():
    if "user" not in session or session["role"] != "admin":
        return redirect("/")
    if request.method == "POST":
        room_name = request.form["room"]
        with sqlite3.connect(DB) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO rooms (name,created_by) VALUES (?,?)",
                      (room_name, session["user"]))
            conn.commit()
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM rooms")
        rooms = c.fetchall()
    return render_template("admin.html", rooms=rooms)

@app.route("/rooms")
def rooms():
    if "user" not in session:
        return redirect("/")
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM rooms")
        rooms = c.fetchall()
    return render_template("rooms.html", rooms=rooms)

@app.route("/chat/<room>")
def chat(room):
    if "user" not in session:
        return redirect("/")
    return render_template("chat.html", room=room, user=session["user"])

@socketio.on("join")
def on_join(data):
    room = data["room"]
    user = data["user"]
    join_room(room)
    send(f"{user} دخل الغرفة", to=room)

@socketio.on("chat")
def on_chat(data):
    room = data["room"]
    user = data["user"]
    msg = data["msg"]
    send(f"{user}: {msg}", to=room)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
