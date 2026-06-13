class CastingAgent:
    def run(self) -> list[dict]:
        roles = ["男主", "女主", "反派", "配角", "动物/怪物"]
        return [{"role_type": role, "name": f"{role}候选A", "personality": "目标明确，情绪可被镜头读取", "appearance": "稳定脸型，明确发型和标志物", "costume": "统一服装轮廓与主色块", "voice_profile": "清晰、有辨识度", "score": 92 - i} for i, role in enumerate(roles)] + [{"role_type": "男主", "name": "男主候选B", "personality": "更文艺内敛", "appearance": "窄脸、短发", "costume": "深灰夹克", "voice_profile": "低沉", "score": 81}]
