from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, join_room, leave_room, send
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secret123"
socketio = SocketIO(app)

DB = "chat.db"

# إنشاء قاعدة البيانات والجداول إذا ما كانت موجودة
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
        c.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT,
            user TEXT,
            content TEXT,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()

init_db()

# الصفحة الرئيسية: دخول مدير أو زائر
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
    return """
    <h2>دخول الزوار</h2>
    <form method="post">
      <input name="name" placeholder="اكتب اسمك">
      <button name="login_user">دخول</button>
    </form>
    <h2>دخول المدير</h2>
    <form method="post">
      <input name="email" placeholder="الإيميل">
      <input name="password" type="password" placeholder="كلمة المرور">
      <button name="login_admin">دخول</button>
    </form>
    <h2>تسجيل مدير جديد</h2>
    <form method="post">
      <input name="name" placeholder="الاسم">
      <input name="email" placeholder="الإيميل">
      <input name="password" placeholder="كلمة المرور">
      <button name="register_admin">تسجيل</button>
    </form>
    """

# لوحة المدير: إنشاء غرف
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
    html = "<h2>لوحة المدير</h2><ul>"
    for r in rooms:
        html += f"<li>{r[1]}</li>"
    html += "</ul>"
    html += """
    <form method="post">
      <input name="room" placeholder="اسم الغرفة">
      <button>إضافة غرفة</button>
    </form>
    """
    return html

# قائمة الغرف للزوار
@app.route("/rooms")
def rooms():
    if "user" not in session:
        return redirect("/")
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM rooms")
        rooms = c.fetchall()
    html = "<h2>اختر غرفة</h2><ul>"
    for r in rooms:
        html += f"<li><a href='/chat/{r[1]}'>{r[1]}</a></li>"
    html += "</ul>"
    return html

# صفحة الدردشة
@app.route("/chat/<room>")
def chat(room):
    if "user" not in session:
        return redirect("/")
    return f"""
    <h2>الغرفة: {room}</h2>
    <div id='messages'></div>
    <input id='msg' placeholder='اكتب رسالتك'>
    <button onclick='sendMsg()'>إرسال</button>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <script>
      var socket = io();
      var room = "{room}";
      var user = "{session['user']}";
      socket.emit("join", {{room:room, user:user}});
      socket.on("message", function(data){{
        var div = document.getElementById("messages");
        div.innerHTML += "<p>"+data+"</p>";
      }});
      function sendMsg(){{
        var msg = document.getElementById("msg").value;
        socket.emit("chat", {{room:room, user:user, msg:msg}});
        document.getElementById("msg").value="";
      }}
    </script>
    """

# أحداث سوكيت
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
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
