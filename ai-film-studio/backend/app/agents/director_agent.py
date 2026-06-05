from app.models.studio import Project
class DirectorAgent:
    def run(self, project: Project) -> dict[str, str]:
        return {"world_view": f"《{project.title}》发生在一个以{project.visual_style}统一管理的60秒高概念世界。", "core_hook": "普通人必须在一分钟内完成一次改变命运的选择。", "tone": "节奏清晰，情绪递进，兼顾商业可看性与视觉统一。", "emotion_curve": "0-15秒建立目标，15-35秒升级冲突，35-50秒爆发，50-60秒余韵。", "director_notes": f"导演性格：{project.director_personality}；所有镜头服务于明确钩子。", "visual_rules": "固定主色调、固定服装轮廓、固定主场景空间关系；不使用侵权模仿。", "negative_rules": "禁止突然换脸、换装、换建筑、换画风、加入无关人物。"}
