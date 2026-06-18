"""示例插件：接入一个**自定义大模型后端**（Provider）+ 配套工具。

演示 register_provider 的完整用法——实现 Provider.chat 即可被 `provider=myecho` 选用，
工具循环、记忆、流式等全部照常工作。真实场景把 chat() 换成对你的模型 API 的调用即可
（参考 mnemo/providers/openai.py 用标准库 http_post_json 发请求）。
"""
from mnemo.providers.base import Provider


class MyEchoProvider(Provider):
    name = "myecho"

    def chat(self, messages, *, temperature=0.7, max_tokens=2048) -> str:
        last = next((m.content for m in reversed(messages) if m.role == "user"), "")
        # 演示用：把用户最后一句反转返回。换成真实 API 调用即可接入任意模型。
        return f"[myecho] {last[::-1]}"

    def available(self) -> bool:
        return True


def shout(args, ctx):
    return (args.get("text", "") or "").upper() + "!!!"


def register(ctx):
    ctx.register_provider("myecho", MyEchoProvider)   # 接入新后端：mnemo --provider myecho
    ctx.tools.add("shout", "把文本变成大写并加感叹号", {"text": "文本"}, shout)
