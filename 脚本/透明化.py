
from collections import deque

import numpy as np
from PIL import Image, ImageFilter


def 抠图(图, 容差=26, 羽化=1.0):
    甲 = np.asarray(图.convert("RGB")).astype(int)
    高, 宽 = 甲.shape[0], 甲.shape[1]
    角 = np.concatenate([甲[:6, :6].reshape(-1, 3), 甲[:6, -6:].reshape(-1, 3),
                         甲[-6:, :6].reshape(-1, 3), 甲[-6:, -6:].reshape(-1, 3)])
    底 = 角.mean(axis=0)
    近似 = (np.abs(甲 - 底).sum(axis=2) <= 容差)

    背景 = np.zeros((高, 宽), bool)
    q = deque()
    for x in range(宽):
        for y in (0, 高 - 1):
            if 近似[y, x] and not 背景[y, x]:
                背景[y, x] = True
                q.append((y, x))
    for y in range(高):
        for x in (0, 宽 - 1):
            if 近似[y, x] and not 背景[y, x]:
                背景[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < 高 and 0 <= nx < 宽 and 近似[ny, nx] and not 背景[ny, nx]:
                背景[ny, nx] = True
                q.append((ny, nx))

    蒙 = Image.fromarray(np.where(背景, 0, 255).astype(np.uint8), "L")
    if 羽化:
        蒙 = 蒙.filter(ImageFilter.GaussianBlur(羽化))
    return Image.fromarray(np.dstack([甲.clip(0, 255).astype(np.uint8), np.asarray(蒙)]), "RGBA")


def 检查(图, 原图=None):
    甲 = np.asarray(图.convert("RGBA"))[:, :, 3]
    return 100.0 * (甲 == 0).mean(), 100.0 * (甲 > 250).mean()
