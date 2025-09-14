import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime
import json

app = Flask(__name__, static_folder='static', template_folder='templates')
app.wsgi_app = ProxyFix(app.wsgi_app)
app.secret_key = os.getenv("SECRET_KEY", "change_this_secret")

socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory DB (يمكن تبديلها بقاعدة حقيقية لاحقاً: Mongo/Postgres)
DATA = {
    "users": {},   # username -> {role, banned, name}
    "rooms": {},   # room_id -> {name, country, type, icon, created_at}
    "messages": {} # room_id -> [ {user, text, time}... ]
}

# === Helper functions ===
def now_iso():
    return datetime.utcnow().isoformat()

def ensure_room(room_id):
    if room_id not in DATA["rooms"]:
        DATA["rooms"][room_id] = {
            "name": room_id,
            "country": "عام",
            "type": "public",
            "icon": "/static/img/icons/mic.svg",
            "created_at": now_iso()
        }
        DATA["messages"][room_id] = []

# === Routes ===
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("rooms"))
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    role = request.form.get("role", "guest")
    if not username:
        return redirect(url_for("index"))
    # store user in session and DATA
    session["username"] = username
    session["role"] = role
    DATA["users"][username] = {"role": role, "banned": False, "name": username}
    return redirect(url_for("rooms"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/rooms")
def rooms():
    if "username" not in session:
        # show as visitor page but allow view
        return render_template("rooms.html", username="زائر", rooms=DATA["rooms"])
    return render_template("rooms.html", username=session["username"], rooms=DATA["rooms"])

@app.route("/chat/<room_id>")
def chat(room_id):
    ensure_room(room_id)
    if "username" not in session:
        # allow guest but mark as visitor
        session["username"] = f"زائر_{now_iso()[-6:]}"
        session["role"] = "guest"
    return render_template("chat.html", room=DATA["rooms"][room_id], room_id=room_id, username=session["username"], role=session.get("role","guest"))

@app.route("/admin")
def admin():
    # simple admin guard
    if session.get("role") not in ("admin",):
        return redirect(url_for("index"))
    return render_template("admin.html", rooms=DATA["rooms"], users=DATA["users"])

# API endpoints for admin actions (JSON)
@app.route("/api/rooms", methods=["GET","POST"])
def api_rooms():
    if request.method == "GET":
        return jsonify(DATA["rooms"])
    payload = request.json
    rid = payload.get("id") or payload.get("name")
    DATA["rooms"][rid] = {
        "name": payload.get("name", rid),
        "country": payload.get("country", "عام"),
        "type": payload.get("type", "public"),
        "icon": payload.get("icon", "/static/img/icons/mic.svg"),
        "created_at": now_iso()
    }
    DATA["messages"].setdefault(rid, [])
    return jsonify({"ok": True, "id": rid})

@app.route("/api/users", methods=["GET","POST"])
def api_users():
    if request.method == "GET":
        return jsonify(DATA["users"])
    payload = request.json
    username = payload["username"]
    DATA["users"][username] = {"role": payload.get("role","user"), "banned": payload.get("banned", False), "name": payload.get("name", username)}
    return jsonify({"ok": True})

# === Socket.IO events ===
@socketio.on("connect")
def on_connect():
    user = session.get("username", "زائر")
    app.logger.info(f"Socket connected: {user}")

@socketio.on("join")
def on_join(data):
    room = data.get("room")
    user = session.get("username", data.get("username","زائر"))
    ensure_room(room)
    join_room(room)
    msg = {"user":"system","text": f"{user} دخل الغرفة", "time": now_iso()}
    DATA["messages"][room].append(msg)
    emit("system", msg, to=room)
    emit("joined", {"room":room, "user":user}, to=room)

@socketio.on("leave")
def on_leave(data):
    room = data.get("room")
    user = session.get("username", "زائر")
    leave_room(room)
    msg = {"user":"system","text": f"{user} خرج من الغرفة", "time": now_iso()}
    DATA["messages"][room].append(msg)
    emit("system", msg, to=room)

@socketio.on("chat")
def on_chat(data):
    room = data.get("room")
    text = data.get("text","")
    user = session.get("username", "زائر")
    ensure_room(room)
    message = {"user": user, "text": text, "time": now_iso()}
    DATA["messages"][room].append(message)
    emit("chat", message, to=room)

# simple signaling events for WebRTC (offer/answer/ice)
@socketio.on("webrtc-offer")
def on_offer(data):
    target = data.get("target")
    emit("webrtc-offer", {**data, "from": session.get("username")}, to=target)

@socketio.on("webrtc-answer")
def on_answer(data):
    target = data.get("target")
    emit("webrtc-answer", {**data, "from": session.get("username")}, to=target)

@socketio.on("webrtc-ice")
def on_ice(data):
    target = data.get("target")
    emit("webrtc-ice", {**data, "from": session.get("username")}, to=target)

# Health
@app.route("/health")
def health():
    return "ok"

if __name__ == "__main__":
    # initial seed: create some rooms if not present
    if not DATA["rooms"]:
        DATA["rooms"] = {
            "general": {"name":"الفرقة العامة","country":"عام","type":"public","icon":"/static/img/flags/eg.png","created_at":now_iso()},
            "syria": {"name":"سوريا","country":"سوريا","type":"country","icon":"/static/img/flags/sy.png","created_at":now_iso()},
            "egypt": {"name":"مصر","country":"مصر","type":"country","icon":"/static/img/flags/eg.png","created_at":now_iso()}
        }
        for k in DATA["rooms"]:
            DATA["messages"][k] = []
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
