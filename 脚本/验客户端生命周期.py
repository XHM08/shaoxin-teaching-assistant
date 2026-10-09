
import ctypes
import os
import socket
import subprocess
import sys
import time
import urllib.request

user32 = ctypes.windll.user32
项目根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
产物目录 = os.path.join(项目根, "dist", "邵新")
exe路径 = os.path.join(产物目录, "邵新.exe")
WM_CLOSE = 0x0010


def 空端口():
    套 = socket.socket()
    套.bind(("127.0.0.1", 0))
    口 = 套.getsockname()[1]
    套.close()
    return 口


def 可见窗口(进程号):
    得 = []
    回调 = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def 看(句柄, _):
        号 = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(句柄, ctypes.byref(号))
        if 号.value == 进程号 and user32.IsWindowVisible(句柄):
            长 = user32.GetWindowTextLengthW(句柄)
            缓 = ctypes.create_unicode_buffer(长 + 1)
            user32.GetWindowTextW(句柄, 缓, 长 + 1)
            得.append((句柄, 缓.value))
        return True
    user32.EnumWindows(回调(看), 0)
    return 得


def 服务通(口):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/" % 口, timeout=2) as 答:
            return "邵新" in 答.read().decode("utf-8", "ignore")
    except Exception:
        return False


def 主程序():
    if not os.path.isfile(exe路径):
        print("还没有打包产物，先跑 python 脚本/打包.py：")
        print("  " + exe路径)
        return 1

    口 = 空端口()
    把手 = open(r"C:/tmp/关窗验.log", "w", encoding="utf-8")
    跑 = subprocess.Popen([exe路径], cwd=产物目录,
                       env=dict(os.environ, SHAOXIN_PORT=str(口)),
                       stdout=把手, stderr=subprocess.STDOUT)
    结论 = []
    try:
        期限 = time.time() + 40
        while time.time() < 期限 and not 服务通(口):
            time.sleep(1)
        结论.append(("窗口出来之前，本地服务已在空端口 %d 上应答" % 口, 服务通(口)))
        if not 服务通(口):
            return 报(结论, "服务没起来，后面的关窗验不了；原文见 C:/tmp/关窗验.log")

        期限 = time.time() + 30
        窗 = []
        while time.time() < 期限 and not 窗:
            time.sleep(1)
            窗 = 可见窗口(跑.pid)
        结论.append(("找到了属于它的可见窗口（%s）" % (窗[0][1] if 窗 else "无"), bool(窗)))
        if not 窗:
            return 报(结论, "找不到窗口，关不了")

        time.sleep(3)
        user32.PostMessageW(窗[0][0], WM_CLOSE, 0, 0)

        期限 = time.time() + 25
        while time.time() < 期限 and 跑.poll() is None:
            time.sleep(0.5)
        结论.append(("点关窗之后客户端退出了（退出码 %s）" % 跑.poll(), 跑.poll() is not None))
        结论.append(("窗口也消失了", not 可见窗口(跑.pid)))

        期限 = time.time() + 10
        while time.time() < 期限 and 服务通(口):
            time.sleep(0.5)
        结论.append(("它拉起来的本地服务跟着停了（端口不再应答）", not 服务通(口)))
        return 报(结论, "")
    finally:
        if 跑.poll() is None:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(跑.pid)], capture_output=True)
        把手.close()


def 报(结论, 尾):
    print()
    坏 = 0
    for 名, 过 in 结论:
        print(("  通过  " if 过 else "  失败  ") + 名)
        坏 += 0 if 过 else 1
    if 尾:
        print("  说明：" + 尾)
    print()
    print("关窗清理 %d 项全过" % len(结论) if not 坏 else "关窗清理 %d 项失败" % 坏)
    return 0 if not 坏 else 1


if __name__ == "__main__":
    sys.exit(主程序())
