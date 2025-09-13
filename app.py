from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, emit
import sqlite3, hashlib

app = Flask(__name__)
app.secret_key = "supersecret"
socketio = SocketIO(app, cors_allowed_origins="*")
DB = "chat.db"

def init_db():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT, status TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS rooms(id INTEGER PRIMARY KEY, name TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, room TEXT, user TEXT, text TEXT)")
        cur.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
        if cur.fetchone()[0] == 0:
            h = hashlib.sha256("admin123".encode()).hexdigest()
            cur.execute("INSERT INTO users(username,password,role,status) VALUES(?,?,?,?)",("admin",h,"admin","متصل"))
            con.commit()

def is_admin():
    return session.get("role") == "admin"

@app.route('/')
def index():
    if "user" in session:
        return redirect(url_for("rooms"))
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form.get("password")
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        if row:
            if row[3] == "admin":
                h = hashlib.sha256(password.encode()).hexdigest()
                if h == row[2]:
                    session["user"], session["role"] = username, "admin"
                    return redirect(url_for("rooms"))
            else:
                session["user"], session["role"] = username, "user"
                return redirect(url_for("rooms"))
        else:
            cur.execute("INSERT INTO users(username,password,role,status) VALUES(?,?,?,?)",(username,"","user","متصل"))
            con.commit()
            session["user"], session["role"] = username, "user"
            return redirect(url_for("rooms"))
    return "خطأ تسجيل الدخول"

@app.route("/rooms")
def rooms():
    if "user" not in session: return redirect("/")
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM rooms")
        rooms = cur.fetchall()
    return render_template("rooms.html", rooms=rooms, user=session["user"], role=session["role"])

@app.route("/admin", methods=["GET","POST"])
def admin():
    if not is_admin(): return redirect("/")
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        if request.method=="POST":
            roomname = request.form["room"]
            cur.execute("INSERT INTO rooms(name) VALUES(?)",(roomname,))
            con.commit()
        cur.execute("SELECT * FROM rooms")
        rooms = cur.fetchall()
    return render_template("admin.html", rooms=rooms)

@app.route("/chat/<room>")
def chat(room):
    if "user" not in session: return redirect("/")
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("SELECT user,text FROM messages WHERE room=?",(room,))
        messages = cur.fetchall()
    return render_template("chat.html", room=room, messages=messages, user=session["user"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

online_users = {}

@socketio.on("join")
def on_join(data):
    room = data["room"]; user = session.get("user")
    join_room(room)
    online_users[user] = room
    emit("status", {"msg":f"{user} انضم", "user":user}, room=room)

@socketio.on("leave")
def on_leave(data):
    room = data["room"]; user = session.get("user")
    leave_room(room)
    online_users.pop(user,None)
    emit("status", {"msg":f"{user} غادر", "user":user}, room=room)

@socketio.on("message")
def on_message(data):
    room = data["room"]; msg = data["msg"]; user = session.get("user")
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.execute("INSERT INTO messages(room,user,text) VALUES(?,?,?)",(room,user,msg))
        con.commit()
    emit("message", {"user":user,"msg":msg}, room=room)

@socketio.on("get_users")
def get_users(data):
    room = data["room"]
    users = [u for u,r in online_users.items() if r==room]
    emit("users", {"users":users})

if __name__ == "__main__":
    init_db()
    socketio.run(app, host="0.0.0.0", port=5000)
