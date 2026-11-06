
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

母图目录 = os.path.join(os.environ.get("AVATAR_HOME", ""), "母图")
表情框 = [(168, 144, 266, 176), (198, 184, 238, 206), (170, 136, 264, 150)]
臂框 = (266, 300, 412, 592)
姿态们 = ["挥手", "挥手2", "举手", "指向"]
肩线 = 450

失败 = []
条数 = 0


def 记(名, 通过, 说明=""):
    global 条数
    条数 += 1
    print(("  ✓ " if 通过 else "  ✗ ") + 名 + ("" if 通过 else "　→　" + str(说明)))
    if not 通过:
        失败.append(名)


def 右块们(图):
    a = np.asarray(图.convert("RGB")).astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    肤 = (r > 195) & (g > 150) & (b > 120) & (r > b + 22)
    h, w = 肤.shape
    seen = np.zeros_like(肤)
    出 = []
    for y in range(h):
        for x in range(w):
            if 肤[y, x] and not seen[y, x]:
                q = deque([(y, x)])
                seen[y, x] = True
                ys, xs = [], []
                while q:
                    cy, cx = q.popleft()
                    ys.append(cy)
                    xs.append(cx)
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and 肤[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                q.append((ny, nx))
                if len(ys) > 400 and np.mean(xs) > 270:
                    出.append((int(min(ys)), int(max(ys)), int(np.mean(xs))))
    return sorted(出, key=lambda 一: 一[0])


def 主():
    if not os.path.isdir(母图目录):
        print("  跳过：没设 AVATAR_HOME（形象资产在仓库外），这一条这次没验")
        print("  （设好 AVATAR_HOME 再跑：set AVATAR_HOME=…\形象）")
        sys.exit(3)
    母 = Image.open(os.path.join(母图目录, "定版-白底-1024.png")).convert("RGB")

    记("母图右侧本来就是两块（前臂 + 手掌分开）",
        len(右块们(母)) == 2, "实测 %d 块" % len(右块们(母)))

    甲 = np.asarray(母).astype(int)
    for 名 in 姿态们:
        路 = os.path.join(母图目录, "部件", 名 + ".png")
        if not os.path.isfile(路):
            记("%s 存在" % 名, False, "缺 " + 路)
            continue
        图 = Image.open(路).convert("RGB")
        块 = 右块们(图)
        记("%s 右侧只有一只手" % 名, len(块) == 1, "实测 %d 块：%s" % (len(块), 块))
        if 块:
            记("%s 的手在肩线以上（y<%d）" % (名, 肩线), 块[0][1] < 肩线,
                "手掌最低点 y=%d" % 块[0][1])

        乙 = np.asarray(图).astype(int)
        差 = np.abs(甲 - 乙).sum(axis=2)
        外 = np.ones(差.shape, bool)
        for x0, y0, x1, y1 in 表情框 + [臂框]:
            外[max(0, y0 - 16):y1 + 16, max(0, x0 - 16):x1 + 16] = False
        记("%s 表情区与框外一个像素没动" % 名, int((差[外] > 0).sum()) == 0,
            "被改 %d 像素" % int((差[外] > 0).sum()))

    print()
    if 失败:
        print("失败 %d / 共 %d：%s" % (len(失败), 条数, "、".join(失败)))
        sys.exit(1)
    print("全部 %d 项通过" % 条数)
    sys.exit(0)


if __name__ == "__main__":
    主()
