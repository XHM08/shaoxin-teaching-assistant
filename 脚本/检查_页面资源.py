
import os
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置


class 取地址(HTMLParser):

    def __init__(self):
        super().__init__()
        self.地址表 = []

    def handle_starttag(self, 标签, 属性表):
        for 名字, 值 in 属性表:
            if 名字 in ("href", "src") and 值:
                self.地址表.append(值)


def 查元素id(原文, 页面名, 问题):
    有定义 = set(re.findall(r'id="([^"]+)"', 原文))
    被引用 = set(re.findall(r"\$\('([^']+)'\)", 原文))
    被引用 |= set(re.findall(r'getElementById\("([^"]+)"\)', 原文))
    缺 = sorted(名字 for 名字 in 被引用 if 名字 not in 有定义)
    if 缺:
        问题.append(页面名 + " 里 JS 引用了不存在的 id：" + "、".join(缺[:8]))
    print("  %s：JS 引用 %d 个 id，缺 %d 个。" % (页面名, len(被引用), len(缺)))


def 取脚本段(原文):
    起点 = 原文.find("<script>")
    终点 = 原文.find("</script>")
    if 起点 < 0 or 终点 < 0:
        return ""
    return 原文[起点 + 8:终点]


def 查导航与视图(原文, 问题):
    视图 = re.findall(r'<section id="view-([^"]+)"', 原文)
    脚本 = re.search(r"const VIEWS\s*=\s*\[([^\]]*)\]", 原文)
    声明们 = re.findall(r"'([^']+)'", 脚本.group(1)) if 脚本 else []
    入口 = re.findall(r'data-go="([^"]+)"', 原文)

    if not 视图:
        问题.append("一个 <section id=view-*> 都没解析到 —— 解析逻辑可能已经失效")
        return
    if not 声明们:
        问题.append("没解析到 VIEWS 数组 —— 解析逻辑可能已经失效")
        return

    对账 = [("VIEWS 数组", set(声明们)), ("data-go 入口", set(入口))]
    基准 = set(视图)
    print("\n  导航与页面对账（共 %d 个页面）：" % len(基准))
    for 名字, 集合 in 对账:
        缺 = 基准 - 集合
        多 = 集合 - 基准
        print("    %-14s %d 个  %s"
              % (名字, len(集合), "一致" if not (缺 or 多) else "不一致"))
        if 缺:
            问题.append("有页面但「" + 名字 + "」里没有：" + "、".join(sorted(缺)))
        if 多:
            问题.append("「" + 名字 + "」里有但没对应页面：" + "、".join(sorted(多)))


def main():
    根 = 配置.根目录
    首页 = os.path.join(根, "网页", "首页.html")
    if not os.path.isfile(首页):
        print("  找不到首页：" + 首页)
        return 1

    with open(首页, encoding="utf-8") as 文件:
        原文 = 文件.read()

    解析器 = 取地址()
    解析器.feed(原文)

    从首页抽到的 = []
    for 一个 in 解析器.地址表:
        if 一个.startswith(("http://", "https://", "#", "mailto:", "javascript:")):
            continue
        if "{" in 一个 or "}" in 一个 or "%" in 一个:
            continue
        if 一个 not in 从首页抽到的:
            从首页抽到的.append(一个)

    if not 从首页抽到的:
        print("  提示：从首页一个本地地址都没抽到 —— 抽地址的逻辑可能已经失效")

    要查的 = ["/", "/网页/首页.html", "/网页/样式.css"]
    for 一个 in 从首页抽到的:
        if 一个 not in 要查的:
            要查的.append(一个)

    端口 = int(配置.读取().get("本地服务", {}).get("端口", 8765))
    try:
        urllib.request.urlopen("http://127.0.0.1:%d/" % 端口, timeout=5).read(1)
        服务活着 = True
    except Exception:
        服务活着 = False

    问题 = []
    print("  要查的地址 %d 条（应用自己的入口 + 首页里引用的）：" % len(要查的))
    for 地址 in 要查的:
        磁盘 = 首页 if 地址 in ("/", "") else os.path.join(
            根, 地址.lstrip("/").replace("/", os.sep))
        磁盘OK = os.path.isfile(磁盘)

        期望类型 = None
        if 地址.endswith(".css"):
            期望类型 = "text/css"
        elif 地址.endswith(".html") or 地址 in ("/", ""):
            期望类型 = "text/html"

        实际类型 = ""
        if 服务活着:
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d%s" % (端口, quote(地址)),
                                            timeout=10) as 响应:
                    网页码 = 响应.status
                    实际类型 = (响应.headers.get("Content-Type") or "").split(";")[0].strip()
            except urllib.error.HTTPError as 异常:
                网页码 = 异常.code
            except Exception:
                网页码 = "连不上"
        else:
            网页码 = "（服务没起）"

        类型OK = (期望类型 is None or 实际类型 == 期望类型)
        好 = 磁盘OK and 类型OK and 网页码 == 200
        标注 = ""
        if not 磁盘OK:
            标注 = "← 磁盘上没这个文件"
        elif not 类型OK:
            标注 = "← 内容类型应是 %s，实际 %s" % (期望类型, 实际类型)
        elif 网页码 == "（服务没起）":
            标注 = "← 服务没起，这一项根本没验到"
        elif not 好:
            标注 = "← 取不到"
        print("    %-24s 磁盘 %-4s HTTP %-8s 类型 %-26s %s"
              % (地址, "有" if 磁盘OK else "没有", 网页码, 实际类型 or "—", 标注))
        if not 好:
            问题.append(地址)

    动态 = sorted(set(re.findall(r"'(/[^'\s]*)'", 取脚本段(原文))))
    if 动态:
        print("\n  以下地址是 JS 现场拼的，**没查**（含模板变量的没法静态查）：")
        for 一条 in 动态:
            print("    " + 一条)
    else:
        print("\n  JS 里没有现场拼的本地地址。")

    查导航与视图(原文, 问题)

    for 一个 in sorted(os.listdir(os.path.join(根, "网页"))):
        if not 一个.endswith(".html") or 一个.startswith("_"):
            continue
        with open(os.path.join(根, "网页", 一个), encoding="utf-8") as 文件:
            查元素id(文件.read(), 一个, 问题)

    if 问题:
        print("\n  %d 条没对上 —— 页面会缺东西、样式丢，或某块功能静默失效：" % len(问题))
        for 一条 in 问题:
            print("    " + 一条)
        return 1

    print("\n  静态地址全部取得回来，元素 id 也都对得上。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
