"""digital-soul：完全本地运行的"数字分身"智能体框架。

它不是"意识上传"，而是一个会用你的性格、记忆和关系来对话与行动的本地智能体：
认识你的人、记得你的经历、知道听谁的不听谁的，并可接入机器人执行动作。
"""

from .loader import build_agent

__all__ = ["build_agent"]
__version__ = "0.1.0"
