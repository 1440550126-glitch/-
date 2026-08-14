#include "classifier.h"
#include "config.h"

const char *meow_class_name(meow_class_t c)
{
    switch (c) {
    case MEOW_FOOD:      return "讨食";
    case MEOW_ATTENTION: return "求关注";
    case MEOW_COMPLAIN:  return "不满/抗议";
    default:             return "非猫叫";
    }
}

/*
 * P0 规则引擎：
 *   - 谱质心在猫叫范围外 → 拒识（开关门、碰撞、人声低频轰鸣大多在范围外）
 *   - 多音节且音调上扬（"喵~喵~"重复上行）→ 讨食
 *   - 长叫 + 低质心 + 不上扬（拖长的低嚎）→ 不满/抗议
 *   - 其余短促叫 → 求关注
 */
meow_class_t classify(const meow_features_t *f)
{
    if (f->duration_ms < UTTER_MIN_MS) return MEOW_NONE;
    if (f->mean_centroid_hz < MEOW_CENTROID_MIN_HZ ||
        f->mean_centroid_hz > MEOW_CENTROID_MAX_HZ) return MEOW_NONE;

    if (f->syllables >= 2 && f->centroid_slope > 0) return MEOW_FOOD;

    if (f->duration_ms > 800 && f->mean_centroid_hz < 700.0f &&
        f->centroid_slope <= 0) return MEOW_COMPLAIN;

    return MEOW_ATTENTION;
}
