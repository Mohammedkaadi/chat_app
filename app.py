import os
import socket
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, emit
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_123')

# 🔥 ضبط قاعدة البيانات
db_url = os.environ.get("DATABASE_URL")

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# ----- قاعدة البيانات -----
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)
    room = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# إنشاء قاعدة البيانات (أول مرة فقط)
with app.app_context():
    db.create_all()

# ----- الصفحات -----
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('chat'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username').strip()
    if not username:
        return redirect(url_for('index'))
    session['username'] = username
    return redirect(url_for('chat'))

@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('index'))
    return render_template('chat.html', username=session['username'])

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

# API: جلب رسائل الغرفة
@app.route('/api/messages/<room>')
def get_messages(room):
    msgs = Message.query.filter_by(room=room).order_by(Message.created_at.asc()).all()
    return jsonify([
        {
            "sender": m.sender,
            "content": m.content,
            "created_at": m.created_at.strftime("%H:%M")
        } for m in msgs
    ])

# ----- Socket.IO Events -----
@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    join_room(room)
    emit('system', {"msg": f"{data['username']} دخل الغرفة"}, to=room)

@socketio.on('send_message')
def handle_message(data):
    room = data['room']
    msg = Message(sender=data['username'], room=room, content=data['content'])
    db.session.add(msg)
    db.session.commit()
    emit('new_message', {
        "sender": msg.sender,
        "content": msg.content,
        "created_at": msg.created_at.strftime("%H:%M"),
        "room": room
    }, to=room)

# ----- تشغيل السيرفر -----
if __name__ == '__main__':
    import eventlet
    import eventlet.wsgi

    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
