
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置, 注册表, 工具箱

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
桌面 = os.path.dirname(根)

相对文档 = [
    os.path.join("科赛", "README.md"),
    os.path.join("科赛", "knowledge", "00-项目概要.md"),
]
简报样式 = os.path.join(桌面, "邵新-交接简报-*.md")

豁免词 = ("旧口径", "旧数", "已废止", "废止", "应为", "改掉", "漂移", "验收")
变更记录行 = re.compile(r"^\s*[-|]?\s*20\d\d[-年]")
数字样式 = re.compile(r"(\d+)\s*(?:个|项)\s*(能力|工具|页面)")


def 现场数字():
    注册表.全部加载(os.path.join(根, "能力"))
    首页 = os.path.join(根, "网页", "首页.html")
    return {
        "能力": len(注册表.全部名字()),
        "工具": len(工具箱.全部名字()),
        "页面": len(re.findall(r'<section id="view-([^"]+)"', open(首页, encoding="utf-8").read())),
    }


def main():
    数 = 现场数字()
    print("  现场：%d 个能力 / %d 个工具 / %d 个页面" % (数["能力"], 数["工具"], 数["页面"]))
    if min(数.values()) <= 0:
        print("  ✗ 加载失败：现场数字算出来是 0，先查 能力/ 与 网页/首页.html 是不是读不到")
        return 1

    要扫 = [os.path.join(桌面, p) for p in 相对文档] + sorted(glob.glob(简报样式))
    在的 = [p for p in 要扫 if os.path.isfile(p)]
    缺的 = [p for p in 要扫 if not os.path.isfile(p)]
    if 缺的:
        print("  跳过（这些不在这台机器上，没验）：")
        for p in 缺的:
            print("     " + p)
    if not 在的:
        print("  跳过：文档一个都没找到，这一条没验")
        return 0

    对不上, 放过, 判了 = [], [], 0
    for p in 在的:
        for 行号, 行 in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
            for 命中 in 数字样式.finditer(行):
                值, 类别 = int(命中.group(1)), 命中.group(2)
                if 变更记录行.match(行):
                    放过.append("%s:%d（变更记录行，按形状跳过）%s" % (os.path.basename(p), 行号, 行.strip()[:52]))
                    continue
                if any(词 in 行 for 词 in 豁免词):
                    放过.append("%s:%d（行里有旧值标记 %s）%s"
                             % (os.path.basename(p), 行号,
                                [w for w in 豁免词 if w in 行][0], 行.strip()[:48]))
                    continue
                判了 += 1
                if 值 != 数[类别]:
                    对不上.append("%s:%d 写「%d 个%s」，现场是 %d。%s"
                              % (os.path.basename(p), 行号, 值, 类别, 数[类别], 行.strip()[:56]))

    print("  扫了 %d 个文件：判了 %d 处，豁免 %d 处" % (len(在的), 判了, len(放过)))
    for x in 放过:
        print("     · " + x)
    if 对不上:
        print("  %d 处对不上：" % len(对不上))
        for x in 对不上:
            print("     ✗ " + x)
        return 1
    print("  文档数字与现场一致 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
