class RepairAgent:
    def run(self, prompt: str, failure_reasons: str, repair_suggestions: str) -> str:
        return prompt + f"\n\n[自动修复补丁]\n失败原因:{failure_reasons}\n修复建议:{repair_suggestions}\n再次强调：锁定上一镜头尾帧、角色脸型、服装、道具位置、建筑背景、色调。"
