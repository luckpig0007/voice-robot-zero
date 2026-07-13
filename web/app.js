const statusEl = document.querySelector("#status");
const messagesEl = document.querySelector("#messages");
const inputForm = document.querySelector("#inputForm");
const textInput = document.querySelector("#textInput");
const listenButton = document.querySelector("#listenButton");
const clearButton = document.querySelector("#clearButton");

const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition || null;

let recognition = null;
let listening = false;
let messages = [];

function setStatus(text) {
  statusEl.textContent = text;
}

function addMessage(role, content) {
  messages.push({ role, content });
  const node = document.createElement("article");
  node.className = `message ${role}`;
  node.textContent = content;
  messagesEl.appendChild(node);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function speak(text) {
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";
  utterance.rate = 1.02;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

async function sendUserMessage(text) {
  const cleanText = text.trim();
  if (!cleanText) return;

  addMessage("user", cleanText);
  textInput.value = "";
  setStatus("思考中...");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "请求失败");
    addMessage("assistant", data.reply);
    speak(data.reply);
    setStatus("准备就绪");
  } catch (error) {
    addMessage("assistant", `出错了：${error.message}`);
    setStatus("请求失败");
  }
}

function setupSpeechRecognition() {
  if (!SpeechRecognition) {
    listenButton.disabled = true;
    listenButton.textContent = "浏览器不支持语音";
    setStatus("请用 Chrome 或 Edge 打开");
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = "zh-CN";
  recognition.interimResults = false;
  recognition.continuous = false;

  recognition.onstart = () => {
    listening = true;
    listenButton.classList.add("active");
    listenButton.textContent = "正在听...";
    setStatus("正在听你说话");
  };

  recognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map((result) => result[0].transcript)
      .join("");
    sendUserMessage(transcript);
  };

  recognition.onerror = (event) => {
    setStatus(`语音识别失败：${event.error}`);
  };

  recognition.onend = () => {
    listening = false;
    listenButton.classList.remove("active");
    listenButton.textContent = "按住说话";
    if (statusEl.textContent === "正在听你说话") setStatus("准备就绪");
  };
}

listenButton.addEventListener("click", () => {
  if (!recognition) return;
  if (listening) {
    recognition.stop();
  } else {
    window.speechSynthesis.cancel();
    recognition.start();
  }
});

inputForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendUserMessage(textInput.value);
});

clearButton.addEventListener("click", () => {
  messages = [];
  messagesEl.textContent = "";
  window.speechSynthesis.cancel();
  setStatus("已清空");
});

setupSpeechRecognition();
