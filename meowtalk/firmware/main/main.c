/*
 * 喵语通 MeowTalk · P0 桌面验证固件
 * 闭环：麦克风 → VAD → 特征 → 分类 → 扬声器播报（全程离线）
 * 设计方案见 docs/cat-translator/README.md
 */
#include <inttypes.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"

#include "config.h"
#include "audio_io.h"
#include "vad.h"
#include "features.h"
#include "classifier.h"
#include "voice.h"

static const char *TAG = "meowtalk";

#define UTTER_BUF_SAMPLES (UTTER_MAX_MS * SAMPLE_RATE / 1000)

static int64_t s_last_play_ms[MEOW_CLASS_COUNT];

static void meow_loop(void *arg)
{
    static int16_t frame[FRAME_SAMPLES];
    int16_t *utter_buf = heap_caps_malloc(UTTER_BUF_SAMPLES * sizeof(int16_t),
                                          MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
    if (!utter_buf) {
        ESP_LOGE(TAG, "PSRAM 分配失败");
        vTaskDelete(NULL);
    }
    vad_init(utter_buf, UTTER_BUF_SAMPLES);

    bool voice_ok = (voice_init() == ESP_OK);
    if (!voice_ok)
        ESP_LOGW(TAG, "语音包不可用，将只打印识别结果不播报");

    ESP_LOGI(TAG, "开始监听... (VAD 阈值=%d)", VAD_RMS_THRESHOLD);

    while (1) {
        if (mic_read(frame, FRAME_SAMPLES) != ESP_OK) continue;
        if (vad_feed(frame, FRAME_SAMPLES) != VAD_UTTER_END) continue;

        int16_t *pcm;
        size_t n = vad_take_utterance(&pcm);
        int dur_ms = (int)(n * 1000 / SAMPLE_RATE);
        if (dur_ms < UTTER_MIN_MS) continue;
        ESP_LOGI(TAG, "🎤 检测到叫声 (%d ms)", dur_ms);

        meow_features_t f;
        if (features_extract(pcm, n, &f) != ESP_OK) continue;
        ESP_LOGI(TAG, "特征: 时长=%dms 质心=%.0fHz 音节=%d 走向=%s 主频=%.0fHz",
                 f.duration_ms, f.mean_centroid_hz, f.syllables,
                 f.centroid_slope > 0 ? "上扬" : "下行", f.peak_hz);

        meow_class_t cls = classify(&f);
        ESP_LOGI(TAG, "判定: %s (规则引擎)", meow_class_name(cls));
        if (cls == MEOW_NONE) continue;

        /* 同类 30s 抑制：猫连环叫只翻译第一声 */
        int64_t now = esp_timer_get_time() / 1000;
        if (s_last_play_ms[cls] &&
            now - s_last_play_ms[cls] < CLASS_REPEAT_SUPPRESS_MS) {
            ESP_LOGI(TAG, "同类 %" PRId64 "s 前刚播过，本次静默",
                     (now - s_last_play_ms[cls]) / 1000);
            continue;
        }

        if (voice_ok) {
            /* 防自触发：播报期间关麦 + 冷却 */
            mic_pause();
            int variant = voice_play(cls);
            ESP_LOGI(TAG, "🔊 播报: class=%d variant=%d", cls, variant);
            vTaskDelay(pdMS_TO_TICKS(PLAYBACK_COOLDOWN_MS));
            mic_resume();
            ESP_LOGI(TAG, "播报完成, 冷却 %dms", PLAYBACK_COOLDOWN_MS);
        }
        s_last_play_ms[cls] = now;
    }
}

void app_main(void)
{
    ESP_ERROR_CHECK(audio_io_init());
    ESP_ERROR_CHECK(features_init());
    xTaskCreatePinnedToCore(meow_loop, "meow", 8192, NULL, 5, NULL, 1);
}
