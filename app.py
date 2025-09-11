import os, sqlite3, secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, session, jsonify, url_for, send_from_directory, flash
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(__file__)
DB = os.path.join(BASE_DIR, 'chat.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXT = {'png','jpg','jpeg','gif','webp','pdf','txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXT

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'change-me-secret')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
bcrypt = Bcrypt(app)
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=True)

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        avatar TEXT,
        reset_token TEXT,
        reset_expires TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER,
        user_id INTEGER,
        message TEXT,
        filename TEXT,
        timestamp TEXT
    )''')
    c.execute("INSERT OR IGNORE INTO rooms (id,name,description) VALUES (1,'general','الغرفة العامة')")
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

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username','').strip()
    email = data.get('email','').strip()
    password = data.get('password','')
    if not username or not email or not password:
        return 'جميع الحقول مطلوبة', 400
    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    try:
        query_db('INSERT INTO users (username,email,password) VALUES (?,?,?)',(username,email,pw_hash))
        return 'تم إنشاء الحساب', 200
    except Exception as e:
        return 'اسم المستخدم أو الإيميل مستخدم مسبقاً', 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username','').strip()
    password = data.get('password','')
    if not username or not password:
        return 'مطلوب اسم مستخدم وكلمة مرور', 400
    row = query_db('SELECT id,password,avatar FROM users WHERE username=?',(username,), one=True)
    if row and bcrypt.check_password_hash(row[1], password):
        session['user_id'] = row[0]
        session['username'] = username
        session['avatar'] = row[2]
        return 'تم تسجيل الدخول', 200
    return 'خطأ في بيانات الدخول', 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/profile', methods=['GET','POST'])
def profile():
    if 'user_id' not in session:
        return redirect('/')
    uid = session['user_id']
    user = query_db('SELECT id,username,email,avatar FROM users WHERE id=?',(uid,), one=True)
    if request.method == 'POST':
        if 'avatar' in request.files:
            f = request.files['avatar']
            if f and allowed_file(f.filename):
                filename = secure_filename(f"{uid}_" + f.filename)
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                f.save(path)
                query_db('UPDATE users SET avatar=? WHERE id=?',(filename, uid))
                session['avatar'] = filename
                flash('تم تحديث الصورة')
                return redirect('/profile')
        flash('لم يتم تعديل الصورة')
    return render_template('profile.html', user=user)

@app.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect('/')
    rooms = query_db('SELECT id,name,description FROM rooms')
    return render_template('chat.html', username=session.get('username'), rooms=rooms, avatar=session.get('avatar'))

@app.route('/rooms', methods=['POST'])
def create_room():
    if 'user_id' not in session:
        return 'Unauthorized', 401
    data = request.get_json()
    name = data.get('name','').strip()
    desc = data.get('desc','').strip()
    if not name:
        return 'اسم الغرفة مطلوب', 400
    try:
        query_db('INSERT INTO rooms (name,description) VALUES (?,?)',(name,desc))
        return 'تم إنشاء الغرفة', 200
    except Exception as e:
        return 'اسم الغرفة مستخدم', 400

@app.route('/recent/<int:room_id>')
def recent(room_id):
    rows = query_db('SELECT messages.message, messages.timestamp, users.username, users.avatar, messages.filename FROM messages JOIN users ON messages.user_id=users.id WHERE room_id=? ORDER BY messages.id DESC LIMIT 200',(room_id,))
    msgs = [{'user': r[2], 'msg': r[0], 'time': r[1], 'avatar': r[3], 'file': r[4]} for r in rows]
    msgs.reverse()
    return jsonify(msgs)

@app.route('/forgot', methods=['GET','POST'])
def forgot():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        user = query_db('SELECT id FROM users WHERE email=?',(email,), one=True)
        if not user:
            return render_template('forgot.html', message='لا يوجد حساب مرتبط بهذا الإيميل')
        token = secrets.token_urlsafe(32)
        expires = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        query_db('UPDATE users SET reset_token=?, reset_expires=? WHERE id=?',(token, expires, user[0]))
        reset_link = request.host_url.rstrip('/') + url_for('reset', token=token)
        smtp_user = os.environ.get('SMTP_USER')
        if smtp_user:
            # implement SMTP send using env vars in production
            pass
        else:
            print('[DEBUG] Password reset link for', email, reset_link)
        return render_template('forgot.html', message='تم إرسال رابط إعادة التعيين (تحقق من الكونسول للنسخة التجريبية).')
    return render_template('forgot.html')

@app.route('/reset/<token>', methods=['GET','POST'])
def reset(token):
    user = query_db('SELECT id,reset_expires FROM users WHERE reset_token=?',(token,), one=True)
    if not user:
        return 'رابط خاطئ أو منتهي', 400
    expires = datetime.fromisoformat(user[1])
    if datetime.utcnow() > expires:
        return 'انتهت صلاحية الرابط', 400
    if request.method == 'POST':
        password = request.form.get('password','')
        if not password:
            return render_template('reset.html', message='أدخل كلمة مرور جديدة')
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        query_db('UPDATE users SET password=?, reset_token=NULL, reset_expires=NULL WHERE id=?',(hashed,user[0]))
        return redirect('/')
    return render_template('reset.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        return 'Unauthorized', 401
    if 'file' not in request.files:
        return 'No file', 400
    f = request.files['file']
    if f and allowed_file(f.filename):
        filename = secure_filename(f"{session['user_id']}_{secrets.token_hex(6)}_" + f.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(path)
        return jsonify({'filename': filename}), 200
    return 'Invalid file', 400

ONLINE = {}

@socketio.on('join')
def on_join(data):
    room = data.get('room')
    username = session.get('username')
    join_room(room)
    ONLINE[request.sid] = username
    emit('user_joined', {'user': username, 'online': list(ONLINE.values())}, room=room, broadcast=True)

@socketio.on('leave')
def on_leave(data):
    room = data.get('room')
    username = session.get('username')
    leave_room(room)
    ONLINE.pop(request.sid, None)
    emit('user_left', {'user': username, 'online': list(ONLINE.values())}, room=room, broadcast=True)

@socketio.on('send_message')
def handle_send_message(data):
    if 'user_id' not in session:
        emit('error', {'msg': 'unauthorized'})
        return
    room = data.get('room')
    msg = data.get('msg','').strip()
    filename = data.get('filename')
    if not msg and not filename:
        return
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    query_db('INSERT INTO messages (room_id,user_id,message,filename,timestamp) VALUES (?,?,?,?,?)',(room, session['user_id'], msg, filename, timestamp))
    payload = {'user': session.get('username'), 'msg': msg, 'time': timestamp, 'room': room, 'avatar': session.get('avatar'), 'file': filename}
    emit('receive_message', payload, room=room, broadcast=True)

@socketio.on('typing')
def on_typing(data):
    room = data.get('room')
    emit('typing', {'user': session.get('username')}, room=room, include_self=False)

@socketio.on('disconnect')
def on_disconnect():
    ONLINE.pop(request.sid, None)
    emit('user_list', {'online': list(ONLINE.values())}, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
