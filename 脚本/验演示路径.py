
import ctypes
import os
import socket
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 桌面客户端 import 端口号

user32 = ctypes.windll.user32
项目根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
产物目录 = os.path.join(项目根, "dist", "邵新")
exe路径 = os.path.join(产物目录, "邵新.exe")
WM_CLOSE = 0x0010


def 有人听吗(口):
    套 = socket.socket()
    套.settimeout(0.5)
    try:
        套.connect(("127.0.0.1", int(口)))
        return True
    except OSError:
        return False
    finally:
        套.close()


def 服务通(口):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/" % 口, timeout=2) as 答:
            return "邵新" in 答.read().decode("utf-8", "ignore")
    except Exception:
        return False


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


def 报(结论, 尾=""):
    print()
    坏 = 0
    for 名, 过 in 结论:
        print(("  通过  " if 过 else "  失败  ") + 名)
        坏 += 0 if 过 else 1
    if 尾:
        print("  说明：" + 尾)
    print()
    print("演示路径 %d 项全过" % len(结论) if not 坏 else "演示路径 %d 项失败" % 坏)
    return 0 if not 坏 else 1


def 主程序():
    结论 = []
    if not os.path.isfile(exe路径):
        return 报([("产物里有 邵新.exe", False)],
                 "先跑 python 脚本/打包.py --干净 --冒烟")

    口 = 端口号()
    结论.append(("启动前，端口 %d 上没人在听" % 口, not 有人听吗(口)))
    if 有人听吗(口):
        return 报(结论, "先把占着 %d 的东西关掉再跑：\n"
                    "    否则下面\"服务起在端口上了\"可能是别人在应答，"
                    "验的就不是这个包。" % 口)

    把手 = open(os.path.join("C:/tmp", "演示路径.log"), "w", encoding="utf-8")
    跑 = subprocess.Popen([exe路径], cwd=产物目录,
                       stdout=把手, stderr=subprocess.STDOUT)
    try:
        期限 = time.time() + 45
        通了 = False
        while time.time() < 期限:
            if 服务通(口):
                通了 = True
                break
            time.sleep(1)
        结论.append(("双击之后，它自己把服务起在 %d 上了" % 口, 通了))
        if not 通了:
            return 报(结论, "服务没起来，原文见 C:/tmp/演示路径.log")

        期限 = time.time() + 30
        窗 = []
        while time.time() < 期限 and not 窗:
            time.sleep(1)
            窗 = 可见窗口(跑.pid)
        结论.append(("窗口开了（%s）" % (窗[0][1] if 窗 else "没开"), bool(窗)))
        if not 窗:
            return 报(结论, "窗口没出来，后面的关窗验不了")

        time.sleep(3)
        user32.PostMessageW(窗[0][0], WM_CLOSE, 0, 0)

        期限 = time.time() + 25
        while time.time() < 期限 and 跑.poll() is None:
            time.sleep(0.5)
        结论.append(("关窗后客户端退出（退出码 %s）" % 跑.poll(), 跑.poll() is not None))
        结论.append(("窗口也消失了", not 可见窗口(跑.pid)))

        期限 = time.time() + 12
        while time.time() < 期限 and 服务通(口):
            time.sleep(0.5)
        结论.append(("它起的服务跟着停了（%d 空了）" % 口, not 服务通(口)))
        return 报(结论)
    finally:
        if 跑.poll() is None:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(跑.pid)], capture_output=True)
        把手.close()


if __name__ == "__main__":
    sys.exit(主程序())
