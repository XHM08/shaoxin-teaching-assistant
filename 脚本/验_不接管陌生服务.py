import http.server
import os
import socket
import subprocess
import sys
import threading

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

冒充页 = "我是别的程序"


class 冒充(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(冒充页.encode("utf-8"))

    def log_message(self, *a):
        pass


def 空端口():
    套 = socket.socket()
    套.bind(("127.0.0.1", 0))
    口 = 套.getsockname()[1]
    套.close()
    return 口


def 判据(码, 输出, 冒充还活着):
    if 码 != 2:
        return False, "退出码是 %s，应当是 2（拒绝接管）" % 码
    if "它不是邵新的服务" not in 输出:
        return False, "没有说出「它不是邵新的服务」，只在日志里留了别的原因"
    if not 冒充还活着:
        return False, "冒充的那个进程被杀了，别人的进程不该动"
    return True, "拒绝接管、说清了原因、也没动别人的进程"


def 自测():
    ok = [
        (判据(2, "！8765 上有个东西在听，但它不是邵新的服务", True), True),
        (判据(0, "！它不是邵新的服务", True), False),
        (判据(2, "（8765 上已经有一个邵新的服务，就用它）", True), False),
        (判据(2, "它不是邵新的服务", False), False),
    ]
    坏 = [(过, 说明, 期望) for (过, 说明), 期望 in ok if 过 is not 期望]
    for (过, 说明), 期望 in ok:
        print("  %s 期望 %s，实得 %s  %s" % ("✓" if 过 is 期望 else "✗", 期望, 过, 说明))
    if 坏:
        print("自测没过：判据函数在合成输入上给错了结论")
        return 1
    print("自测 4 条全过：码不对 / 没说原因 / 杀了别人的进程，三种都判得出来")
    return 0


def main():
    if "--自测" in sys.argv:
        return 自测()

    口 = 空端口()
    服务 = http.server.ThreadingHTTPServer(("127.0.0.1", 口), 冒充)
    线 = threading.Thread(target=服务.serve_forever, daemon=True)
    线.start()
    print("冒充的服务已装到 127.0.0.1:%d（不是邵新）" % 口)

    env = dict(os.environ, SHAOXIN_PORT=str(口))
    跑 = subprocess.run([sys.executable, os.path.join("脚本", "跑全部自检.py")],
                        cwd=根, env=env, capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=120)
    输出 = (跑.stdout or "") + (跑.stderr or "")
    print("---- 跑法说的话 ----")
    for 行 in 输出.splitlines()[:6]:
        print("  " + 行)

    还活着 = 线.is_alive()
    try:
        套 = socket.socket()
        套.settimeout(2)
        套.connect(("127.0.0.1", 口))
        套.close()
    except OSError:
        还活着 = False

    过, 说明 = 判据(跑.returncode, 输出, 还活着)
    服务.shutdown()
    服务.server_close()
    print("\n%s %s" % ("通过" if 过 else "失败", 说明))
    return 0 if 过 else 1


if __name__ == "__main__":
    sys.exit(main())
