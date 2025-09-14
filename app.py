
import os
import sqlite3
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'db.sqlite')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-secret')
socketio = SocketIO(app, cors_allowed_origins='*')

ADMIN_KEY = os.environ.get('ADMIN_KEY', '')

# Database init and helpers
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        role TEXT DEFAULT 'guest',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        is_private INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER,
        user_id INTEGER,
        username TEXT,
        text TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
