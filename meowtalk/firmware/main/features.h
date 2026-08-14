#pragma once
#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"

typedef struct {
    int   duration_ms;      /* 叫声时长 */
    float mean_centroid_hz; /* 平均谱质心 */
    float centroid_slope;   /* 音调走向：尾段质心 - 首段质心 (Hz)，>0 上扬 */
    int   syllables;        /* 音节数（能量包络峰数，"喵~喵~"=2） */
    float peak_hz;          /* 100~1000Hz 内主频（基频粗估） */
} meow_features_t;

esp_err_t features_init(void);
esp_err_t features_extract(const int16_t *pcm, size_t n, meow_features_t *out);
