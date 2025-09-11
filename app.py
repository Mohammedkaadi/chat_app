from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, join_room, leave_room, send
import uuid, os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecret")
socketio = SocketIO(app)

users = {}
reset_tokens = {}

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("chat"))
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = request.form["password"]
    email = request.form["email"]
    if username in users:
        flash("اسم المستخدم موجود مسبقاً")
    else:
        users[username] = {"password": password, "email": email}
        flash("تم إنشاء الحساب بنجاح! يمكنك تسجيل الدخول الآن.")
    return redirect(url_for("index"))

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    if username in users and users[username]["password"] == password:
        session["username"] = username
        return redirect(url_for("chat"))
    flash("خطأ في اسم المستخدم أو كلمة المرور")
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))

@app.route("/forgot", methods=["POST"])
def forgot_password():
    email = request.form["email"]
    for user, data in users.items():
        if data["email"] == email:
            token = str(uuid.uuid4())
            reset_tokens[token] = user
            flash(f"رابط إعادة التعيين (مؤقت): /reset/{token}")
            return redirect(url_for("index"))
    flash("البريد الإلكتروني غير مسجل")
    return redirect(url_for("index"))

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    if token not in reset_tokens:
        flash("الرابط غير صالح")
        return redirect(url_for("index"))
    if request.method == "POST":
        new_pass = request.form["password"]
        user = reset_tokens[token]
        users[user]["password"] = new_pass
        reset_tokens.pop(token)
        flash("تم تغيير كلمة المرور بنجاح")
        return redirect(url_for("index"))
    return render_template("reset.html", token=token)

@app.route("/chat")
def chat():
    if "username" not in session:
        return redirect(url_for("index"))
    return render_template("chat.html", username=session["username"])

@socketio.on("join")
def on_join(data):
    room = data["room"]
    join_room(room)
    send(f"{session['username']} انضم إلى الغرفة", to=room)

@socketio.on("leave")
def on_leave(data):
    room = data["room"]
    leave_room(room)
    send(f"{session['username']} غادر الغرفة", to=room)

@socketio.on("message")
def on_message(data):
    room = data["room"]
    send({"user": session["username"], "msg": data["msg"]}, to=room)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
