#include "audio_io.h"
#include "config.h"

#include <string.h>
#include "driver/i2s_std.h"
#include "driver/gpio.h"
#include "esp_check.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "audio_io";

static i2s_chan_handle_t s_rx;   /* INMP441 */
static i2s_chan_handle_t s_tx;   /* MAX98357A */
static int32_t s_raw[FRAME_SAMPLES];

esp_err_t audio_io_init(void)
{
    /* 功放使能脚，默认关断 */
    gpio_config_t io = {
        .pin_bit_mask = 1ULL << PIN_SPK_SD_MODE,
        .mode = GPIO_MODE_OUTPUT,
    };
    ESP_RETURN_ON_ERROR(gpio_config(&io), TAG, "gpio");
    gpio_set_level(PIN_SPK_SD_MODE, 0);

    /* RX：麦克风，32bit 槽位、左声道 */
    i2s_chan_config_t rx_chan = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    ESP_RETURN_ON_ERROR(i2s_new_channel(&rx_chan, NULL, &s_rx), TAG, "rx chan");
    i2s_std_config_t rx_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT,
                                                        I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .bclk = PIN_MIC_SCK,
            .ws   = PIN_MIC_WS,
            .din  = PIN_MIC_SD,
            .mclk = I2S_GPIO_UNUSED,
            .dout = I2S_GPIO_UNUSED,
        },
    };
    rx_cfg.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT;
    ESP_RETURN_ON_ERROR(i2s_channel_init_std_mode(s_rx, &rx_cfg), TAG, "rx init");
    ESP_RETURN_ON_ERROR(i2s_channel_enable(s_rx), TAG, "rx en");

    /* TX：功放，16bit 单声道（98357 内部混合 L/R） */
    i2s_chan_config_t tx_chan = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_MASTER);
    ESP_RETURN_ON_ERROR(i2s_new_channel(&tx_chan, &s_tx, NULL), TAG, "tx chan");
    i2s_std_config_t tx_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT,
                                                        I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .bclk = PIN_SPK_BCLK,
            .ws   = PIN_SPK_LRC,
            .dout = PIN_SPK_DIN,
            .mclk = I2S_GPIO_UNUSED,
            .din  = I2S_GPIO_UNUSED,
        },
    };
    ESP_RETURN_ON_ERROR(i2s_channel_init_std_mode(s_tx, &tx_cfg), TAG, "tx init");
    return ESP_OK;
}

esp_err_t mic_read(int16_t *dst, size_t n_samples)
{
    size_t need = n_samples * sizeof(int32_t), got = 0;
    ESP_RETURN_ON_ERROR(i2s_channel_read(s_rx, s_raw, need, &got, portMAX_DELAY),
                        TAG, "read");
    size_t n = got / sizeof(int32_t);
    for (size_t i = 0; i < n; i++) {
        int32_t v = s_raw[i] >> MIC_SHIFT;
        if (v > INT16_MAX) v = INT16_MAX;
        if (v < INT16_MIN) v = INT16_MIN;
        dst[i] = (int16_t)v;
    }
    return ESP_OK;
}

void mic_pause(void)  { i2s_channel_disable(s_rx); }

void mic_resume(void)
{
    i2s_channel_enable(s_rx);
    /* 丢掉禁用期间残留的 DMA 数据 */
    int16_t junk[FRAME_SAMPLES];
    for (int i = 0; i < 4; i++) mic_read(junk, FRAME_SAMPLES);
}

esp_err_t spk_play(const int16_t *pcm, size_t n_samples)
{
    static int16_t chunk[1024];
    gpio_set_level(PIN_SPK_SD_MODE, 1);
    vTaskDelay(pdMS_TO_TICKS(10));            /* 功放上电稳定 */
    ESP_RETURN_ON_ERROR(i2s_channel_enable(s_tx), TAG, "tx en");

    size_t off = 0;
    while (off < n_samples) {
        size_t n = n_samples - off;
        if (n > 1024) n = 1024;
        for (size_t i = 0; i < n; i++) chunk[i] = pcm[off + i] >> VOLUME_SHIFT;
        size_t written = 0;
        i2s_channel_write(s_tx, chunk, n * sizeof(int16_t), &written, portMAX_DELAY);
        off += n;
    }
    vTaskDelay(pdMS_TO_TICKS(20));            /* 等 DMA 排空 */
    i2s_channel_disable(s_tx);
    gpio_set_level(PIN_SPK_SD_MODE, 0);
    return ESP_OK;
}
