
import os
import socket
import subprocess
import sys
import time
import urllib.request

from 地基 import WebView2, 配置, 语音, 版本


源码脚本 = {"服务": "本地服务.py", "悬浮窗": "课堂悬浮窗.py"}

子进程们 = []
日志把手 = []


角色进程 = {}


def 冻结了吗():
    return bool(getattr(sys, "frozen", False))


def 子进程命令(角色, 冻结=None):
    是冻结 = 冻结了吗() if 冻结 is None else 冻结
    if 是冻结:
        return [sys.executable, 角色]
    脚本 = 源码脚本.get(角色)
    if 脚本 is None:
        raise ValueError("不认识的角色：" + str(角色) + "（只有 服务 / 悬浮窗）")
    return [sys.executable, os.path.join(配置.根目录, 脚本)]


def _弹窗(文字, 标题="「邵新」辅助教育系统", 图标=0x40):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, 文字, 标题, 图标)
        return True
    except Exception:

        return False


def 提示(文字, 报错=True):
    完整 = 文字
    if 报错:
        完整 = 文字 + "\n\n（详细日志在 exe 同级的 日志\\ 目录里）"
    if 冻结了吗() and _弹窗(完整, 图标=0x10 if 报错 else 0x40):
        return
    sys.stderr.write(完整 + "\n")


def 有人听吗(端口号):
    套 = socket.socket()
    套.settimeout(0.5)
    try:
        套.connect(("127.0.0.1", int(端口号)))
        return True
    except OSError:
        return False
    finally:
        套.close()


def 等端口(端口号, 超时秒=15):
    期限 = time.time() + 超时秒
    while time.time() < 期限:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/" % int(端口号), timeout=2) as 答:
                if "邵新" in 答.read().decode("utf-8", "ignore"):
                    return True
        except Exception:

            pass
        time.sleep(0.4)
    return False


def 端口号():
    return 配置.取端口()


def _开日志(角色):
    目录 = os.path.join(配置.根目录, "日志")
    os.makedirs(目录, exist_ok=True)
    把手 = open(os.path.join(目录, "客户端-" + 角色 + ".log"), "a",
              encoding="utf-8", errors="replace")
    日志把手.append(把手)
    return 把手


def _起(角色, 命令, 工作目录):
    把手 = _开日志(角色)
    try:
        跑 = subprocess.Popen(命令, cwd=工作目录, stdout=把手, stderr=subprocess.STDOUT)
    except OSError as 异常:
        提示("起「" + 角色 + "」失败：" + str(异常))
        return None
    子进程们.append(跑)
    角色进程[角色] = 跑
    return 跑


def 起本地服务():
    return _起("服务", 子进程命令("服务"), 配置.根目录)


def 起悬浮窗():
    跑 = 角色进程.get("悬浮窗")
    if 跑 is not None and 跑.poll() is None:
        return 跑
    return _起("悬浮窗", 子进程命令("悬浮窗"), 配置.根目录)


def 起语音():
    try:
        目录 = 语音.读程序目录()
    except ValueError as 异常:
        return None, str(异常)
    PY = os.path.join(目录, ".venv", "Scripts", "python.exe")
    if not os.path.isfile(PY):
        return None, "没找到 GPT-SoVITS 的环境"
    脚本 = os.path.join(配置.根目录, "语音", "启动语音服务.py")
    if not os.path.isfile(脚本):
        return None, "没找到 语音/启动语音服务.py"
    把手 = _开日志("语音")
    try:
        跑 = subprocess.Popen([PY, 脚本], cwd=os.path.join(配置.根目录, "语音"),
                          stdout=把手, stderr=subprocess.STDOUT)
    except OSError as 异常:
        return None, "语音服务起不来：" + str(异常)
    子进程们.append(跑)
    return 跑, ""


def 收队(进程表, 超时秒=3):
    活的 = [跑 for 跑 in 进程表 if 跑.poll() is None]
    for 跑 in reversed(活的):
        try:
            跑.terminate()
        except OSError:
            pass
    期限 = time.time() + 超时秒
    while time.time() < 期限 and any(跑.poll() is None for 跑 in 活的):
        time.sleep(0.1)
    强的 = 0
    for 跑 in 活的:
        if 跑.poll() is None:
            try:
                跑.kill()
            except OSError:
                pass
            else:
                强的 += 1
    return 强的


def 收全部(超时秒=3):
    return 收队(list(子进程们), 超时秒)


def _开文件夹(目录):
    全 = 目录 if os.path.isabs(目录) else os.path.join(配置.根目录, 目录)
    if not os.path.isdir(全):
        提示("找不到这个文件夹：\n" + 全)
        return
    try:
        os.startfile(全)
    except (AttributeError, OSError) as 异常:
        提示("打不开这个文件夹：\n" + 全 + "\n\n" + str(异常))


def _关于():
    _弹窗("「邵新」辅助教育系统\n版本 " + 版本.版本号
         + "\n\n本地运行 · 数据不出本机（除主动发给 AI 服务商的内容）", 图标=0x40)


def 主程序():
    口 = 端口号()
    地址 = "http://127.0.0.1:%d" % 口


    if not 等端口(口, 0.5):
        if 有人听吗(口):
            提示("端口 " + str(口) + " 被别的程序占着了（不是邵新自己的服务）。\n\n"
                 "怎么办：\n"
                 "  · 先把可能占着它的程序关掉，再双击一次；\n"
                 "  · 或在 配置.json 里把 本地服务.端口 改成别的值。")
            return 1
        起本地服务()
        if not 等端口(口, 15):
            提示("邵新的本地服务 15 秒没起来。\n\n"
                 "去看 日志\\客户端-服务.log，最后几行有报错原文。\n"
                 "常见原因：Python 缺依赖（照报错那句 pip install 装上）。")
            收全部()
            return 1

    状态 = []
    有, _版本, _依据 = WebView2.查()
    if not 有:
        成, 说明 = WebView2.装()
        if not 成:
            命令 = WebView2.回退命令(地址)
            if 命令 is None:
                提示("这台机器缺 WebView2 运行时，而且装不上、也没有 Edge 可以退。\n\n"
                     "（" + 说明 + "）\n\n"
                     "手动装一个再来：\n"
                     "https://developer.microsoft.com/microsoft-edge/webview2/")
                收全部()
                return 1
            提示("WebView2 用不了（" + 说明 + "），这次改用 Edge 开窗口：功能一样，"
                 "只是窗口由 Edge 承载。", 报错=False)
            subprocess.Popen(命令)
            return 0

    _, 语音说明 = 起语音()
    if 语音说明:
        状态.append("语音未启动")

    import webview
    from webview.menu import Menu, MenuAction

    标题 = "「邵新」辅助教育系统 v" + 版本.版本号
    if 状态:
        标题 = 标题 + "　（" + "；".join(状态) + "）"

    菜单 = [Menu("窗口", [
        MenuAction("打开课堂悬浮窗", 起悬浮窗),
        MenuAction("打开课件输出文件夹", lambda: _开文件夹(配置.取目录("课件输出"))),
        MenuAction("打开日志文件夹", lambda: _开文件夹("日志")),
        MenuAction("关于", _关于),
    ])]

    图标 = os.path.join(配置.根目录, "邵新.ico")
    缓存目录 = os.path.join(配置.取目录("教师数据"), "网页缓存")
    os.makedirs(缓存目录, exist_ok=True)
    webview.create_window(标题, 地址, width=1400, height=900,
                          min_size=(1024, 700), menu=菜单)
    try:
        webview.start(gui="edgechromium",
                      private_mode=False,
                      storage_path=缓存目录,
                      icon=图标 if os.path.isfile(图标) else None)
    finally:
        收全部()
    return 0


if __name__ == "__main__":
    sys.exit(主程序())
