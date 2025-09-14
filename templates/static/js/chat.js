const socket = io();

socket.on("connect", () => {
  socket.emit("join", {username: USERNAME, room: ROOM});
});

socket.on("message", (msg) => {
  const box = document.getElementById("messages");
  const div = document.createElement("div");
  div.textContent = msg;
  box.appendChild(div);
});

function sendMessage() {
  const input = document.getElementById("msg");
  const text = input.value;
  if(text.trim() !== ""){
    socket.emit("message", {username: USERNAME, room: ROOM, msg: text});
    input.value = "";
  }
}