
import os
import subprocess
import sys

客户端_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
注册表键 = r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients"
安装目录候选 = (
    r"C:\Program Files (x86)\Microsoft\EdgeWebView\Application",
    r"C:\Program Files\Microsoft\EdgeWebView\Application",
)
Edge候选 = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)
安装器名字 = "MicrosoftEdgeWebview2Setup.exe"


def 从注册表读():
    if sys.platform != "win32":
        return ""
    try:
        import winreg
    except ImportError:
        return ""
    try:
        键 = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 注册表键 + "\\" + 客户端_GUID)
    except OSError:
        return ""
    try:
        return str(winreg.QueryValueEx(键, "pv")[0] or "").strip()
    except OSError:
        return ""
    finally:
        键.Close()


def 从目录找():
    找到的 = []
    for 父 in 安装目录候选:
        try:
            们 = [d for d in os.listdir(父) if d[:1].isdigit()]
        except OSError:
            continue
        找到的.extend(们)
    return sorted(找到的)[-1] if 找到的 else ""


def 判定(注册表值, 目录值):
    if 注册表值:
        return True, 注册表值, "注册表"
    if 目录值:
        return True, 目录值, "安装目录"
    return False, "", "两处都没找到"


def 查():
    return 判定(从注册表读(), 从目录找())


def 安装器路径():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 安装器名字)


def 装(超时秒=180):
    安装器 = 安装器路径()
    if not os.path.isfile(安装器):
        return False, "没有内置安装器：" + 安装器
    try:
        跑 = subprocess.run([安装器, "/silent", "/install"], timeout=超时秒,
                         capture_output=True, text=True)
    except OSError as 异常:
        return False, "安装器起不来：" + str(异常)
    except subprocess.TimeoutExpired:
        return False, "安装器跑了 %d 秒还没完" % 超时秒
    有, 版本, 依据 = 查()
    if 有:
        return True, "装上了（%s 报 %s）" % (依据, 版本)
    return False, "装完还是查不到（安装器退出码 %s）" % 跑.returncode


def 回退命令(地址, 宽度=1400, 高度=900, 候选=None):
    for 处 in (Edge候选 if 候选 is None else 候选):
        if os.path.isfile(处):
            return [处, "--app=" + 地址, "--window-size=%d,%d" % (宽度, 高度)]
    return None
