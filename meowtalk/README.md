# 喵语通 MeowTalk · P0 固件（桌面验证版）

「听到猫叫 → 端侧分析意图 → 扬声器实时开口说人话」的最小闭环。
洞洞板/面包板飞线 3 个模块即可跑通，全程离线。

设计方案（外观图 / 框图 / BOM）见 [docs/cat-translator/](../docs/cat-translator/README.md)。

## 硬件与接线（P0 三件套）

| 模块 | 引脚 | 接 ESP32-S3 |
|---|---|---|
| INMP441 麦克风 | VDD / GND | 3V3 / GND |
| | SCK | GPIO4 |
| | WS | GPIO5 |
| | SD | GPIO6 |
| | L/R | GND（左声道） |
| MAX98357A 功放 | VIN / GND | 5V（USB 供电时）或电池正极 / GND |
| | BCLK | GPIO15 |
| | LRC | GPIO16 |
| | DIN | GPIO17 |
| | SD（使能） | GPIO18 |
| | GAIN | 悬空（9 dB） |
| Φ15mm 8Ω 喇叭 | + / − | 功放输出 + / − |

⚠️ 功放 VIN 与 GND 之间**并一颗 220 µF 电容**，否则播报瞬间电流拉不住会失声/复位。

## 构建与烧录

需要 [ESP-IDF 5.2+](https://docs.espressif.com/projects/esp-idf/)：

```bash
cd meowtalk/firmware
idf.py set-target esp32s3
idf.py build flash monitor
```

## 制作并烧录语音包

```bash
cd meowtalk/tools
pip install edge-tts            # 还需要系统装有 ffmpeg
python make_voice_pack.py --phrases phrases.json --out voicepack.bin
# 也可以用自己录的音频：--wav-dir ./my_wavs（文件名 class0_xxx.wav / class1_xxx.wav ...）

# 烧到 voices 分区（parttool.py 随 ESP-IDF 提供）
parttool.py --port /dev/ttyUSB0 write_partition \
    --partition-name voices --input voicepack.bin
```

## 跑起来是什么样

串口 115200，对着麦克风学猫叫（或播放猫叫视频）：

```
I (5210) meowtalk: 🎤 检测到叫声 (612 ms)
I (5290) meowtalk: 特征: 时长=612ms 质心=845Hz 音节=2 走向=上扬
I (5291) meowtalk: 判定: 讨食 (规则引擎)
I (5292) meowtalk: 🔊 播报: class=0 variant=3
I (6104) meowtalk: 播报完成, 冷却 500ms
```

P0 使用**规则引擎**兜底分类（时长/谱质心/音节数/音调走向），不训练模型也能完整跑通闭环。

## 升级为真模型（P1）

```bash
cd meowtalk/tools
python train_model.py --dataset ./catmeows --out model/
```

- 数据集：CatMeows（Zenodo record 4008297，约 440 条标注猫叫：讨食 / 陌生环境 / 梳毛）；
- 脚本输出 int8 量化的 `model.tflite` + C 头文件，或直接用 [Edge Impulse](https://edgeimpulse.com/) 训练后导出 ESP32 库，
  替换 `firmware/main/classifier.c` 中 `classify_rules()` 的调用点即可（接口已预留，见 `classifier.h`）。

## 常见问题

- **没声音**：查 GPIO18（SD 使能）是否接对；220 µF 是否并上；GAIN 悬空。
- **自己触发自己**：正常现象已由固件防护（播报期间关麦 + 500 ms 冷却）；若仍误触发，调大 `config.h` 里 `VAD_RMS_THRESHOLD`。
- **一直不触发**：串口看 `rms=` 调试值，调小阈值；确认 INMP441 的 L/R 接了 GND。
- **同一类叫声不重复播**：设计如此（30 s 同类抑制），改 `config.h` 的 `CLASS_REPEAT_SUPPRESS_MS`。
