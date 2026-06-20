#!/usr/bin/env python3
# 兽灵切图：处理"透明棋盘格被烤进 JPEG"的精灵表
# 思路：边缘洪泛去近白棋盘格(保留体内白) -> 列投影分出各姿势 -> 导出 RGBA 透明 PNG
import os, sys, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ART = os.path.dirname(os.path.abspath(__file__)); RAW = f"{ART}/raw"
T = 233           # 近白阈值（棋盘格两色≈240/252，均≥233；前景墨线<233）
MIN_BLOB = 500    # 小于此面积的前景碎块视作噪点丢弃

def close_gaps(on, g):
    on = on.copy(); N = len(on); i = 0
    while i < N:
        if not on[i]:
            j = i
            while j < N and not on[j]: j += 1
            if i > 0 and j < N and j - i <= g: on[i:j] = True
            i = j
        else: i += 1
    return on

def cut(path, n=4):
    img = Image.open(path).convert("RGB"); a = np.asarray(img); H, W = a.shape[:2]
    light = a.min(2) >= T                                  # 近白候选（含棋盘格两色）
    lbl, _ = ndimage.label(light)
    border = set(np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))) - {0}
    exterior = np.isin(lbl, list(border)) if border else np.zeros((H, W), bool)
    fg = ~exterior
    fl, fn = ndimage.label(fg)                              # 去前景小噪点
    sizes = np.bincount(fl.ravel())
    keep = np.where(sizes >= MIN_BLOB)[0]; keep = keep[keep != 0]
    fg = np.isin(fl, keep)
    fg = ndimage.binary_fill_holes(fg)                      # 补体内小洞
    alpha = np.where(fg, 255, 0).astype(np.uint8)
    rgba = np.dstack([a, alpha])
    # 按已知数量 n 分割：在每个预期分界附近找投影最低谷切开（对灵气搭桥免疫）
    col = np.convolve(fg.sum(0).astype(float), np.ones(15) / 15, "same")
    cuts = [0]
    for i in range(1, n):
        c = int(W * i / n); win = int(W * 0.13)
        lo, hi = max(1, c - win), min(W - 1, c + win)
        cuts.append(lo + int(np.argmin(col[lo:hi])))
    cuts.append(W)
    poses = []
    for i in range(n):
        seg = fg[:, cuts[i]:cuts[i + 1]]
        xs = np.where(seg.any(0))[0]; ys = np.where(seg.any(1))[0]
        if len(xs) == 0: continue
        x0, x1 = cuts[i] + xs[0], cuts[i] + xs[-1] + 1
        y0, y1 = ys[0], ys[-1] + 1
        pad = 6
        poses.append(Image.fromarray(
            rgba[max(0, y0 - pad):min(H, y1 + pad), max(0, x0 - pad):min(W, x1 + pad)], "RGBA"))
    return poses

def checker(w, h, s=12):
    yy, xx = np.mgrid[0:h, 0:w]
    base = np.where(((xx // s + yy // s) % 2) == 0, 235, 205).astype(np.uint8)
    return Image.fromarray(np.dstack([base] * 3), "RGB")

def montage(rows, out, cell=300):
    cols = max(len(r) for _, r in rows); pad, lab = 12, 20
    W = cols * (cell + pad) + pad; Hh = len(rows) * (cell + pad + lab) + pad
    canvas = Image.new("RGB", (W, Hh), (250, 250, 250)); d = ImageDraw.Draw(canvas)
    for ri, (name, imgs) in enumerate(rows):
        y = pad + ri * (cell + pad + lab); d.text((pad, y), name, fill=(20, 20, 20))
        for ci, im in enumerate(imgs):
            x = pad + ci * (cell + pad); t = im.copy(); t.thumbnail((cell, cell))
            bg = checker(cell, cell); ox, oy = (cell - t.width) // 2, (cell - t.height) // 2
            bg.paste(t, (ox, oy), t); canvas.paste(bg, (x, y + lab))
    canvas.save(out); print("预览:", out, canvas.size)

if __name__ == "__main__":
    files = sys.argv[1:] or [f"{RAW}/beast_{n}.jpg" for n in ["dragon", "eagle", "bear", "wolf", "tiger"]]
    rows = []
    for p in files:
        name = os.path.splitext(os.path.basename(p))[0].replace("beast_", "")
        poses = cut(p)
        d = f"{ART}/sprites/beasts/{name}"; os.makedirs(d, exist_ok=True)
        for i, im in enumerate(poses, 1):
            im.save(f"{d}/action_{i:02d}.png")
        print(f"{name}: {len(poses)} 姿势 -> sprites/beasts/{name}/action_*.png  尺寸={[im.size for im in poses]}")
        rows.append((name, poses))
    montage(rows, f"{ART}/_preview_beasts.png")
