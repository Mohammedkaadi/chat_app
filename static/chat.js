const socket = io();
socket.on('connect', ()=>{ console.log('socket connected'); });
socket.on('system', (m)=>{ const box=document.getElementById('messages'); const d=document.createElement('div'); d.className='p-2 text-sm text-gray-700'; d.innerText=m.text; box.appendChild(d); box.scrollTop=box.scrollHeight; });
socket.on('chat', (m)=>{ const box=document.getElementById('messages'); const d=document.createElement('div'); d.className='p-2 bg-white rounded mb-2'; d.innerHTML='<strong>'+m.user+'</strong>: '+m.text; box.appendChild(d); box.scrollTop=box.scrollHeight; });
document.getElementById('send_btn')?.addEventListener('click', send);
document.getElementById('msg_input')?.addEventListener('keypress', (e)=>{ if(e.key==='Enter') send(); });
function send(){ const input=document.getElementById('msg_input'); const text=input.value.trim(); if(!text) return; socket.emit('chat',{room:ROOM,text}); input.value=''; }
