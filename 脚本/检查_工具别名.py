
import os
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 地基 import 注册表, 工具箱

注册表.全部加载(os.path.join(根, "能力"))
from 能力 import _对话工具

过, 失败 = [], []


def 记(条件, 说明):
    (过 if 条件 else 失败).append(说明)


表 = {}
for 工具名, 工具 in 工具箱.已登记工具.items():
    for 一 in (工具.get("别名") or ()):
        表[一] = 工具名
记(len(表) >= 5, "① 至少挂了 5 个别名（现在 %d 个：%s）" % (len(表), "、".join(sorted(表))))
解不回 = [一 for 一 in 表 if 工具箱.解别名(一) != 表[一]]
记(not 解不回, "① 每个别名都解回自己的正式名（解不回的：%s）" % (解不回 or "无"))

撞 = [一 for 一 in 表 if 一 in 工具箱.已登记工具]
记(not 撞, "② 别名没有和正式名撞车（撞的：%s）" % (撞 or "无"))
计 = {}
for 名 in 表:
    计[名] = 计.get(名, 0) + 1
重 = [名 for 名, 数 in 计.items() if 数 > 1]
记(not 重, "② 没有两个工具抢同一个别名（抢的：%s）" % (重 or "无"))

样例 = None
扫描根 = os.path.join(根, "材料")
for 目录, _子们, 文件们 in os.walk(扫描根):
    for 名 in 文件们:
        if 名.lower().endswith(".md"):
            样例 = os.path.join(目录, 名)
            break
    if 样例:
        break
if not 样例:
    记(False, "③ 材料里没有 md，没法用真文件验别名（这条算没过）")
else:
    相对 = os.path.relpath(样例, 扫描根)
    甲 = 工具箱.调用("数材料字数", {"文件": 相对})
    乙 = 工具箱.调用("count_words", {"文件": 相对})
    记(甲.get("成功") is True and 乙.get("成功") is True
       and 甲["结果"]["字数"] == 乙["结果"]["字数"],
       "③ 别名与正式名数出同一个字数（%s / %s）"
       % (甲.get("结果", {}).get("字数"), 乙.get("结果", {}).get("字数")))

文字 = 工具箱.工具清单文字()
缺 = [一 for 一 in 表 if 一 not in 文字]
记(not 缺, "④ 给模型的清单文字里写全了别名（缺的：%s）" % (缺 or "无"))

记(工具箱.解别名("image_read_typo") is None, "⑤ 反向验：不存在的别名解不出来")
假调 = 工具箱.调用("image_read_typo", {})
记(假调.get("成功") is False and "没有登记这个工具" in str(假调.get("错误")),
   "⑤ 反向验：用不存在的别名调用被白名单拒（%s）" % str(假调.get("错误"))[:30])
try:
    工具箱.登记工具("假工具", "x", [{"代号": "a", "标签": "b"}], lambda: None, 别名=("image_read",))
    记(False, "⑤ 反向验：重复别名应该登记失败，结果登记成功了")
except ValueError:
    记(True, "⑤ 反向验：重复别名登记时被拦下")

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
