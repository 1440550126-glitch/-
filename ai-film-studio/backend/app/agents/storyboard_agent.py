class StoryboardAgent:
    def run(self) -> list[dict]:
        durations = [6,6,5,6,6,5,6,6,7,7]
        return [{"shot_number": i+1, "duration_seconds": d, "story_goal": f"镜头{i+1}推进60秒短片核心冲突", "characters_json": ["男主候选A", "女主候选A"] if i%2==0 else ["男主候选A", "反派候选A"], "location_id": None, "props_json": ["prop_key_01"] if i<5 else ["prop_token_02"], "camera_instruction": "中近景推轨，方向保持由左向右", "action_instruction": "角色完成可连续衔接的动作，不突变走位", "lighting_instruction": "青金色主光，柔和环境光，阴影方向固定"} for i,d in enumerate(durations)]
