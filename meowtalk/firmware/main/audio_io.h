#pragma once
#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"

esp_err_t audio_io_init(void);

/* 阻塞读取 n 个 16bit 单声道采样（已完成 32→16bit 转换） */
esp_err_t mic_read(int16_t *dst, size_t n_samples);

/* 播报期间关麦（禁用 RX 通道），结束后重开并丢弃陈旧 DMA 数据 */
void mic_pause(void);
void mic_resume(void);

/* 阻塞播放 16bit 单声道 PCM，内部按 VOLUME_SHIFT 缩放并控制功放使能 */
esp_err_t spk_play(const int16_t *pcm, size_t n_samples);
