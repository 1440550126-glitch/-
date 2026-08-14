#!/usr/bin/env python3
"""用 CatMeows 数据集训练 3 分类猫叫模型（P1 阶段替换固件规则引擎用）。

数据集: CatMeows — https://zenodo.org/records/4008297 （CC BY 4.0）
  下载解压后目录下应有 dataset/ 内的 .wav，文件名首字母即标签：
    B = brushing（梳毛不满） / F = waiting for food（讨食） / I = isolation（陌生环境不安）

用法:
  pip install tensorflow librosa numpy
  python train_model.py --dataset ./catmeows/dataset --out ./model

输出:
  model/meow_cnn.tflite     — int8 量化模型（TFLite Micro / esp-tflite-micro 可直接用）
  model/meow_model_data.h  — C 数组头文件，可打进固件

也可以不写代码：把同样的 wav 传到 Edge Impulse（MFE + 1D-CNN 模板），
直接导出 ESP32 库，接到 firmware/main/classifier.c 的 classify() 里。
"""
import argparse
from pathlib import Path

import numpy as np

SR = 16000
DURATION_S = 2.0          # 统一裁剪/补零到 2s
N_MELS = 40
LABELS = {"B": 0, "F": 1, "I": 2}
LABEL_NAMES = ["brushing_梳毛不满", "food_讨食", "isolation_陌生环境"]


def load_dataset(root: Path):
    import librosa
    xs, ys = [], []
    files = sorted(root.rglob("*.wav"))
    if not files:
        raise SystemExit(f"{root} 下没有 wav 文件，请先下载 CatMeows 数据集")
    for f in files:
        label = LABELS.get(f.name[0].upper())
        if label is None:
            continue
        y, _ = librosa.load(f, sr=SR, mono=True)
        target = int(SR * DURATION_S)
        y = np.pad(y, (0, max(0, target - len(y))))[:target]
        mel = librosa.feature.melspectrogram(
            y=y, sr=SR, n_fft=512, hop_length=256, n_mels=N_MELS)
        logmel = librosa.power_to_db(mel).astype(np.float32)
        xs.append(logmel[..., None])          # (40, 126, 1)
        ys.append(label)
    print(f"共 {len(xs)} 条样本: " +
          ", ".join(f"{n}={sum(1 for v in ys if v == i)}"
                    for i, n in enumerate(LABEL_NAMES)))
    return np.stack(xs), np.array(ys)


def build_model(input_shape):
    import tensorflow as tf
    L = tf.keras.layers
    return tf.keras.Sequential([
        L.Input(shape=input_shape),
        L.Conv2D(8, 3, activation="relu", padding="same"),
        L.MaxPool2D(2),
        L.Conv2D(16, 3, activation="relu", padding="same"),
        L.MaxPool2D(2),
        L.Conv2D(32, 3, activation="relu", padding="same"),
        L.GlobalAveragePooling2D(),
        L.Dropout(0.3),
        L.Dense(len(LABELS), activation="softmax"),
    ])


def export_tflite(model, x_sample, out_dir: Path):
    import tensorflow as tf

    def rep_data():
        for i in range(min(100, len(x_sample))):
            yield [x_sample[i:i + 1]]

    conv = tf.lite.TFLiteConverter.from_keras_model(model)
    conv.optimizations = [tf.lite.Optimize.DEFAULT]
    conv.representative_dataset = rep_data
    conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    conv.inference_input_type = tf.int8
    conv.inference_output_type = tf.int8
    blob = conv.convert()

    tfl = out_dir / "meow_cnn.tflite"
    tfl.write_bytes(blob)

    lines = [f"0x{b:02x}," for b in blob]
    rows = ["    " + " ".join(lines[i:i + 12]) for i in range(0, len(lines), 12)]
    (out_dir / "meow_model_data.h").write_text(
        "#pragma once\n#include <stdint.h>\n"
        f"/* int8 量化 3 分类猫叫模型, {len(blob)} 字节 */\n"
        f"const unsigned int meow_model_len = {len(blob)};\n"
        "alignas(16) const unsigned char meow_model[] = {\n"
        + "\n".join(rows) + "\n};\n")
    print(f"✅ 导出 {tfl}（{len(blob)/1024:.1f} KB）与 meow_model_data.h")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("model"))
    ap.add_argument("--epochs", type=int, default=60)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    x, y = load_dataset(args.dataset)
    idx = np.random.default_rng(42).permutation(len(x))
    x, y = x[idx], y[idx]
    split = int(len(x) * 0.85)

    model = build_model(x.shape[1:])
    model.compile(optimizer="adam",
                  loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.summary()
    model.fit(x[:split], y[:split], validation_data=(x[split:], y[split:]),
              epochs=args.epochs, batch_size=16)

    loss, acc = model.evaluate(x[split:], y[split:], verbose=0)
    print(f"验证集准确率: {acc:.1%}（CatMeows 三分类文献基线约 80~90%）")
    export_tflite(model, x[:split], args.out)


if __name__ == "__main__":
    main()
