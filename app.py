from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, send
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secret123")
socketio = SocketIO(app)

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("rooms"))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    if username:
        session["username"] = username
        return redirect(url_for("rooms"))
    return redirect(url_for("index"))

@app.route("/rooms")
def rooms():
    if "username" not in session:
        return redirect(url_for("index"))
    return render_template("rooms.html", username=session["username"])

@app.route("/chat/<room>")
def chat(room):
    if "username" not in session:
        return redirect(url_for("index"))
    return render_template("chat.html", room=room, username=session["username"])

@app.route("/admin")
def admin():
    return render_template("admin.html")

@socketio.on("join")
def on_join(data):
    username = data["username"]
    room = data["room"]
    join_room(room)
    send(f"{username} دخل الغرفة", to=room)

@socketio.on("message")
def on_message(data):
    room = data["room"]
    msg = f"{data['username']}: {data['msg']}"
    send(msg, to=room)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
