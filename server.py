#!/usr/bin/env python3
import json
import os
import re
import time
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
DOCS_DIR = ROOT / "docs"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8765"))
TOP_K = int(os.getenv("RAG_TOP_K", "3"))


SYSTEM_PROMPT = os.getenv(
    "ROBOT_SYSTEM_PROMPT",
    (
        "你是一个简洁、温暖、可靠的中文学习知识库助手。"
        "优先基于给定资料回答；资料不足时要明确说明，不要编造。"
    ),
)


def tokenize(text):
    return re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]", text.lower())


def split_document(text):
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks = []
    for paragraph in paragraphs:
        if len(paragraph) <= 600:
            chunks.append(paragraph)
            continue
        for start in range(0, len(paragraph), 500):
            chunk = paragraph[start : start + 600].strip()
            if chunk:
                chunks.append(chunk)
    return chunks


def load_doc_chunks():
    chunks = []
    if not DOCS_DIR.exists():
        return chunks

    for path in sorted(DOCS_DIR.rglob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for index, chunk in enumerate(split_document(text), start=1):
            chunks.append(
                {
                    "source": str(path.relative_to(ROOT)),
                    "chunk_id": index,
                    "content": chunk,
                }
            )
    return chunks


def score_chunk(question_tokens, question_text, chunk):
    chunk_text = chunk["content"].lower()
    chunk_tokens = tokenize(chunk_text)
    if not chunk_tokens:
        return 0

    token_overlap = sum(1 for token in question_tokens if token in chunk_tokens)
    phrase_boost = 3 if question_text and question_text in chunk_text else 0
    title_boost = 2 if any(token in chunk["source"].lower() for token in question_tokens) else 0
    return token_overlap + phrase_boost + title_boost


def retrieve_references(question, top_k=TOP_K):
    question_text = question.strip().lower()
    question_tokens = tokenize(question_text)
    if not question_tokens:
        return []

    scored = []
    for chunk in load_doc_chunks():
        score = score_chunk(question_tokens, question_text, chunk)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    references = []
    for score, chunk in scored[:top_k]:
        references.append(
            {
                "source": chunk["source"],
                "chunk_id": chunk["chunk_id"],
                "snippet": chunk["content"][:420],
                "score": score,
            }
        )
    return references


def build_rag_message(references):
    if not references:
        return None

    context_blocks = []
    for ref in references:
        context_blocks.append(
            f"[{ref['source']}#片段{ref['chunk_id']}]\n{ref['snippet']}"
        )
    return (
        "以下是从本地知识库检索到的资料片段。回答必须优先依据这些资料，"
        "并在答案末尾用简短方式提到来源文件；如果资料不足，请直接说明。\n\n"
        + "\n\n".join(context_blocks)
    )


def latest_user_text(messages):
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def chat_with_model(messages, references):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        user_text = latest_user_text(messages)
        if references:
            sources = "、".join(
                f"{ref['source']}#片段{ref['chunk_id']}" for ref in references
            )
            return (
                "我在本地资料里找到了相关内容。现在还没有配置大模型 API key，"
                "所以先用检索结果演示 RAG 流程。\n\n"
                f"你的问题是：{user_text}\n\n"
                f"可参考来源：{sources}"
            )
        return (
            "我已经听到了。现在还没有配置大模型 API key，所以先用本地演示模式回复。"
            f"你刚才说的是：{user_text}"
        )

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    url = f"{base_url}/chat/completions"
    model_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    rag_message = build_rag_message(references)
    if rag_message:
        model_messages.append({"role": "system", "content": rag_message})
    model_messages.extend(messages[-10:])

    payload = {
        "model": model,
        "messages": model_messages,
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
            user_text = latest_user_text(messages)
            start = time.perf_counter()
            references = retrieve_references(user_text)
            retrieve_ms = int((time.perf_counter() - start) * 1000)
            model_start = time.perf_counter()
            reply = chat_with_model(messages, references)
            model_ms = int((time.perf_counter() - model_start) * 1000)
            print(
                json.dumps(
                    {
                        "event": "chat",
                        "references": len(references),
                        "retrieve_ms": retrieve_ms,
                        "model_ms": model_ms,
                    },
                    ensure_ascii=False,
                )
            )
            self.respond_json({"reply": reply, "references": references})
        except Exception as exc:
            print(json.dumps({"event": "error", "error": str(exc)}, ensure_ascii=False))
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
