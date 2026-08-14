#include "features.h"
#include "config.h"

#include <math.h>
#include <string.h>
#include "esp_dsp.h"
#include "esp_check.h"
#include "esp_heap_caps.h"

static const char *TAG = "features";

#define NFFT       FRAME_SAMPLES          /* 512 */
#define NBINS      (NFFT / 2)
#define MAX_FRAMES (UTTER_MAX_MS * SAMPLE_RATE / 1000 / FRAME_HOP + 2)
#define HZ_PER_BIN ((float)SAMPLE_RATE / NFFT)

static float *s_fft;        /* 复数交错 2*NFFT */
static float  s_win[NFFT];
static float  s_energy[MAX_FRAMES];
static float  s_centroid[MAX_FRAMES];

esp_err_t features_init(void)
{
    s_fft = heap_caps_malloc(2 * NFFT * sizeof(float), MALLOC_CAP_DEFAULT);
    ESP_RETURN_ON_FALSE(s_fft, ESP_ERR_NO_MEM, TAG, "fft buf");
    ESP_RETURN_ON_ERROR(dsps_fft2r_init_fc32(NULL, NFFT), TAG, "fft init");
    dsps_wind_hann_f32(s_win, NFFT);
    return ESP_OK;
}

/* 单帧：加窗 FFT → 功率谱 → 能量 / 谱质心 / 主频 */
static void analyze_frame(const int16_t *x, float *energy, float *centroid, float *peak_hz)
{
    for (int i = 0; i < NFFT; i++) {
        s_fft[2 * i]     = (float)x[i] * s_win[i];
        s_fft[2 * i + 1] = 0.0f;
    }
    dsps_fft2r_fc32(s_fft, NFFT);
    dsps_bit_rev_fc32(s_fft, NFFT);

    float e = 0, num = 0, den = 1e-9f;
    float pk = 0, pk_hz = 0;
    int lo = (int)(100.0f / HZ_PER_BIN), hi = (int)(1000.0f / HZ_PER_BIN);
    for (int k = 1; k < NBINS; k++) {
        float re = s_fft[2 * k], im = s_fft[2 * k + 1];
        float p = re * re + im * im;
        float f = k * HZ_PER_BIN;
        e += p;
        num += f * p;
        den += p;
        if (k >= lo && k <= hi && p > pk) { pk = p; pk_hz = f; }
    }
    *energy = e;
    *centroid = num / den;
    *peak_hz = pk_hz;
}

esp_err_t features_extract(const int16_t *pcm, size_t n, meow_features_t *out)
{
    memset(out, 0, sizeof(*out));
    if (n < NFFT) return ESP_ERR_INVALID_SIZE;

    int frames = 0;
    float peak_sum = 0;
    for (size_t off = 0; off + NFFT <= n && frames < MAX_FRAMES; off += FRAME_HOP) {
        float pk;
        analyze_frame(pcm + off, &s_energy[frames], &s_centroid[frames], &pk);
        peak_sum += pk;
        frames++;
    }

    out->duration_ms = (int)(n * 1000 / SAMPLE_RATE);
    out->peak_hz = peak_sum / frames;

    /* 平均谱质心（能量加权） */
    float csum = 0, esum = 1e-9f;
    float emax = 0;
    for (int i = 0; i < frames; i++) {
        csum += s_centroid[i] * s_energy[i];
        esum += s_energy[i];
        if (s_energy[i] > emax) emax = s_energy[i];
    }
    out->mean_centroid_hz = csum / esum;

    /* 音调走向：末 1/3 与首 1/3 的质心差 */
    int third = frames / 3;
    if (third > 0) {
        float head = 0, tail = 0;
        for (int i = 0; i < third; i++) head += s_centroid[i];
        for (int i = frames - third; i < frames; i++) tail += s_centroid[i];
        out->centroid_slope = (tail - head) / third;
    }

    /* 音节数：能量包络过峰计数（>50% 峰值起算，跌破 20% 复位） */
    bool above = false;
    int syl = 0;
    for (int i = 0; i < frames; i++) {
        if (!above && s_energy[i] > 0.5f * emax) { above = true; syl++; }
        else if (above && s_energy[i] < 0.2f * emax) { above = false; }
    }
    out->syllables = syl;
    return ESP_OK;
}
