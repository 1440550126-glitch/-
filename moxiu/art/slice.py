#!/usr/bin/env python3
# 《墨修》精灵表切图：投影分割 -> 单体裁剪 -> 角色边缘洪泛抠白底（保留内部白），场景保留白底裁剪
import os, numpy as np
from PIL import Image
from scipy import ndimage

ART = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ART, "raw")

# ---------- 1D 投影分割 ----------
def close_gaps(on, max_gap):
    on = on.copy(); N = len(on); i = 0
    while i < N:
        if not on[i]:
            j = i
            while j < N and not on[j]: j += 1
            if i > 0 and j < N and (j - i) <= max_gap: on[i:j] = True
            i = j
        else: i += 1
    return on

def spans(profile, thresh, min_len, max_gap):
    on = close_gaps(profile > thresh, max_gap)
    out = []; N = len(on); i = 0
    while i < N:
        if on[i]:
            j = i
            while j < N and on[j]: j += 1
            if j - i >= min_len: out.append((i, j))
            i = j
        else: i += 1
    return out

def content_mask(arr):                      # 非白即内容（白底 JPEG 取 244 阈值）
    return ~np.all(arr >= 244, axis=2)

def tight_bbox(sub_mask):
    ys = np.where(sub_mask.any(1))[0]; xs = np.where(sub_mask.any(0))[0]
    if len(ys) == 0 or len(xs) == 0: return None
    return xs[0], ys[0], xs[-1] + 1, ys[-1] + 1

def trim(im, pad=6):                              # 裁到内容紧边
    bb = tight_bbox(content_mask(np.asarray(im.convert("RGB"))))
    if not bb: return im
    x0, y0, x1, y1 = bb
    return im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)))

def split_block(crop, k):                         # 把竖向堆叠的 k 张场景按内容谷值切开
    m = content_mask(np.asarray(crop.convert("RGB"))); H, W = m.shape
    prof = np.convolve(m.sum(1).astype(float), np.ones(9) / 9, "same")
    cuts = [0]
    for i in range(1, k):
        c = int(H * i / k); win = int(H * 0.13)
        lo, hi = max(1, c - win), min(H - 1, c + win)
        cuts.append(lo + int(np.argmin(prof[lo:hi])))
    cuts.append(H)
    return [trim(crop.crop((0, cuts[i], W, cuts[i + 1]))) for i in range(k)]

# ---------- 角色抠白底：连通到边缘的近白像素 -> 透明 ----------
def cut_alpha(crop):
    a = np.asarray(crop.convert("RGB")).astype(np.int16)
    nearwhite = np.all(a >= 240, axis=2)
    lbl, n = ndimage.label(nearwhite)               # 4-连通白区域
    border = set(np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))) - {0}
    outside = np.isin(lbl, list(border)) if border else np.zeros_like(nearwhite)
    alpha = np.where(outside, 0, 255).astype(np.uint8)
    rgba = np.dstack([np.asarray(crop.convert("RGB")), alpha])
    return Image.fromarray(rgba, "RGBA")

# ---------- 切一张表 ----------
def slice_sheet(path, char_dir, scene_dir, char_prefix, scene_prefix):
    img = Image.open(path).convert("RGB"); arr = np.asarray(img); H, W = arr.shape[:2]
    mask = content_mask(arr)
    bands = spans(mask.sum(1), thresh=max(6, int(0.004 * W)), min_len=45, max_gap=14)
    os.makedirs(char_dir, exist_ok=True); os.makedirs(scene_dir, exist_ok=True)
    chars, scenes = [], []
    print(f"\n=== {os.path.basename(path)}  {W}x{H} · {len(bands)} 个横向条带 ===")
    for bi, (y0, y1) in enumerate(bands):
        band = mask[y0:y1]
        cells = spans(band.sum(0), thresh=max(6, int(0.004 * (y1 - y0))), min_len=40, max_gap=14)
        for (x0, x1) in cells:
            bb = tight_bbox(mask[y0:y1, x0:x1])
            if not bb: continue
            cx0, cy0, cx1, cy1 = bb
            ax0, ay0, ax1, ay1 = x0 + cx0, y0 + cy0, x0 + cx1, y0 + cy1
            w, h = ax1 - ax0, ay1 - ay0
            if w * h < 2500 or w < 24 or h < 24: continue          # 丢弃碎片
            pad = 8
            px0, py0 = max(0, ax0 - pad), max(0, ay0 - pad)
            px1, py1 = min(W, ax1 + pad), min(H, ay1 + pad)
            crop = img.crop((px0, py0, px1, py1))
            if h > 460:                                            # 竖向堆叠的多张场景（无白缝）
                k = max(1, round(h / (w * 0.6)))
                scenes.extend(split_block(crop, k))
            elif h > w * 1.05:                                     # 竖图 -> 角色
                chars.append(crop)
            elif w >= 150 and h >= 150:                            # 宽图且非残片 -> 场景
                scenes.append(crop)
            # 其余（被生成截断的残片）丢弃
    for i, c in enumerate(chars, 1):
        cut_alpha(c).save(os.path.join(char_dir, f"{char_prefix}_{i:02d}.png"))
    for i, s in enumerate(scenes, 1):
        s.save(os.path.join(scene_dir, f"{scene_prefix}_{i:02d}.png"))
    print(f"  角色 {len(chars)} 张 -> {char_dir}/{char_prefix}_*.png")
    print(f"  场景 {len(scenes)} 张 -> {scene_dir}/{scene_prefix}_*.png")
    for i, c in enumerate(chars, 1): print(f"    char {i:02d}: {c.size}")
    for i, s in enumerate(scenes, 1): print(f"    scene {i:02d}: {s.size}")
    return chars, scenes

# ---------- 预览拼图（棋盘格底显示透明）----------
def checker(w, h, s=12):
    yy, xx = np.mgrid[0:h, 0:w]
    base = np.where(((xx // s + yy // s) % 2) == 0, 235, 205).astype(np.uint8)
    return Image.fromarray(np.dstack([base] * 3), "RGB")

def montage(imgs, cols, cell, title, transparent, out):
    rows = (len(imgs) + cols - 1) // cols
    pad, lab = 10, 18
    cw, ch = cell, cell
    W, H = cols * (cw + pad) + pad, rows * (ch + pad + lab) + pad + 24
    canvas = Image.new("RGB", (W, H), (250, 250, 250))
    from PIL import ImageDraw
    d = ImageDraw.Draw(canvas); d.text((pad, 6), title, fill=(20, 20, 20))
    for k, im in enumerate(imgs):
        r, c = divmod(k, cols)
        x = pad + c * (cw + pad); y = 24 + pad + r * (ch + pad + lab)
        t = im.copy(); t.thumbnail((cw, ch))
        bg = checker(cw, ch) if transparent else Image.new("RGB", (cw, ch), (255, 255, 255))
        ox, oy = (cw - t.width) // 2, (ch - t.height) // 2
        if t.mode == "RGBA": bg.paste(t, (ox, oy), t)
        else: bg.paste(t, (ox, oy))
        canvas.paste(bg, (x, y))
        d.text((x, y + ch + 2), f"{k+1:02d}", fill=(80, 80, 80))
    canvas.save(out); print("预览:", out, canvas.size)

SHEETS = [                       # (原图, 角色目录名, 场景前缀)
    ("sheet1.jpg", "faxiu",   "dark"),    # 法修/魔修（紫黑）
    ("sheet2.jpg", "jianxiu", "bright"),  # 剑修（白/灰）
    ("sheet3.jpg", "huoxiu",  "fire"),    # 火修（红金）
]

if __name__ == "__main__":
    SPR = os.path.join(ART, "sprites"); SCN = os.path.join(ART, "scenes")
    all_scenes = []
    for fn, cname, sname in SHEETS:
        p = os.path.join(RAW, fn)
        if not os.path.exists(p):
            print(f"跳过(缺图): {fn}"); continue
        c, s = slice_sheet(p, f"{SPR}/{cname}", SCN, "pose", sname)
        montage(c, 3, 230, f"{cname} poses", True, f"{ART}/_preview_{cname}.png")
        all_scenes += s
    montage(all_scenes, 2, 340, "scenes", False, f"{ART}/_preview_scenes.png")
    print("\n完成。")
