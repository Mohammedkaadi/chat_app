const socket = io();
let currentRoom = "";

function joinRoom() {
    const room = document.getElementById("room").value;
    if (room) {
        currentRoom = room;
        socket.emit("join", { room });
    }
}

function leaveRoom() {
    if (currentRoom) {
        socket.emit("leave", { room: currentRoom });
        currentRoom = "";
    }
}

function sendMessage() {
    const msg = document.getElementById("message").value;
    if (msg && currentRoom) {
        socket.emit("message", { room: currentRoom, msg });
        document.getElementById("message").value = "";
    }
}

socket.on("message", (data) => {
    const box = document.getElementById("chat-box");
    if (typeof data === "string") {
        box.innerHTML += `<p><i>${data}</i></p>`;
    } else {
        box.innerHTML += `<p><b>${data.user}:</b> ${data.msg}</p>`;
    }
    box.scrollTop = box.scrollHeight;
});
