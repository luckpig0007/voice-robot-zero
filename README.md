# Voice Robot Zero

一个从 0 开始的语音 + 本地知识库问答最小闭环：

- 浏览器语音识别：麦克风转文字
- Python 后端：维护对话、检索本地资料并调用 OpenAI-compatible Chat Completions
- 浏览器语音合成：把回复朗读出来
- 本地 RAG 雏形：读取 `docs/` 下的 Markdown / TXT，切分片段，返回引用来源
- 零第三方 Python 依赖：只用标准库

## 核心流程

```text
用户语音/文本
  -> 前端 /api/chat
  -> 后端读取最近对话
  -> 从 docs/ 检索 TopK 相关片段
  -> 将片段注入 Prompt
  -> 调用 LLM 或本地 demo 模式
  -> 返回 reply + references
  -> 前端展示答案和引用来源，并朗读答案
```

## 运行

```bash
cd /Users/jianglinsu/Desktop/newgrand/voiceAgent/voice-robot-zero
python3 server.py
```

打开：

```text
http://127.0.0.1:8765
```

建议用 Chrome 或 Edge。首次点击语音按钮时，浏览器会请求麦克风权限。

## 配置大模型

不配置 API key 时，项目会使用本地演示回复。要接入真实模型：

```bash
cd /Users/jianglinsu/Desktop/newgrand/voiceAgent/voice-robot-zero
source .env.example
python3 server.py
```

如果你使用的是其他 OpenAI-compatible 服务，只要改：

```bash
export OPENAI_BASE_URL="你的服务地址/v1"
export OPENAI_MODEL="你的模型名"
```

可选配置：

```bash
export RAG_TOP_K="3"
```

## 本地知识库

把 `.md` 或 `.txt` 文件放到 `docs/` 目录，服务端会在每次提问时读取并检索相关片段。

当前内置了 3 份示例资料：

- `docs/rag.md`
- `docs/llm-api.md`
- `docs/interview.md`

可以试这些问题：

- 什么是 RAG？
- API key 为什么不能放前端？
- AI 应用工程师项目应该怎么讲？
- 怎么减少大模型幻觉？

接口返回示例：

```json
{
  "reply": "回答内容",
  "references": [
    {
      "source": "docs/rag.md",
      "chunk_id": 1,
      "snippet": "命中的资料片段",
      "score": 8
    }
  ]
}
```

## 当前边界

这是第一版验证闭环，不包含唤醒词、流式 TTS、打断、硬件端、账号系统和设备管理。RAG 目前使用标准库做简化关键词检索，还没有接入 embedding 或向量数据库。下一步可以加：

1. embedding 模型和向量检索，替换简化关键词检索。
2. Tool Calling，比如时间、天气 mock、计算器、网页摘要。
3. 简单评估集，准备 10 个问题和期望答案。
4. 服务端 ASR/TTS、流式回复和播放，降低等待时间。
5. 唤醒词、打断、连续对话，或 ESP32 / 树莓派客户端。
