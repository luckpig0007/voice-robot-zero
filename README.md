# Voice Robot Zero

一个从 0 开始的语音智能机器人最小闭环：

- 浏览器语音识别：麦克风转文字
- Python 后端：维护对话并调用 OpenAI-compatible Chat Completions
- 浏览器语音合成：把回复朗读出来
- 零第三方 Python 依赖：只用标准库

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

## 当前边界

这是第一版验证闭环，不包含唤醒词、流式 TTS、打断、硬件端、账号系统和设备管理。下一步可以加：

1. 服务端 ASR/TTS，摆脱浏览器 Web Speech API。
2. 流式回复和播放，降低等待时间。
3. 唤醒词、打断、连续对话。
4. ESP32 或树莓派客户端。
5. 工具调用，比如查天气、控制设备、读取本地文件。
