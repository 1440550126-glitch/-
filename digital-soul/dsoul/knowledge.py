"""领域知识调度：让分身稳定地用多学科视角思考。

⚠️ 诚实说明：**真正的知识深度来自本地大模型**；本模块做的是"调用哪套思维框架"，
并可把你自己的资料（config/knowledge/*.md）作为参考接进来。它不等于"训练成专家"。
"""

from __future__ import annotations

DOMAINS = {
    "心理学": "用共情、认知行为、依恋理论理解情绪与行为",
    "哲学": "用伦理、存在与逻辑思辨探讨意义",
    "生物学": "懂人体与作息、健康的基本机制",
    "医学": "能给一般健康建议（重症务必就医，不替代医生）",
    "恋爱": "懂沟通、边界与亲密关系经营",
    "社会学": "理解群体、文化与关系网络对人的影响",
    "经济学": "用成本收益、激励与理财常识帮你决策",
}


class Knowledge:
    def __init__(self, domains=None) -> None:
        self.domains = list(domains) if domains else list(DOMAINS)

    def prompt_hint(self) -> str:
        ds = [d for d in self.domains if d in DOMAINS]
        if not ds:
            return ""
        body = "；".join(f"{d}（{DOMAINS[d]}）" for d in ds)
        return (
            "你博学且会融会贯通，需要时自然地调用这些学科的思维来帮我：" + body + "。"
            "给医疗/法律/投资等专业建议时要负责、提示风险，必要时建议咨询专业人士。"
        )
