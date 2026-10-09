
import hashlib
import html.parser
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置

EDGE们 = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

根 = 配置.根目录
网页目录 = os.path.join(根, "网页")
首页 = os.path.join(网页目录, "首页.html")
预览 = os.path.join(网页目录, "_预览.html")
产物 = os.path.join(根, "_页面截图")
端口 = int(配置.读取().get("本地服务", {}).get("端口", 8765))
地址 = "http://127.0.0.1:%d%s" % (端口, urllib.parse.quote("/网页/_预览.html"))

最小图 = 20000
最小DOM = 5000


class 收视图(html.parser.HTMLParser):

    def __init__(self):
        super().__init__()
        self.表 = {}

    def handle_starttag(self, 标签, 属性表):
        if 标签 != "section":
            return
        键值 = dict(属性表)
        编号 = 键值.get("id", "")
        if 编号.startswith("view-"):
            self.表[编号] = 键值.get("class") or ""


def 找Edge():
    for 一个 in EDGE们:
        if os.path.isfile(一个):
            return 一个
    return None


def 写预览(原, 页):
    注入 = ("\n<script>window.addEventListener('load',function(){"
            "setTimeout(function(){show('" + 页 + "')},600)});</script>\n</body>")
    改后 = 原.replace("</body>", 注入, 1)
    if len(改后) == len(原):
        return None
    io.open(预览, "w", encoding="utf-8").write(改后)
    return 改后


def main():
    edge = 找Edge()
    if not edge:
        print("  找不到 Edge，这个自检跑不了。找过这些位置：")
        for 一个 in EDGE们:
            print("    " + 一个)
        return 1

    锁 = os.path.join(产物 + ".lock")
    try:
        if os.path.isfile(锁) and (time.time() - os.path.getmtime(锁)) < 600:
            主人 = open(锁, encoding="utf-8", errors="replace").read().strip()
            print("  另一次「页面渲染」自检正在跑（%s）—— 这次跳过，免得两边互相毁证据。" % 主人)
            print("  （等它跑完再跑一次；锁超过 10 分钟会自动失效，卡死也不会一直挡着）")
            return 0
        os.makedirs(产物, exist_ok=True)
        with open(锁, "w", encoding="utf-8") as 文件:
            文件.write("pid=%d 起于 %s" % (os.getpid(), time.strftime("%H:%M:%S")))
    except OSError:
        锁 = ""

    try:
        return 跑一遍(edge)
    finally:
        if 锁:
            try:
                os.remove(锁)
            except OSError:
                pass


def 跑一遍(edge):
    if not os.path.isfile(首页):
        print("  找不到首页：" + 首页)
        return 1

    原 = io.open(首页, encoding="utf-8").read()

    脚本 = re.search(r"const VIEWS\s*=\s*\[([^\]]*)\]", 原)
    页们 = re.findall(r"'([^']+)'", 脚本.group(1)) if 脚本 else []
    if len(页们) < 5:
        print("  从首页没解析出 VIEWS（只拿到 %d 个）—— 解析逻辑可能已经失效" % len(页们))
        return 1
    if "</body>" not in 原:
        print("  首页里找不到 </body>，注入会静默失效 —— 先看这个")
        return 1

    try:
        urllib.request.urlopen("http://127.0.0.1:%d/" % 端口, timeout=5).read(1)
    except Exception as 异常:
        print("  服务没起（%s），先跑 启动.bat 或 python 本地服务.py" % type(异常).__name__)
        return 1

    shutil.rmtree(产物, ignore_errors=True)
    os.makedirs(产物, exist_ok=True)
    配置目录 = tempfile.mkdtemp(prefix="edge配置_")

    问题 = []
    指纹表 = {}
    残留说明 = None
    print("  逐页截图（共 %d 页）→ %s" % (len(页们), 产物))

    try:
        if 写预览(原, 页们[0]) is None:
            print("  注入没生效（长度没变）—— 先看首页的收尾标签")
            return 1
        try:
            with urllib.request.urlopen(地址, timeout=10) as 响应:
                预览码 = 响应.status
        except urllib.error.HTTPError as 异常:
            预览码 = 异常.code
        except Exception as 异常:
            预览码 = "连不上（%s）" % type(异常).__name__
        if 预览码 != 200:
            print("  预览页取不到：HTTP %s —— 地址 %s" % (预览码, 地址))
            return 1

        for 页 in 页们:
            if 写预览(原, 页) is None:
                问题.append(页 + " 的注入没生效")
                continue

            图 = os.path.join(产物, 页 + ".png")
            try:
                跑 = subprocess.run([edge, "--headless=new", "--disable-gpu",
                                     "--user-data-dir=" + 配置目录,
                                     "--hide-scrollbars", "--window-size=1280,1500",
                                     "--virtual-time-budget=15000",
                                     "--screenshot=" + 图, 地址],
                                    timeout=150, capture_output=True)
                dom = subprocess.run([edge, "--headless=new", "--disable-gpu",
                                      "--user-data-dir=" + 配置目录,
                                      "--virtual-time-budget=15000",
                                      "--dump-dom", 地址],
                                     timeout=150, capture_output=True)
            except subprocess.TimeoutExpired:
                问题.append(页 + " 截图超时（150 秒）")
                print("    %-8s 超时" % 页)
                continue
            except OSError as 异常:
                问题.append(页 + " 起不了 Edge：" + str(异常))
                continue

            if 跑.returncode != 0:
                问题.append(页 + " 截图时 Edge 退出码 %d" % 跑.returncode)
                print("    %-8s Edge 截图失败" % 页)
                continue
            if not os.path.isfile(图):
                问题.append(页 + " Edge 说成功但图没生成")
                continue

            字节数 = os.path.getsize(图)
            指纹 = hashlib.md5(open(图, "rb").read()).hexdigest()
            指纹表[页] = 指纹
            if 字节数 < 最小图:
                问题.append(页 + " 截图只有 %d 字节，多半是白屏" % 字节数)

            if dom.returncode != 0:
                问题.append(页 + " 取 DOM 时 Edge 退出码 %d" % dom.returncode)
            文本 = dom.stdout.decode("utf-8", "replace")
            io.open(os.path.join(产物, 页 + ".dom.html"), "w",
                    encoding="utf-8").write(文本)
            if len(文本) < 最小DOM:
                问题.append(页 + " 的 DOM 只有 %d 字符，Edge 可能没真渲染" % len(文本))

            收 = 收视图()
            收.feed(文本)
            目标 = "view-" + 页
            if len(收.表) != len(页们):
                问题.append("%s 这轮只找到 %d 个 view 段落，应有 %d 个"
                            % (页, len(收.表), len(页们)))
            暴露 = sorted(键 for 键, 类 in 收.表.items()
                          if 键 != 目标 and "hide" not in 类)
            if 目标 not in 收.表:
                问题.append(页 + " 的 DOM 里没有 " + 目标 + " 这一段")
            elif "hide" in 收.表[目标]:
                问题.append(页 + " 没切过去：" + 目标 + " 还带着 hide")
            elif 暴露:
                问题.append(页 + " 显示时这些页也还露着：" + "、".join(暴露))

            print("    %-8s %7d 字节  md5 %s" % (页, 字节数, 指纹[:12]))

    finally:
        try:
            for 一个 in (预览,):
                if os.path.isfile(一个):
                    os.remove(一个)
        except OSError as 异常:
            残留说明 = str(异常)
        shutil.rmtree(配置目录, ignore_errors=True)

    for 一个 in (预览,):
        if 残留说明 or os.path.isfile(一个):
            问题.append("临时页没删掉，还留在 " + 一个 + "，请手动删"
                        + ("（" + 残留说明 + "）" if 残留说明 else ""))

    反查 = {}
    for 页, 指纹 in 指纹表.items():
        反查.setdefault(指纹, []).append(页)
    for 指纹, 组 in 反查.items():
        if len(组) > 1:
            问题.append("这几页截出了同一张图：" + "、".join(组) + "（md5 " + 指纹[:12] + "）")

    if 问题:
        print("\n  %d 处不对：" % len(问题))
        for 一条 in 问题:
            print("    " + 一条)
        return 1

    print("\n  %d 个页面都画得出来，且两两不是同一张图。" % len(指纹表))
    print("  图在 " + 产物 + " —— 请自己打开看一眼，脚本判断不了好不好看。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
