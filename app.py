import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, join_room, leave_room, emit
from datetime import datetime
import uuid

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change_this_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'data.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins='*')

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(30), default='guest')  # admin / user / guest
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)
    def check_password(self, pw):
        if not self.password_hash: return False
        return check_password_hash(self.password_hash, pw)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    country = db.Column(db.String(100), nullable=True)
    type = db.Column(db.String(50), default='public')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    ts = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='messages')

# Helpers
def current_user():
    uid = session.get('user_id')
    if not uid: return None
    return User.query.get(uid)

def require_login(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return wrapped

def require_admin(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        u = current_user()
        if not u or u.role != 'admin':
            flash('مطلوب صلاحية المدير', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapped

# Routes
@app.route('/')
def index():
    # show landing page index.html
    return render_template('index.html')

@app.route('/setup-admin', methods=['GET','POST'])
def setup_admin():
    # first-run admin creation, disappears after admin exists
    if User.query.filter_by(role='admin').first():
        flash('Admin already exists', 'info')
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email') or None
        password = request.form.get('password')
        if not username or not password:
            flash('اكتب اسم وكلمة مرور', 'warning')
            return redirect(url_for('setup_admin'))
        admin = User(username=username, email=email, role='admin')
        admin.set_password(password)
        db.session.add(admin); db.session.commit()
        flash('تم إنشاء المدير', 'success')
        return redirect(url_for('login'))
    return render_template('setup_admin.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password') or ''
        if not username:
            flash('اكتب اسم المستخدم', 'warning'); return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('الاسم مستخدم', 'warning'); return redirect(url_for('register'))
        if password:
            u = User(username=username, role='user'); u.set_password(password)
        else:
            u = User(username=username, role='guest')
        db.session.add(u); db.session.commit()
        session['user_id'] = u.id
        flash('تم التسجيل', 'success'); return redirect(url_for('rooms'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier').strip()
        password = request.form.get('password') or ''
        user = None
        if '@' in identifier:
            user = User.query.filter_by(email=identifier).first()
        if not user:
            user = User.query.filter_by(username=identifier).first()
        if not user:
            flash('المستخدم غير موجود', 'danger'); return redirect(url_for('login'))
        if user.role == 'guest' and not user.password_hash:
            session['user_id'] = user.id; flash('تم تسجيل الدخول كزائر', 'success'); return redirect(url_for('rooms'))
        if not password or not user.check_password(password):
            flash('خطأ في بيانات الدخول', 'danger'); return redirect(url_for('login'))
        session['user_id'] = user.id; flash('تم تسجيل الدخول', 'success'); return redirect(url_for('rooms'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None); flash('تم الخروج', 'info'); return redirect(url_for('index'))

@app.route('/rooms')
@require_login
def rooms():
    u = current_user()
    rooms = Room.query.order_by(Room.created_at.asc()).all()
    return render_template('rooms.html', rooms=rooms, user=u)

@app.route('/room/<slug>')
@require_login
def room_view(slug):
    r = Room.query.filter_by(slug=slug).first_or_404()
    u = current_user()
    recent = Message.query.filter_by(room_id=r.id).order_by(Message.ts.asc()).limit(200).all()
    return render_template('chat.html', room=r, messages=recent, user=u)

@app.route('/admin')
@require_admin
def admin_panel():
    rooms = Room.query.order_by(Room.created_at.desc()).all()
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin.html', rooms=rooms, users=users)

@app.route('/admin/rooms/create', methods=['POST'])
@require_admin
def admin_create_room():
    name = request.form.get('name').strip()
    country = request.form.get('country','عام')
    rtype = request.form.get('type','public')
    slug = request.form.get('slug') or name.replace(' ','-') + '-' + uuid.uuid4().hex[:6]
    room = Room(name=name, slug=slug, country=country, type=rtype)
    db.session.add(room); db.session.commit()
    flash('تم إنشاء الغرفة', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/users/toggle/<int:user_id>')
@require_admin
def admin_toggle_user(user_id):
    u = User.query.get_or_404(user_id)
    u.role = 'user' if u.role == 'admin' else 'admin'
    db.session.commit()
    flash('تم تعديل صلاحية المستخدم', 'info')
    return redirect(url_for('admin_panel'))

# SocketIO events
@socketio.on('join')
def on_join(data):
    room_slug = data.get('room')
    username = data.get('username')
    join_room(room_slug)
    emit('system', {'text': f'{username} دخل الغرفة'}, to=room_slug)

@socketio.on('leave')
def on_leave(data):
    room_slug = data.get('room')
    username = data.get('username')
    leave_room(room_slug)
    emit('system', {'text': f'{username} خرج من الغرفة'}, to=room_slug)

@socketio.on('chat')
def on_chat(data):
    room_slug = data.get('room')
    text = data.get('text','').strip()
    uid = session.get('user_id')
    if not uid or not text: return
    room = Room.query.filter_by(slug=room_slug).first()
    if not room: return
    m = Message(room_id=room.id, user_id=uid, text=text)
    db.session.add(m); db.session.commit()
    emit('chat', {'user': current_user().username, 'text': text, 'ts': m.ts.isoformat()}, to=room_slug)

@app.cli.command('initdb')
def initdb():
    with app.app_context():
        db.create_all()
    print('db created')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
