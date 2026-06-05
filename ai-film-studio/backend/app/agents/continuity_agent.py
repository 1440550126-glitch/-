class ContinuityAgent:
    def run(self, shot_number: int, retry_count: int, pass_score: int) -> dict:
        base = 82 if shot_number % 4 == 0 and retry_count == 0 else 92
        scores = {"character_score": base+1, "background_score": base, "costume_score": base+2, "prop_score": base, "color_score": base+1, "transition_score": base}
        total = sum(scores.values()) / len(scores)
        return {**scores, "total_score": total, "passed": total >= pass_score, "failure_reasons": "首尾帧衔接和道具位置略有漂移" if total < pass_score else "", "repair_suggestions": "强化上一尾帧、道具位置、服装锁定和青金色调" if total < pass_score else "已通过"}
