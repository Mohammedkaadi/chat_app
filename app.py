import os
from flask import Flask, render_template, request, redirect, session, jsonify
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO, emit
import sqlite3
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret')
bcrypt = Bcrypt(app)
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=True)

DB = 'chat.db'

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        timestamp TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

def query_db(query, args=(), one=False):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/chat')
    return render_template('index.html')

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('chat.html', username=session.get('username'))

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username','').strip()
    email = data.get('email','').strip()
    password = data.get('password','')
    if not username or not email or not password:
        return 'مطلوب تعبئة جميع الحقول', 400
    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    try:
        query_db('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', (username, email, pw_hash))
        return 'تم إنشاء الحساب', 200
    except Exception as e:
        return 'اسم المستخدم أو الإيميل مستخدم سابقاً', 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username','').strip()
    password = data.get('password','')
    if not username or not password:
        return 'مطلوب اسم المستخدم وكلمة المرور', 400
    row = query_db('SELECT id, password FROM users WHERE username=?', (username,), one=True)
    if row and bcrypt.check_password_hash(row[1], password):
        session['user_id'] = row[0]
        session['username'] = username
        return 'تم تسجيل الدخول', 200
    return 'خطأ في بيانات الدخول', 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/recent_messages')
def recent_messages():
    rows = query_db('SELECT messages.message, messages.timestamp, users.username FROM messages JOIN users ON messages.user_id = users.id ORDER BY messages.id DESC LIMIT 50')
    msgs = [{'user': r[2], 'msg': r[0], 'time': r[1]} for r in rows]
    msgs.reverse()
    return jsonify(msgs)

@socketio.on('send_message')
def handle_send_message(data):
    if 'user_id' not in session:
        emit('error', {'msg': 'unauthorized'})
        return
    msg = data.get('msg','').strip()
    if not msg:
        return
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    query_db('INSERT INTO messages (user_id, message, timestamp) VALUES (?, ?, ?)', (session['user_id'], msg, timestamp))
    payload = {'user': session.get('username'), 'msg': msg, 'time': timestamp}
    emit('receive_message', payload, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Use eventlet/gevent in production. socketio.run will pick eventlet if installed.
    socketio.run(app, host='0.0.0.0', port=port)
