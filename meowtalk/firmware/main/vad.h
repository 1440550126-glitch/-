#pragma once
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

typedef enum {
    VAD_SILENT,      /* 无叫声 */
    VAD_IN_UTTER,    /* 叫声进行中（已缓存） */
    VAD_UTTER_END,   /* 本帧判定叫声结束，可取走 utterance */
} vad_result_t;

void vad_init(int16_t *utter_buf, size_t utter_buf_samples);
vad_result_t vad_feed(const int16_t *frame, size_t n);

/* VAD_UTTER_END 后调用：取叫声数据与长度（样本数），并复位状态 */
size_t vad_take_utterance(int16_t **out);

/* 最近一帧 RMS（调阈值用） */
int vad_last_rms(void);
