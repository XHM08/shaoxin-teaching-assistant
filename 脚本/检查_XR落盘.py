
import io
import os
import shutil
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 地基 import 文件属性, 技能包
from 能力 import 写文件, 登记技能包

过, 失败 = [], []


def 记(条件, 说明):
    (过 if 条件 else 失败).append(说明)


草稿 = os.path.join(配置目录 := os.path.join(根, "材料", "_批量识图"), "自检-XR草稿.md")
os.makedirs(配置目录, exist_ok=True)
代号 = "zizhu-xr-check"

try:
    果 = 写文件.处理(路径=草稿, 内容="# 标题" + chr(10) + "正文一段")
    行们 = io.open(草稿, encoding="utf-8").read().split(chr(10))
    记(行们[0] == "# 标题", "① 第 1 行还是标题（%r）" % 行们[0])
    记(行们[1].strip() == "XR: C", "① 第 2 行是 XR: C（%r）" % 行们[1])
    记(果.get("写了XR") is True, "① 返回值里说清了写过 XR")

    写文件.处理(路径=草稿, 内容="# 标题" + chr(10) + "XR: B" + chr(10) + "正文")
    文 = io.open(草稿, encoding="utf-8").read()
    记(文.count("XR:") == 1 and 文.split(chr(10))[1].strip() == "XR: C",
       "② 原有的 XR 行被重排成一行、且在第 2 行（%r）" % 文.split(chr(10))[:3])

    果 = 写文件.处理(路径=os.path.join(配置目录, "自检-XR.json"), 内容='{"a": 1}')
    json文 = io.open(果["路径"], encoding="utf-8").read()
    记(果.get("写了XR") is False and "XR:" not in json文,
       "③ .json 不写 XR（内容 %r）" % json文)
    os.remove(果["路径"])

    写文件.处理(路径=草稿, 内容="# 肖泽云语文" + chr(10) + chr(10) + "## 教学流程" + chr(10) + "先疏通字词。")
    果 = 登记技能包.处理(md路径=草稿, 代号=代号, 描述="自检用，验 XR 属性", 覆盖="是")
    正文 = io.open(果["路径"], encoding="utf-8").read()
    记("XR:" not in 正文, "④ 技能包正文里没有 XR 行")
    记(文件属性.读XR(果["路径"]) == "XR: C",
       "④ 文件属性里读到 XR: C（%r）" % 文件属性.读XR(果["路径"]))
    记(果.get("XR") == "XR: C", "④ 返回值里带了 XR 标记")

    流路 = str(果["路径"]) + ":XR"
    try:
        os.remove(流路)
    except OSError:
        记(False, "⑤ 反向验没法做：删不掉 XR 流（%s）" % 流路)
    记(文件属性.读XR(果["路径"]) != "XR: C",
       "⑤ 反向验：属性删掉之后读回来就不是 XR: C 了（%r）" % 文件属性.读XR(果["路径"]))
finally:
    shutil.rmtree(技能包.技能包目录(代号), ignore_errors=True)
    for 路 in (草稿, os.path.join(配置目录, "自检-XR.json")):
        if os.path.isfile(路):
            os.remove(路)

print()
for 一 in 过:
    print("  ✓ " + 一)
for 一 in 失败:
    print("  ✗ " + 一)
print()
if 失败:
    print("有 %d 项没过" % len(失败))
    sys.exit(1)
print("全部 %d 项通过" % len(过))
