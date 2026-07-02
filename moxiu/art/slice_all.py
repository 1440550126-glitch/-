#!/usr/bin/env python3
# 统一切图器 v2：光底洪泛去背 -> 行(空隙)分带 -> 列(密度波峰)分人 -> 透明PNG
# 波峰法对"特效/锁链/暗影搭桥"免疫，并能自动数出每行人数
import os, glob, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.signal import find_peaks

ART = os.path.dirname(os.path.abspath(__file__))
SRC = f"{ART}/raw/sheets"; OUT = f"{ART}/sprites/cut"; ANN = f"{ART}/_check"
T = 233; MINBLOB = 400
SKIP = {"s05"}
FORCE = {"s06": [4, 4, 4]}      # 已知网格：每行强制列数（认领后逐步补充）

def fg_of(a):
    light = a.min(2) >= T
    lbl, _ = ndimage.label(light)
    border = set(np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))) - {0}
    ext = np.isin(lbl, list(border)) if border else np.zeros(a.shape[:2], bool)
    fg = ~ext
    fl, _ = ndimage.label(fg); sizes = np.bincount(fl.ravel())
    keep = np.where(sizes >= MINBLOB)[0]; keep = keep[keep != 0]
    fg = np.isin(fl, keep)
    return ndimage.binary_fill_holes(fg)

def row_bands(fg, W):                       # 行用空隙分（行间通常有白缝）
    prof = fg.sum(1); on = prof > max(5, int(0.004 * W))
    on = on.copy(); N = len(on); i = 0
    while i < N:                            # 合并<30px小缝
        if not on[i]:
            j = i
            while j < N and not on[j]: j += 1
            if i > 0 and j < N and j - i <= 30: on[i:j] = True
            i = j
        else: i += 1
    out = []; i = 0
    while i < N:
        if on[i]:
            j = i
            while j < N and on[j]: j += 1
            if j - i >= 70: out.append((i, j))
            i = j
        else: i += 1
    return out

def col_splits(band, W, n_force=None):      # 自相关求人物重复间距 -> 人数 -> 谷值强制切
    xs = np.where(band.any(0))[0]
    if len(xs) == 0: return []
    x0, x1 = int(xs[0]), int(xs[-1]) + 1; cw = x1 - x0
    dens = band[:, x0:x1].sum(0).astype(float)
    k = max(9, (cw // 60) | 1); dens = np.convolve(dens, np.ones(k) / k, "same")
    d = dens - dens.mean()
    n = 1
    if n_force:
        n = n_force
    elif not np.allclose(d, 0) and cw > 40:
        ac = np.correlate(d, d, "full")[len(d) - 1:]; ac[0] = 0
        lo = max(3, int(cw * 0.09)); hi = int(cw * 0.92)     # 最小人物宽≈9%内容宽
        if hi > lo:
            lag = lo + int(np.argmax(ac[lo:hi]))
            if lag > 0: n = max(1, min(8, round(cw / lag)))  # 每行≤8兜底，防特效误判过切
    if n <= 1:
        return [(x0, x1)]
    cuts = [x0]
    for i in range(1, n):
        c = int(cw * i / n); win = max(4, int(cw * 0.5 / n))
        loi, hii = max(1, c - win), min(cw - 1, c + win)
        cuts.append(x0 + loi + int(np.argmin(dens[loi:hii])))
    cuts.append(x1)
    return list(zip(cuts[:-1], cuts[1:]))

def cut_sheet(path, force=None):
    img = Image.open(path).convert("RGB"); a = np.asarray(img); H, W = a.shape[:2]
    fg = fg_of(a); rgba = np.dstack([a, np.where(fg, 255, 0).astype(np.uint8)])
    out_rows, boxes = [], []
    for bi, (y0, y1) in enumerate(row_bands(fg, W)):
        nf = force[bi] if force and bi < len(force) else None
        rc = []
        for (x0, x1) in col_splits(fg[y0:y1], W, nf):
            sub = fg[y0:y1, x0:x1]
            ys = np.where(sub.any(1))[0]; xs = np.where(sub.any(0))[0]
            if not len(ys) or not len(xs): continue
            ry0, ry1 = y0 + ys[0], y0 + ys[-1] + 1; rx0, rx1 = x0 + xs[0], x0 + xs[-1] + 1
            if (rx1 - rx0) * (ry1 - ry0) < 2500: continue
            p = 6; bb = (max(0, rx0-p), max(0, ry0-p), min(W, rx1+p), min(H, ry1+p))
            rc.append(Image.fromarray(rgba[bb[1]:bb[3], bb[0]:bb[2]], "RGBA")); boxes.append(bb)
        if rc: out_rows.append(rc)
    # 核对：原图缩小+画框
    sc = 760 / W; ann = img.resize((760, int(H * sc))); dr = ImageDraw.Draw(ann)
    for (x0, y0, x1, y1) in boxes:
        dr.rectangle([x0*sc, y0*sc, x1*sc, y1*sc], outline=(220, 20, 20), width=2)
    return out_rows, ann

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for sp in sorted(glob.glob(f"{SRC}/s*.??g")):
        sid = os.path.splitext(os.path.basename(sp))[0]
        if sid in SKIP: continue
        rows, ann = cut_sheet(sp, FORCE.get(sid))
        d = f"{OUT}/{sid}"; os.makedirs(d, exist_ok=True)
        for f in glob.glob(f"{d}/*.png"): os.remove(f)
        n = 0
        for ri, row in enumerate(rows, 1):
            for ci, im in enumerate(row, 1):
                im.save(f"{d}/r{ri}c{ci}.png"); n += 1
        ann.save(f"{ANN}/annot_{sid}.png")
        print(f"{sid}: 行×列={[len(r) for r in rows]} 共{n}")
