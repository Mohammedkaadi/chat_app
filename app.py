from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change_me_please")
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

DB = os.path.join(os.path.dirname(__file__), 'chat.db')

def init_db():
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            desc TEXT,
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

def query(sql, params=(), one=False):
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute(sql, params)
        rv = c.fetchall()
    return (rv[0] if rv else None) if one else rv

# قائمة المستخدمين المتصلين
online_users = {}

@app.route('/', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        if 'register_admin' in request.form:
            name = request.form.get('name','').strip()
            email = request.form.get('email','').strip()
            password = request.form.get('password','').strip()
            if name and email and password:
                try:
                    with sqlite3.connect(DB) as conn:
                        c = conn.cursor()
                        c.execute('INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)',
                                  (name,email,generate_password_hash(password),'admin'))
                        conn.commit()
                        flash('تم تسجيل المدير. سجّل الدخول الآن.','success')
                except:
                    flash('الايميل مسجّل مسبقاً','danger')
            else:
                flash('املأ جميع الحقول','danger')
        if 'login_admin' in request.form:
            email = request.form.get('email','').strip()
            password = request.form.get('password','').strip()
            row = query('SELECT * FROM users WHERE email=? AND role="admin"', (email,), one=True)
            if row and check_password_hash(row[3], password):
                session['user'] = row[1]
                session['role'] = 'admin'
                return redirect(url_for('admin'))
            else:
                flash('بيانات المدير غير صحيحة','danger')
        if 'login_user' in request.form:
            name = request.form.get('name','').strip()
            if name:
                session['user'] = name
                session['role'] = 'user'
                return redirect(url_for('rooms'))
            else:
                flash('اكتب اسمك للدخول','danger')
    return render_template('index.html')

@app.route('/admin', methods=['GET','POST'])
def admin():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        room = request.form.get('room','').strip()
        desc = request.form.get('desc','').strip()
        if room:
            try:
                with sqlite3.connect(DB) as conn:
                    c = conn.cursor()
                    c.execute('INSERT INTO rooms (name,desc,created_by) VALUES (?,?,?)',
                              (room,desc, session.get('user')))
                    conn.commit()
                    flash('تمت إضافة الغرفة','success')
            except:
                flash('اسم الغرفة موجود مسبقاً','danger')
    rooms = query('SELECT * FROM rooms ORDER BY id DESC')
    return render_template('admin.html', rooms=rooms, admin=session.get('user'))

@app.route('/rooms')
def rooms():
    if 'user' not in session:
        return redirect(url_for('index'))
    rooms = query('SELECT * FROM rooms ORDER BY id DESC')
    return render_template('rooms.html', rooms=rooms, user=session.get('user'))

@app.route('/chat/<room>')
def chat(room):
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('chat.html', room=room, user=session.get('user'), role=session.get('role'))

@app.route('/settings', methods=['GET','POST'])
def settings():
    if 'user' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        newname = request.form.get('name','').strip()
        sound = request.form.get('sound','off')
        if newname:
            session['user'] = newname
        session['sound'] = sound
        flash('تم حفظ الإعدادات','success')
    return render_template('settings.html', user=session.get('user'), sound=session.get('sound','on'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- Socket.IO Events ---
@socketio.on('join')
def on_join(data):
    room = data.get('room')
    user = data.get('user')
    role = data.get('role','user')
    join_room(room)
    if room not in online_users:
        online_users[room] = set()
    online_users[room].add(user)
    emit('user_list', list(online_users[room]), to=room)
    send({'type':'notice','msg':f"{user} دخل الغرفة"}, to=room)

@socketio.on('leave')
def on_leave(data):
    room = data.get('room')
    user = data.get('user')
    leave_room(room)
    if room in online_users and user in online_users[room]:
        online_users[room].remove(user)
        emit('user_list', list(online_users[room]), to=room)
    send({'type':'notice','msg':f"{user} غادر الغرفة"}, to=room)

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
