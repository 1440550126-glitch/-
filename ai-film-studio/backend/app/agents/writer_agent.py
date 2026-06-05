from app.models.studio import StoryBible
class WriterAgent:
    def run(self, bible: StoryBible) -> dict:
        return {"synopsis": f"主角在{bible.world_view}中追逐核心信念，最终用一次行动证明主题。", "three_act_structure": {"act1": "建立角色与目标", "act2": "对抗阻力并付出代价", "act3": "完成选择并留下反转余味"}, "scene_script": {"scene1": "主场景开场", "scene2": "备用场景制造压力", "scene3": "回到主场景完成爆发"}, "dialogue": {"hero": "如果只剩一分钟，我也要把答案留下。"}, "shot_outline": {"count": 10, "duration": "每镜头4-8秒"}}
