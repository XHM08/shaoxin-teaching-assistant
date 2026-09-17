
import hashlib
import html.parser
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
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

手机UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
         "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")


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

        手机页 = os.path.join(网页目录, "手机.html")
        自检页 = os.path.join(网页目录, "_手机自检.html")
        if not os.path.isfile(手机页):
            问题.append("找不到 网页/手机.html")
        else:
            原手机 = io.open(手机页, encoding="utf-8").read()
            if "</body>" not in 原手机:
                问题.append("手机.html 里找不到 </body>，注入会静默失效")
            else:
                注入 = ("\n<script>window.addEventListener('load',function(){"
                        "setTimeout(async function(){"
                        "var 框=document.createElement('div');框.id='__自检';"
                        "document.body.appendChild(框);"
                        "try{var d=await 跑能力('用量统计',{});"
                        "框.textContent='自检结果:OK '+(d.提示||'').slice(0,40);}"
                        "catch(e){框.textContent='自检结果:失败 '+e.message;}},1200)});"
                        "</script>\n</body>")
                改后 = 原手机.replace("</body>", 注入, 1)
                if len(改后) == len(原手机):
                    问题.append("手机.html 的注入没生效")
                else:
                    io.open(自检页, "w", encoding="utf-8").write(改后)
                    手机地址 = "http://127.0.0.1:%d%s" % (
                        端口, urllib.parse.quote("/网页/_手机自检.html"))
                    图 = os.path.join(产物, "手机版.png")
                    手机跑 = 手机dom = None
                    try:
                        手机跑 = subprocess.run([edge, "--headless=new", "--disable-gpu",
                                               "--user-data-dir=" + 配置目录,
                                               "--hide-scrollbars", "--window-size=390,844",
                                               "--user-agent=" + 手机UA,
                                               "--virtual-time-budget=20000",
                                               "--screenshot=" + 图, 手机地址],
                                              timeout=180, capture_output=True)
                        手机dom = subprocess.run([edge, "--headless=new", "--disable-gpu",
                                                "--user-data-dir=" + 配置目录,
                                                "--user-agent=" + 手机UA,
                                                "--virtual-time-budget=20000",
                                                "--dump-dom", 手机地址],
                                               timeout=180, capture_output=True)
                    except subprocess.TimeoutExpired:
                        问题.append("手机版跑了 180 秒还没完")
                    except OSError as 异常:
                        问题.append("手机版起不了 Edge：" + str(异常))

                    if 手机跑 is not None and 手机dom is not None:
                        if 手机跑.returncode != 0:
                            问题.append("手机版截图时 Edge 退出码 %d" % 手机跑.returncode)
                        elif not os.path.isfile(图):
                            问题.append("手机版截图没出来")
                        else:
                            字节数 = os.path.getsize(图)
                            指纹 = hashlib.md5(open(图, "rb").read()).hexdigest()
                            指纹表["手机版"] = 指纹
                            if 字节数 < 最小图:
                                问题.append("手机版截图只有 %d 字节，多半是白屏" % 字节数)
                            文本 = 手机dom.stdout.decode("utf-8", "replace")
                            io.open(os.path.join(产物, "手机版.dom.html"), "w",
                                    encoding="utf-8").write(文本)
                            if 手机dom.returncode != 0:
                                问题.append("手机版取 DOM 时 Edge 退出码 %d" % 手机dom.returncode)
                            elif len(文本) < 最小DOM:
                                问题.append("手机版 DOM 只有 %d 字符，可能没真渲染" % len(文本))
                            else:
                                if "viewport" not in 文本:
                                    问题.append("手机版没有 viewport（手机上会按桌面宽度缩放）")
                                for 该有的 in ("我有一道题", "电脑上操作", "学生档案馆", "用量"):
                                    if 该有的 not in 文本:
                                        问题.append("手机版里找不到「" + 该有的 + "」")
                                结果框 = re.search(r'<div id="__自检"[^>]*>(.*?)</div>',
                                                文本, re.S)
                                结果文字 = (结果框.group(1) if 结果框 else "").strip()
                                if not 结果文字.startswith("自检结果:OK"):
                                    问题.append("手机版的 JS 没拿到接口结果（__自检 里是："
                                                + (结果文字[:80] or "空") + "）")
                                print("    %-8s %7d 字节  md5 %s" % ("手机版", 字节数, 指纹[:12]))

        try:
            分派 = ((手机UA, "我有一道题", "手机 UA 打开根地址"),
                   ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "工作台", "电脑 UA 打开根地址"))
            for 代理, 该出现, 说明 in 分派:
                请求 = urllib.request.Request("http://127.0.0.1:%d/" % 端口,
                                             headers={"User-Agent": 代理})
                with urllib.request.urlopen(请求, timeout=10) as 响应:
                    原 = 响应.read().decode("utf-8", "replace")
                if 该出现 not in 原:
                    问题.append(说明 + "拿到的不是该有的那一版")
        except Exception as 异常:
            问题.append("按 UA 分派页面：" + type(异常).__name__ + "：" + str(异常)[:80])
    finally:
        try:
            for 一个 in (预览, 自检页):
                if os.path.isfile(一个):
                    os.remove(一个)
        except OSError as 异常:
            残留说明 = str(异常)
        shutil.rmtree(配置目录, ignore_errors=True)

    for 一个 in (预览, 自检页):
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

    print("\n  %d 个页面都画得出来，且两两不是同一张图（含手机版）。" % len(指纹表))
    print("  图在 " + 产物 + " —— 请自己打开看一眼，脚本判断不了好不好看。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
