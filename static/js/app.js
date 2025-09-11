// Client-side for ChatWave Pro: auth, chat, rooms, emoji, dark/light, uploads

async function postJson(url,data){
  const r = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  return {ok:r.ok, text:await r.text()};
}

// AUTH
document.getElementById('signupForm')?.addEventListener('submit', async (e)=>{
  e.preventDefault(); const f=e.target; const data={username:f.username.value.trim(),email:f.email.value.trim(),password:f.password.value}; const r=await postJson('/signup',data); alert(r.text); if(r.ok) f.reset();
});
document.getElementById('loginForm')?.addEventListener('submit', async (e)=>{ e.preventDefault(); const f=e.target; const data={username:f.username.value.trim(),password:f.password.value}; const r=await postJson('/login',data); if(r.ok) window.location='/chat'; else alert(r.text); });

// THEME toggle
const themeToggle = document.getElementById('themeToggle');
if(themeToggle){
  const saved = localStorage.getItem('cw-theme') || 'light';
  document.body.classList.toggle('theme-light', saved==='light');
  themeToggle.addEventListener('click', ()=>{
    const isLight = document.body.classList.toggle('theme-light');
    localStorage.setItem('cw-theme', isLight ? 'light':'dark');
  });
}

// CHAT page logic
if(document.getElementById('chatForm')){
  const socket = io();
  let currentRoom = null;
  const messagesEl = document.getElementById('messages');
  const onlineEl = document.getElementById('onlineList');
  const typingEl = document.getElementById('typing');
  const emojiBtn = document.getElementById('emojiBtn');
  const emojiPicker = document.getElementById('emojiPicker');
  const fileInput = document.getElementById('fileInput');
  const attachBtn = document.getElementById('attachBtn');

  // build a small emoji grid
  const EMOJIS = ['😀','😁','😂','🤣','😊','😍','😎','🤩','👍','🙏','🔥','🎉','💬','❤️','😅','🤔','🙌','👏','😴','🤖','🎯','📎','📷','📁','🔒','✨','🌙','☀️','🕶️','🍀','🚀'];
  EMOJIS.forEach(e => { const b=document.createElement('button'); b.type='button'; b.className='emoji'; b.textContent=e; b.addEventListener('click', ()=>{ insertAtCursor(document.getElementById('msgInput'), e); }); emojiPicker.appendChild(b); });

  // room clicks
  document.querySelectorAll('.room').forEach(li=> li.addEventListener('click', ()=>{
    const id = li.dataset.id;
    joinRoom(id);
    document.querySelectorAll('.room').forEach(x=>x.classList.remove('active'));
    li.classList.add('active');
  }));

  document.getElementById('createRoom')?.addEventListener('submit', async e=>{
    e.preventDefault(); const f=e.target; const name=f.name.value.trim(); const desc=f.desc.value.trim(); if(!name) return alert('اسم الغرفة مطلوب'); const r=await postJson('/rooms',{name,desc}); alert(r.text); if(r.ok) location.reload();
  });

  async function joinRoom(id){
    if(currentRoom) socket.emit('leave',{room:currentRoom});
    currentRoom = id;
    messagesEl.innerHTML='';
    const resp = await fetch('/recent/'+id); const msgs = await resp.json();
    msgs.forEach(m=> appendMessage(m.user,m.msg,m.time,m.avatar,m.file));
    socket.emit('join',{room:id});
  }

  const first = document.querySelector('.room');
  if(first) first.click();

  document.getElementById('chatForm').addEventListener('submit', async e=>{
    e.preventDefault();
    const text = document.getElementById('msgInput').value.trim();
    // handle file upload if selected
    const file = fileInput.files[0];
    if(file){
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch('/upload',{method:'POST', body:fd});
      if(r.ok){
        const j = await r.json();
        socket.emit('send_message',{room:currentRoom, msg: '', filename: j.filename});
      } else {
        alert('Failed upload');
      }
      fileInput.value='';
      return;
    }
    if(!text) return;
    socket.emit('send_message',{room:currentRoom, msg:text});
    document.getElementById('msgInput').value='';
  });

  // typing
  let typingTimer=null;
  document.getElementById('msgInput').addEventListener('input', ()=>{
    socket.emit('typing',{room:currentRoom});
    clearTimeout(typingTimer);
    typingTimer = setTimeout(()=>{ typingEl.textContent=''; }, 1200);
  });

  socket.on('receive_message', data => { if(String(data.room) === String(currentRoom)) appendMessage(data.user,data.msg,data.time,data.avatar,data.file); });
  socket.on('typing', d=> { typingEl.textContent = d.user + ' يكتب...'; });
  socket.on('user_joined', d=> { updateOnline(d.online); });
  socket.on('user_left', d=> { updateOnline(d.online); });
  socket.on('user_list', d=> { updateOnline(d.online); });

  function appendMessage(user,msg,time,avatar,file){
    const el = document.createElement('div'); el.className='message';
    let inner = `<div class="meta"><strong>${escapeHtml(user)}</strong> <span class="muted">• ${time}</span></div>`;
    if(file){ const url='/uploads/'+file; inner += `<div class="body"><a href="${url}" target="_blank">📎 ${escapeHtml(file)}</a></div>`; }
    if(msg) inner += `<div class="body">${escapeHtml(msg)}</div>`;
    el.innerHTML = inner;
    messagesEl.appendChild(el); messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  function updateOnline(list){ onlineEl.innerHTML=''; list.forEach(u=>{ const li=document.createElement('li'); li.textContent=u; onlineEl.appendChild(li); }); }
  function escapeHtml(s){ return String(s).replace(/[&<>"']/g, (m)=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[m]); }

  // emoji picker toggle
  emojiBtn.addEventListener('click', ()=>{ emojiPicker.style.display = emojiPicker.style.display==='none' ? 'grid' : 'none'; });

  // attach file
  attachBtn.addEventListener('click', ()=> fileInput.click());

  // helper to insert emoji at cursor
  function insertAtCursor(el, text) {
    const start = el.selectionStart || 0;
    const end = el.selectionEnd || 0;
    const val = el.value;
    el.value = val.slice(0,start) + text + val.slice(end);
    el.selectionStart = el.selectionEnd = start + text.length;
    el.focus();
  }
}
