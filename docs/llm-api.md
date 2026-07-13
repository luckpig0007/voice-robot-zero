# LLM API 工程要点

AI 应用中，API key 应该保存在后端环境变量里，不能暴露给前端。前端只调用自己的业务接口，例如 `/api/chat`，后端再负责请求 OpenAI-compatible 模型服务。

模型调用需要处理常见异常：API key 缺失、模型名称错误、base_url 配错、网络超时、服务返回 401 或 5xx。页面应该展示用户能理解的错误提示，终端日志保留完整排查信息。

为了控制 token 成本，后端可以只发送最近若干轮对话历史，或把长文档先检索再注入上下文。这样既能保持多轮体验，也能避免请求变得越来越贵。

OpenAI-compatible 接口通常使用 `/v1/chat/completions`，请求里包含 model、messages 和 temperature。messages 里一般会有 system、user、assistant 三类角色。
