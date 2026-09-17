
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置

每次都变 = {
    "问题", "课题", "页数", "材料原文", "老师的话", "之前的对话", "老师这次说的",
    "题目", "作答", "反馈内容", "代码片段",
}

成批稳定 = {
    "教师档案", "技能包", "动作清单", "工具说明", "维度",
    "错误类型清单", "项目背景",
}

尾部容差 = 20

结果 = []


def 检查(名字, 通过):
    结果.append((名字, bool(通过)))


def 取占位符(原文):
    return [(m.start(), m.group(1))
            for m in re.finditer(r"\{([\u4e00-\u9fa5A-Za-z_][\u4e00-\u9fa5A-Za-z0-9_]*)\}", 原文)]


提示词目录 = 配置.取目录("提示词")
模板们 = sorted(名 for 名 in os.listdir(提示词目录) if 名.endswith(".md"))
if not 模板们:
    print("  一个 .md 模板都没找到：" + 提示词目录)
    sys.exit(1)

print("  看 " + str(len(模板们)) + " 个模板：" + "、".join(模板们) + "\n")

for 文件名 in 模板们:
    with open(os.path.join(提示词目录, 文件名), encoding="utf-8") as 文件:
        原文 = 文件.read()
    名字 = 文件名[:-3]
    位置们 = 取占位符(原文)

    没登记 = [名 for _, 名 in 位置们 if 名 not in 每次都变 and 名 not in 成批稳定]
    检查("%s：占位符都登记过（没登记的：%s）" % (名字, "、".join(没登记) or "无"),
        not 没登记)
    if not 位置们:
        检查("%s：模板里认得出的占位符至少 1 个（现在 0 个）" % 名字, False,
           "看它是不是把变量写成了正则认不出的形式，比如带空格或连字符")
        continue

    变的位置 = [位置 for 位置, 名 in 位置们 if 名 in 每次都变]
    稳的位置 = [位置 for 位置, 名 in 位置们 if 名 in 成批稳定]

    if not 变的位置:
        检查("%s：有变量占位符" % 名字, False)
        continue

    第一个变 = min(变的位置)
    尾巴 = re.sub(r"\{[^}]+\}", "", 原文[第一个变:]).strip()
    检查("%s：变量之后没有固定正文（剩 %d 字）" % (名字, len(尾巴)),
        len(尾巴) <= 尾部容差)
    if len(尾巴) > 尾部容差:
        print("       尾巴原文：" + 尾巴[:80].replace("\n", "⏎"))

    检查("%s：稳定占位符都排在变量前面" % 名字,
        (not 稳的位置) or max(稳的位置) < 第一个变)

坏的 = 0
print()
for 一条, 通过 in 结果:
    print(("  通过  " if 通过 else "  失败  ") + 一条)
    坏的 += 0 if 通过 else 1
print("全部 %d 项通过" % len(结果) if not 坏的 else "%d 项失败" % 坏的)
sys.exit(0 if not 坏的 else 1)
