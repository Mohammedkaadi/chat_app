from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send
import sqlite3, os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY","change_me_please")
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

DB = os.path.join(os.path.dirname(__file__),'chat.db')

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
            desc TEXT,
            flag TEXT,
            created_by TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT,
            user TEXT,
            role TEXT,
            content TEXT,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()

init_db()

@app.route('/', methods=['GET','POST'])
def index():
    # register admin / login admin / guest login
    if request.method == 'POST':
        if 'register_admin' in request.form:
            name = request.form.get('name','').strip()
            email = request.form.get('email','').strip()
            password = request.form.get('password','').strip()
            if name and email and password:
                with sqlite3.connect(DB) as conn:
                    c = conn.cursor()
                    c.execute('INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)', (name,email,password,'admin'))
                    conn.commit()
                    return render_template('index.html', message='تم تسجيل المدير. سجل الدخول الآن.')
        if 'login_admin' in request.form:
            email = request.form.get('email','').strip()
            password = request.form.get('password','').strip()
            with sqlite3.connect(DB) as conn:
                c = conn.cursor()
                c.execute('SELECT * FROM users WHERE email=? AND password=? AND role="admin"', (email,password))
                admin = c.fetchone()
                if admin:
                    session['user'] = admin[1]
                    session['role'] = 'admin'
                    return redirect(url_for('admin'))
                else:
                    return render_template('index.html', error='خطأ في بيانات المدير')
        if 'login_user' in request.form:
            name = request.form.get('name','').strip()
            if not name:
                return render_template('index.html', error='اكتب اسمك للدخول كزائر')
            session['user'] = name
            session['role'] = 'user'
            return redirect(url_for('rooms'))
    return render_template('index.html')

@app.route('/admin', methods=['GET','POST'])
def admin():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        room = request.form.get('room','').strip()
        desc = request.form.get('desc','').strip()
        flag = request.form.get('flag','').strip()
        if room:
            with sqlite3.connect(DB) as conn:
                c = conn.cursor()
                c.execute('INSERT INTO rooms (name,desc,flag,created_by) VALUES (?,?,?,?)', (room,desc,flag, session.get('user')))
                conn.commit()
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM rooms ORDER BY id DESC')
        rooms = c.fetchall()
    return render_template('admin.html', rooms=rooms, admin=session.get('user'))

@app.route('/rooms')
def rooms():
    if 'user' not in session:
        return redirect(url_for('index'))
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM rooms ORDER BY id DESC')
        rooms = c.fetchall()
    return render_template('rooms.html', rooms=rooms, user=session.get('user'))

@app.route('/chat/<room>')
def chat(room):
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('chat.html', room=room, user=session.get('user'), role=session.get('role'))

@app.route('/api/messages/<room>')
def api_messages(room):
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute('SELECT user, role, content, time FROM messages WHERE room=? ORDER BY id ASC', (room,))
        rows = c.fetchall()
    return jsonify([{'user':r[0],'role':r[1],'content':r[2],'time':r[3]} for r in rows])

@socketio.on('join')
def on_join(data):
    room = data.get('room')
    user = data.get('user')
    role = data.get('role','user')
    join_room(room)
    send({'type':'notice','msg':f"{user} دخل الغرفة"}, to=room)

@socketio.on('chat')
def on_chat(data):
    room = data.get('room')
    user = data.get('user')
    role = data.get('role','user')
    msg = data.get('msg')
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO messages (room,user,role,content) VALUES (?,?,?,?)', (room, user, role, msg))
        conn.commit()
    send({'type':'message','user':user,'role':role,'msg':msg}, to=room)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
