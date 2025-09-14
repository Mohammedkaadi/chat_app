import os
from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, leave_room, send

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///chat.db")
db = SQLAlchemy(app)
socketio = SocketIO(app)

# ----------------------
# Models
# ----------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=False, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

# ----------------------
# Routes
# ----------------------
@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    rooms = Room.query.all()
    return render_template("index.html", username=session["username"], rooms=rooms)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        user = User(username=username)
        db.session.add(user)
        db.session.commit()
        session["username"] = username
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/setup-admin", methods=["GET", "POST"])
def setup_admin():
    # السماح بإنشاء مدير واحد فقط
    if User.query.filter_by(is_admin=True).first():
        return "تم إنشاء المدير مسبقاً ✅"

    if request.method == "POST":
        email = request.form["email"]
        admin = User(username=email, is_admin=True)
        db.session.add(admin)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("setup_admin.html")

# ----------------------
# SocketIO events
# ----------------------
@socketio.on("join")
def on_join(data):
    username = data["username"]
    room = data["room"]
    join_room(room)
    send(f"{username} دخل الغرفة.", to=room)


@socketio.on("leave")
def on_leave(data):
    username = data["username"]
    room = data["room"]
    leave_room(room)
    send(f"{username} غادر الغرفة.", to=room)


@socketio.on("message")
def handle_message(data):
    send(data["msg"], to=data["room"])

# ----------------------
# Main
# ----------------------
if __name__ == "__main__":
    # 🟢 هذا هو التعديل المهم
    with app.app_context():
        db.create_all()

    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
