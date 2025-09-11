# ChatWave Pro — Full featured demo

Features:
- Flask + Socket.IO real-time chat
- Multiple rooms
- Dark/Light mode (client)
- Emoji picker (built-in simple list)
- Avatar upload (stored in static/uploads)
- File/image upload in chat
- Password reset flow (token, demo prints link to console; configure SMTP to send real emails)
- Responsive UI for mobile

Run locally:
1. pip install -r requirements.txt
2. python app.py
3. Open http://127.0.0.1:5000

Notes:
- For production, set SECRET_KEY env var and configure SMTP env vars:
  SMTP_USER, SMTP_PASS, SMTP_HOST, SMTP_PORT
- Uploaded files are stored in static/uploads (ephemeral on platforms like Railway).
