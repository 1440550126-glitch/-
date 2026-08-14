#pragma once

/* ---------- 引脚（与 docs/cat-translator 接线速查一致） ---------- */
#define PIN_MIC_SCK        4
#define PIN_MIC_WS         5
#define PIN_MIC_SD         6

#define PIN_SPK_BCLK      15
#define PIN_SPK_LRC       16
#define PIN_SPK_DIN       17
#define PIN_SPK_SD_MODE   18   /* 拉高使能功放，拉低关断省电 */

/* ---------- 音频 ---------- */
#define SAMPLE_RATE       16000
#define FRAME_SAMPLES     512          /* 32 ms/帧 */
#define FRAME_HOP         256
#define MIC_SHIFT         14           /* INMP441 32bit 槽位 → 16bit，兼做增益 */

/* ---------- VAD ---------- */
#define VAD_RMS_THRESHOLD    500       /* int16 RMS 触发阈值，环境安静可调小 */
#define VAD_START_FRAMES     3         /* 连续 N 帧有声 → 判定叫声开始 */
#define VAD_END_FRAMES       7         /* 连续 N 帧无声 → 判定叫声结束（约 220ms 尾窗） */
#define UTTER_MIN_MS         150       /* 短于此丢弃（碰撞声等） */
#define UTTER_MAX_MS         3000      /* 长于此截断 */

/* ---------- 叫声合法性（谱质心范围外判为非猫叫） ---------- */
#define MEOW_CENTROID_MIN_HZ 250.0f
#define MEOW_CENTROID_MAX_HZ 3500.0f

/* ---------- 播报策略 ---------- */
#define PLAYBACK_COOLDOWN_MS     500   /* 播完后麦克风冷却，防自触发 */
#define CLASS_REPEAT_SUPPRESS_MS 30000 /* 同类意图 30s 内不重复播报 */
#define VOLUME_SHIFT             1     /* 音量：右移位数，0=最大 1=一半 2=1/4 */
