#!/usr/bin/env python3
import json
import os
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8765"))


SYSTEM_PROMPT = os.getenv(
    "ROBOT_SYSTEM_PROMPT",
    "你是一个简洁、温暖、可靠的中文语音智能助手。回答要适合被朗读，避免太长。",
)


def chat_with_model(messages):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        user_text = messages[-1]["content"] if messages else ""
        return (
            "我已经听到了。现在还没有配置大模型 API key，所以先用本地演示模式回复。"
            f"你刚才说的是：{user_text}"
        )

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        "temperature": 0.7,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"模型接口返回错误 {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"模型接口调用失败: {exc}") from exc


class VoiceRobotHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
            messages = payload.get("messages", [])
            if not isinstance(messages, list):
                raise ValueError("messages must be a list")
            reply = chat_with_model(messages)
            self.respond_json({"reply": reply})
        except Exception as exc:
            self.respond_json({"error": str(exc)}, status=500)

    def respond_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    server = ThreadingHTTPServer((HOST, PORT), VoiceRobotHandler)
    print(f"Voice robot running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
