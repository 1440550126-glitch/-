#pragma once
#include "esp_err.h"
#include "classifier.h"

/* 从 voices 分区加载语音包索引（格式见 tools/make_voice_pack.py） */
esp_err_t voice_init(void);

/* 随机挑该类别下一条语音并阻塞播放；返回播放的 variant 序号，无可用返回 -1 */
int voice_play(meow_class_t cls);
