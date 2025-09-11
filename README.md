# ChatWave Pro — Full project

Features:
- Flask + Socket.IO chat (rooms)
- Signup/login, reset password (token), profile + avatar upload
- File uploads in chat (stored in static/uploads)
- Dark/Light theme client-side, emoji picker, responsive UI

Run locally:
1. pip install -r requirements.txt
2. python app.py
3. Open http://127.0.0.1:5000

Notes:
- Set SECRET_KEY env var in production.
- Password reset link prints to console in demo mode. Configure SMTP env vars to send emails.
