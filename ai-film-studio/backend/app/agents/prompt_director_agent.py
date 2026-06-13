from app.models.studio import Shot, Project
class PromptDirectorAgent:
    def run(self, project: Project, shot: Shot, characters: list, assets: list, memory_context: str, first_frame: str | None) -> dict[str, str]:
        char_lines = "\n".join([f"- 角色ID:{c.id} 名字:{c.name} 脸型/发型/服装:{c.appearance}；{c.costume}；性格:{c.personality}" for c in characters if c.is_selected])
        asset_lines = "\n".join([f"- asset_id:{a.id} {a.asset_type}:{a.name} {a.description}" for a in assets])
        text = f"""[镜头目标]\n{shot.story_goal}\n\n[角色锁定]\n{char_lines}\n必须保持角色脸型一致；必须保持发型一致；必须保持服装一致。\n\n[场景锁定]\nlocation_id:{shot.location_id or 'primary'}\n{asset_lines}\n必须保持建筑一致；必须保持背景一致；必须保持色调一致。\n\n[道具锁定]\n{shot.props_json}\n必须保持道具一致；必须保持动物一致。\n\n[动作]\n{shot.action_instruction}\n\n[摄影机]\n{shot.camera_instruction}\n\n[光线]\n{shot.lighting_instruction}\n\n[风格]\n{project.visual_style}，{project.director_personality}，不使用侵权式模仿。\n\n[首帧参考]\n使用上一镜头尾帧作为本镜头首帧：{first_frame or '第一镜头无上一尾帧'}\n\n[记忆挂点]\n{memory_context or '第一镜头建立角色、建筑、服装、色调基准。'}\n\n[禁止事项]\n不要改变角色脸。\n不要改变角色服装。\n不要改变角色发型。\n不要改变背景。\n不要改变建筑。\n不要改变动物。\n不要改变道具。\n不要突然切换时间。\n不要突然切换画风。\n不要新增无关人物。"""
        return {"prompt_text": text, "negative_prompt": "换脸, 换装, 新增路人, 突然换场景, 改变画风, 道具消失"}
