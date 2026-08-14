#include "voice.h"
#include "audio_io.h"

#include <string.h>
#include "esp_partition.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_random.h"

static const char *TAG = "voice";

/* 与 tools/make_voice_pack.py 的打包格式严格对应（小端） */
#define VP_MAGIC "MVPK"

typedef struct __attribute__((packed)) {
    char     magic[4];
    uint16_t version;
    uint16_t count;
} vp_header_t;

typedef struct __attribute__((packed)) {
    uint8_t  class_id;
    uint8_t  flags;
    uint16_t pad;
    uint32_t offset;   /* 相对分区起始 */
    uint32_t length;   /* 字节数（PCM16 mono 16kHz） */
} vp_entry_t;

#define VP_MAX_ENTRIES 256

static const esp_partition_t *s_part;
static const uint8_t *s_mmap;          /* 分区只读映射基址 */
static vp_entry_t s_entries[VP_MAX_ENTRIES];
static int s_count;

esp_err_t voice_init(void)
{
    s_part = esp_partition_find_first(ESP_PARTITION_TYPE_DATA, 0x40, "voices");
    ESP_RETURN_ON_FALSE(s_part, ESP_ERR_NOT_FOUND, TAG, "voices 分区不存在");

    esp_partition_mmap_handle_t h;
    const void *base;
    ESP_RETURN_ON_ERROR(esp_partition_mmap(s_part, 0, s_part->size,
                                           ESP_PARTITION_MMAP_DATA, &base, &h),
                        TAG, "mmap");
    s_mmap = base;

    const vp_header_t *hd = (const vp_header_t *)s_mmap;
    ESP_RETURN_ON_FALSE(memcmp(hd->magic, VP_MAGIC, 4) == 0, ESP_ERR_INVALID_STATE,
                        TAG, "语音包未烧录或损坏（magic 不符），见 meowtalk/README.md");
    s_count = hd->count < VP_MAX_ENTRIES ? hd->count : VP_MAX_ENTRIES;
    memcpy(s_entries, s_mmap + sizeof(vp_header_t), s_count * sizeof(vp_entry_t));
    ESP_LOGI(TAG, "语音包已加载: %d 条语音", s_count);
    return ESP_OK;
}

int voice_play(meow_class_t cls)
{
    int idx[VP_MAX_ENTRIES], n = 0;
    for (int i = 0; i < s_count; i++)
        if (s_entries[i].class_id == (uint8_t)cls) idx[n++] = i;
    if (n == 0) {
        ESP_LOGW(TAG, "类别 %d 无语音", cls);
        return -1;
    }
    int pick = idx[esp_random() % n];
    const vp_entry_t *e = &s_entries[pick];
    spk_play((const int16_t *)(s_mmap + e->offset), e->length / sizeof(int16_t));
    return pick;
}
