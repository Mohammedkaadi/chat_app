// Frontend logic for auth + chat (Socket.IO)
async function postJson(url, data){
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data)
  });
  const text = await res.text();
  return {ok: res.ok, text};
}

// Signup
document.getElementById('signupForm')?.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const f = e.target;
  const data = {username: f.username.value.trim(), email: f.email.value.trim(), password: f.password.value};
  const r = await postJson('/signup', data);
  alert(r.text);
  if(r.ok){ f.reset(); }
});

// Login
document.getElementById('loginForm')?.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const f = e.target;
  const data = {username: f.username.value.trim(), password: f.password.value};
  const r = await postJson('/login', data);
  if(r.ok){ window.location.href = '/chat'; } else { alert(r.text); }
});

// Chat page logic
if(document.getElementById('chatForm')){
  const socket = io();

  // load recent messages once
  (async function loadRecent(){
    const resp = await fetch('/recent_messages');
    const msgs = await resp.json();
    const container = document.getElementById('messages');
    msgs.forEach(m => appendMessage(m.user, m.msg, m.time, container));
    container.scrollTop = container.scrollHeight;
  })();

  // receive incoming messages
  socket.on('receive_message', (data) => {
    const container = document.getElementById('messages');
    appendMessage(data.user, data.msg, data.time, container);
    container.scrollTop = container.scrollHeight;
  });

  // send
  document.getElementById('chatForm').addEventListener('submit', (e)=>{
    e.preventDefault();
    const input = document.getElementById('msgInput');
    const text = input.value.trim();
    if(!text) return;
    socket.emit('send_message', {msg: text});
    input.value = '';
  });
}

function appendMessage(user, msg, time, container){
  const el = document.createElement('div');
  el.className = 'message';
  el.innerHTML = `<div class="meta"><strong>${escapeHtml(user)}</strong> <span style="opacity:.6">• ${time}</span></div><div class="body">${escapeHtml(msg)}</div>`;
  container.appendChild(el);
}

function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, (m)=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[m]);
}
