"""示例插件入口。被加载时，Mnemo 会调用 register(ctx)。

ctx 提供：
  ctx.tools              —— ToolRegistry，.add(name, desc, params, func, danger=False)
  ctx.skills             —— SkillRegistry，.add_runtime(Skill(...))
  ctx.config             —— 配置
  ctx.register_provider  —— register_provider(name, ProviderClass) 接入新大模型
"""
import random


def coin_flip(args, ctx):
    """工具函数签名固定为 (args: dict, ctx: ToolContext) -> str。"""
    n = int(args.get("times", 1))
    return " ".join(random.choice(["正面", "反面"]) for _ in range(max(1, min(n, 20))))


def register(ctx):
    ctx.tools.add(
        name="coin_flip",
        description="抛硬币，返回正面/反面",
        parameters={"times": "抛几次，默认 1"},
        func=coin_flip,
    )
    # 也可以在此 ctx.register_provider("my_llm", MyProvider) 接入任意大模型后端
