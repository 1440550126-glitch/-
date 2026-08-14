#pragma once
#include "features.h"

/* 类别 ID 与语音包 make_voice_pack.py 的 class_id 一一对应 */
typedef enum {
    MEOW_NONE      = -1,  /* 非猫叫 / 不确定，不播报 */
    MEOW_FOOD      = 0,   /* 讨食 */
    MEOW_ATTENTION = 1,   /* 求关注 */
    MEOW_COMPLAIN  = 2,   /* 不满/抗议 */
    MEOW_CLASS_COUNT = 3,
} meow_class_t;

const char *meow_class_name(meow_class_t c);

/*
 * P0：规则引擎。P1 换真模型时保持本接口不变，
 * 在 classifier.c 内改为调用 Edge Impulse 导出库 / TFLite Micro 即可。
 */
meow_class_t classify(const meow_features_t *f);
