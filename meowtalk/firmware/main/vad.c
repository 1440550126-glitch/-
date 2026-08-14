#include "vad.h"
#include "config.h"
#include <math.h>
#include <string.h>

static int16_t *s_buf;
static size_t   s_cap, s_len;
static int      s_voiced_run, s_silent_run;
static bool     s_active;
static int      s_last_rms;

void vad_init(int16_t *utter_buf, size_t utter_buf_samples)
{
    s_buf = utter_buf;
    s_cap = utter_buf_samples;
    s_len = 0;
    s_voiced_run = s_silent_run = 0;
    s_active = false;
}

static int frame_rms(const int16_t *x, size_t n)
{
    int64_t acc = 0;
    for (size_t i = 0; i < n; i++) acc += (int32_t)x[i] * x[i];
    return (int)sqrtf((float)(acc / (int64_t)n));
}

vad_result_t vad_feed(const int16_t *frame, size_t n)
{
    s_last_rms = frame_rms(frame, n);
    bool voiced = s_last_rms >= VAD_RMS_THRESHOLD;

    if (!s_active) {
        if (voiced) {
            if (++s_voiced_run >= VAD_START_FRAMES) {
                s_active = true;
                s_silent_run = 0;
            }
            /* 预缓存起始帧，避免掐头 */
            if (s_len + n <= s_cap) {
                memcpy(s_buf + s_len, frame, n * sizeof(int16_t));
                s_len += n;
            }
        } else {
            s_voiced_run = 0;
            s_len = 0;
        }
        return s_active ? VAD_IN_UTTER : VAD_SILENT;
    }

    /* 叫声进行中 */
    if (s_len + n <= s_cap) {
        memcpy(s_buf + s_len, frame, n * sizeof(int16_t));
        s_len += n;
    }
    if (voiced) {
        s_silent_run = 0;
    } else if (++s_silent_run >= VAD_END_FRAMES) {
        return VAD_UTTER_END;
    }
    /* 超长截断 */
    if (s_len >= (size_t)(UTTER_MAX_MS * SAMPLE_RATE / 1000)) return VAD_UTTER_END;
    return VAD_IN_UTTER;
}

size_t vad_take_utterance(int16_t **out)
{
    *out = s_buf;
    size_t len = s_len;
    /* 去掉尾部静音窗 */
    size_t tail = (size_t)VAD_END_FRAMES * FRAME_SAMPLES;
    if (len > tail) len -= tail;
    s_len = 0;
    s_active = false;
    s_voiced_run = s_silent_run = 0;
    return len;
}

int vad_last_rms(void) { return s_last_rms; }
