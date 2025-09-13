from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, send_from_directory, abort
from flask_socketio import SocketIO, join_room, leave_room, send
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, time, uuid

# --- Config ---
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get("SECRET_KEY", "change_me_please")
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

BASEDIR = os.path.dirname(__file__)
DB = os.path.join(BASEDIR, 'chat.db')
UPLOADS = os.path.join(BASEDIR, 'static', 'uploads')
os.makedirs(UPLOADS, exist_ok=True)

# --- DB init ---
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
            type TEXT DEFAULT 'text',
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()
init_db()

# --- helpers ---
def query(sql, params=(), one=False):
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute(sql, params)
        rows = c.fetchall()
    return (rows[0] if rows else None) if one else rows

def admin_exists():
    row = query('SELECT COUNT(*) FROM users WHERE role="admin"', one=True)
    return row and row[0] > 0

# in-memory online tracking: room -> {username: {'sid':..., 'role':..., 'last_seen':...}}
online_users = {}

# --- Routes ---
@app.route('/', methods=['GET','POST'])
def index():
    # if admin exists, hide register option in UI (handled in template by calling admin_exists())
    if request.method == 'POST':
        # register admin (allowed only if no admin yet)
        if 'register_admin' in request.form:
            if admin_exists():
                flash('تم تفعيل حساب المدير من قبل، لا يمكن تسجيل مدير جديد', 'danger')
            else:
                name = request.form.get('name','').strip()
                email = request.form.get('email','').strip()
                password = request.form.get('password','').strip()
                if not (name and email and password):
                    flash('املأ جميع الحقول', 'danger')
                else:
                    pwd_hash = generate_password_hash(password)
                    try:
                        with sqlite3.connect(DB) as conn:
                            c = conn.cursor()
                            c.execute('INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)',
                                      (name,email,pwd_hash,'admin'))
                            conn.commit()
                            flash('تم تسجيل المدير. سجّل الدخول الآن.', 'success')
                    except Exception:
                        flash('خطأ: الايميل قد يكون مسجلاً مسبقاً', 'danger')
        # login admin
        if 'login_admin' in request.form:
            email = request.form.get('email','').strip()
            password = request.form.get('password','').strip()
            row = query('SELECT * FROM users WHERE email=? AND role="admin"', (email,), one=True)
            if row and check_password_hash(row[3], password):
                session['user'] = row[1]
                session['role'] = 'admin'
                return redirect(url_for('admin'))
            else:
                flash('بيانات المدير غير صحيحة', 'danger')
        # login guest
        if 'login_user' in request.form:
            name = request.form.get('name','').strip()
            if name:
                session['user'] = name
                session['role'] = 'user'
                return redirect(url_for('rooms'))
            else:
                flash('اكتب اسمك للدخول', 'danger')
    return render_template('index.html', admin_exists=admin_exists())

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
                    c.execute('INSERT INTO rooms (name,desc,created_by) VALUES (?,?,?)', (room,desc, session.get('user')))
                    conn.commit()
                    flash('تمت إضافة الغرفة', 'success')
            except Exception:
                flash('اسم الغرفة موجود مسبقاً', 'danger')
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
    # ensure room exists
    r = query('SELECT * FROM rooms WHERE name=?', (room,), one=True)
    if not r:
        abort(404)
    return render_template('chat.html', room=room, user=session.get('user'), role=session.get('role'))

@app.route('/settings', methods=['GET','POST'])
def settings():
    if 'user' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        newname = request.form.get('name','').strip()
        sound = request.form.get('sound','on')
        if newname:
            session['user'] = newname
        session['sound'] = sound
        flash('تم حفظ الإعدادات','success')
        return redirect(url_for('settings'))
    return render_template('settings.html', user=session.get('user'), sound=session.get('sound','on'))

@app.route('/api/messages/<room>')
def api_messages(room):
    rows = query('SELECT user, role, content, type, time FROM messages WHERE room=? ORDER BY id ASC', (room,))
    return jsonify([{'user':r[0],'role':r[1],'content':r[2],'type':r[3],'time':r[4]} for r in rows])

@app.route('/api/members/<room>')
def api_members(room):
    members = []
    roommap = online_users.get(room, {})
    for name,info in roommap.items():
        members.append({'user':name, 'role': info.get('role','user'), 'last_seen': info.get('last_seen')})
    return jsonify(members)

# upload audio file
@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return 'no file', 400
    file = request.files['audio']
    room = request.form.get('room')
    user = request.form.get('user')
    role = request.form.get('role','user')
    if not (room and user):
        return 'missing', 400
    ext = os.path.splitext(file.filename)[1] or '.webm'
    fname = f"{int(time.time())}_{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOADS, fname)
    file.save(save_path)
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO messages (room,user,role,content,type) VALUES (?,?,?,?,?)', (room, user, role, fname, 'audio'))
        conn.commit()
    url = url_for('uploaded_file', filename=fname)
    socketio.emit('message', {'type':'audio','user':user,'role':role,'url':url}, to=room)
    return jsonify({'ok':True, 'url': url})

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOADS, filename)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- Socket events ---
@socketio.on('join')
def on_join(data):
    room = data.get('room')
    user = data.get('user')
    role = data.get('role','user')
    sid = request.sid
    join_room(room)
    online_users.setdefault(room, {})[user] = {'sid': sid, 'role': role, 'last_seen': int(time.time())}
    send({'type':'notice','msg':f"{user} دخل الغرفة"}, to=room)
    socketio.emit('members_update', {'room': room, 'members': list(online_users[room].keys())}, to=room)

@socketio.on('leave')
def on_leave(data):
    room = data.get('room'); user = data.get('user')
    leave_room(room)
    if room in online_users and user in online_users[room]:
        online_users[room].pop(user, None)
        send({'type':'notice','msg':f"{user} غادر الغرفة"}, to=room)
        socketio.emit('members_update', {'room': room, 'members': list(online_users.get(room, {}).keys())}, to=room)

@socketio.on('chat')
def on_chat(data):
    room = data.get('room'); user = data.get('user'); role = data.get('role','user'); msg = data.get('msg')
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO messages (room,user,role,content,type) VALUES (?,?,?,?,?)', (room, user, role, msg, 'text'))
        conn.commit()
    send({'type':'message','user':user,'role':role,'msg':msg}, to=room)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    for room, users in list(online_users.items()):
        for name, info in list(users.items()):
            if info.get('sid') == sid:
                users.pop(name, None)
                send({'type':'notice','msg':f"{name} خرج من الغرفة"}, to=room)
                socketio.emit('members_update', {'room': room, 'members': list(online_users.get(room, {}).keys())}, to=room)
        if not users:
            online_users.pop(room, None)

# serve service worker at root (if not served via static)
@app.route('/service-worker.js')
def service_worker():
    return send_from_directory(app.static_folder, 'service-worker.js')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
