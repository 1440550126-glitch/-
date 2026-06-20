#!/usr/bin/env python3
# 统一切图器：光底(白/淡棋盘格)边缘洪泛去背 -> 自动行列网格分割 -> 透明 PNG
import os, glob, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ART = os.path.dirname(os.path.abspath(__file__))
SRC = f"{ART}/raw/sheets"; OUT = f"{ART}/sprites/_byindex"
T = 233; MINBLOB = 400
SKIP = {"s05"}                      # 偏蓝剑修技能图，按用户要求去掉

def spans(p, thresh, min_len, gap):
    on = p > thresh; on = on.copy(); N = len(on); i = 0
    while i < N:                    # 合并小缝
        if not on[i]:
            j = i
            while j < N and not on[j]: j += 1
            if i > 0 and j < N and j - i <= gap: on[i:j] = True
            i = j
        else: i += 1
    out = []; i = 0
    while i < N:
        if on[i]:
            j = i
            while j < N and on[j]: j += 1
            if j - i >= min_len: out.append((i, j))
            i = j
        else: i += 1
    return out

def cut_sheet(path):
    img = Image.open(path).convert("RGB"); a = np.asarray(img); H, W = a.shape[:2]
    light = a.min(2) >= T
    lbl, _ = ndimage.label(light)
    border = set(np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))) - {0}
    ext = np.isin(lbl, list(border)) if border else np.zeros((H, W), bool)
    fg = ~ext
    fl, fn = ndimage.label(fg); sizes = np.bincount(fl.ravel())
    keep = np.where(sizes >= MINBLOB)[0]; keep = keep[keep != 0]
    fg = np.isin(fl, keep); fg = ndimage.binary_fill_holes(fg)
    rgba = np.dstack([a, np.where(fg, 255, 0).astype(np.uint8)])
    rows = spans(fg.sum(1), max(5, int(0.004 * W)), 70, 28)
    cells = []
    for (y0, y1) in rows:
        band = fg[y0:y1]
        cols = spans(band.sum(0), max(5, int(0.004 * (y1 - y0))), 55, 22)
        rc = []
        for (x0, x1) in cols:
            sub = fg[y0:y1, x0:x1]
            ys = np.where(sub.any(1))[0]; xs = np.where(sub.any(0))[0]
            if not len(ys): continue
            ry0, ry1 = y0 + ys[0], y0 + ys[-1] + 1; rx0, rx1 = x0 + xs[0], x0 + xs[-1] + 1
            if (rx1 - rx0) * (ry1 - ry0) < 2500: continue
            p = 6
            rc.append(Image.fromarray(
                rgba[max(0, ry0 - p):min(H, ry1 + p), max(0, rx0 - p):min(W, rx1 + p)], "RGBA"))
        if rc: cells.append(rc)
    return cells

def checker(w, h, s=10):
    yy, xx = np.mgrid[0:h, 0:w]
    return Image.fromarray(np.dstack([np.where(((xx//s+yy//s) % 2) == 0, 235, 205).astype(np.uint8)]*3), "RGB")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    sheets = sorted(glob.glob(f"{SRC}/s*.??g"))
    summary = []
    prev_rows = []
    for sp in sheets:
        sid = os.path.splitext(os.path.basename(sp))[0]
        if sid in SKIP:
            print(f"{sid}: 跳过"); continue
        cells = cut_sheet(sp)
        d = f"{OUT}/{sid}"; os.makedirs(d, exist_ok=True)
        n = 0; flat = []
        for ri, row in enumerate(cells, 1):
            for ci, im in enumerate(row, 1):
                im.save(f"{d}/r{ri}c{ci}.png"); flat.append(im); n += 1
        counts = [len(r) for r in cells]
        summary.append((sid, counts, n))
        print(f"{sid}: 行×列={counts} 共{n}格")
        prev_rows.append((sid, flat))
    # 核对拼图：每页4个sheet，每个一行其cell
    def page(items, pg):
        cell = 230; pad = 8; lab = 16
        maxc = max(len(f) for _, f in items)
        W = maxc * (cell + pad) + pad; rowh = cell + pad + lab
        H = len(items) * rowh + pad
        cv = Image.new("RGB", (W, H), (248, 248, 248)); dr = ImageDraw.Draw(cv)
        for ri, (sid, flat) in enumerate(items):
            y = pad + ri * rowh; dr.text((pad, y), f"{sid}  ({len(flat)})", fill=(180, 0, 0))
            for ci, im in enumerate(flat):
                t = im.copy(); t.thumbnail((cell, cell)); bg = checker(cell, cell)
                bg.paste(t, ((cell-t.width)//2, (cell-t.height)//2), t)
                cv.paste(bg, (pad + ci*(cell+pad), y + lab))
        out = f"{ART}/_check/cut_{pg}.png"; cv.save(out); print("核对图:", out)
    for pg, st in enumerate(range(0, len(prev_rows), 4)):
        page(prev_rows[st:st+4], pg)
    print("总计 sheet:", len(summary), " 总格数:", sum(s[2] for s in summary))
