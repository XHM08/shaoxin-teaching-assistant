
import atexit
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)
日志目录 = r"C:/tmp/跑全部"
保留目录 = r"C:/tmp/跑全部_失败"
要确认的 = "_会写盘.py"
超时秒 = 290

服务_我起的 = None
日志把手 = []


def 端口号():
    from 地基 import 配置
    return 配置.取端口()


def 端口被占():
    套 = socket.socket()
    套.settimeout(1)
    try:
        套.connect(("127.0.0.1", 端口号()))
        return True
    except OSError:
        return False
    finally:
        套.close()


def 服务在吗():
    try:
        页 = urllib.request.urlopen("http://127.0.0.1:%d/" % 端口号(), timeout=3).read(4096)
    except Exception:
        return False
    return "邵新" in 页.decode("utf-8", "replace")


def 关服务():
    global 服务_我起的
    if 服务_我起的 is None:
        return
    跑 = 服务_我起的
    服务_我起的 = None
    if 跑.poll() is None:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(跑.pid)], capture_output=True)
    while 日志把手:
        日志把手.pop().close()


def 起服务():
    global 服务_我起的
    if 服务在吗():
        print("（%d 上已经有一个邵新的服务，就用它，跑完不动它）" % 端口号())
        return
    if 端口被占():
        print("！%d 上有个东西在听，但它不是邵新的服务（拿不到含「邵新」的页面）。" % 端口号())
        print("  先把它关掉再跑。查是谁：netstat -ano | findstr :%d" % 端口号())
        print("  再 taskkill /F /T /PID <上面那个 PID>。这次不接它，免得结果说不清是谁的问题。")
        sys.exit(2)
    把手 = open(r"C:/tmp/跑全部_服务.log", "w", encoding="utf-8")
    日志把手.append(把手)
    跑 = subprocess.Popen([sys.executable, "本地服务.py"], cwd=根,
                       stdout=把手, stderr=subprocess.STDOUT)
    服务_我起的 = 跑
    atexit.register(关服务)
    期限 = time.time() + 45
    while time.time() < 期限:
        if 服务在吗():
            print("（%d 上原来没服务，跑法自己起了一个，跑完会关掉）" % 端口号())
            return
        time.sleep(1)
    print("（想自己起服务但没起来，见 C:/tmp/跑全部_服务.log；要服务的那 7 条会红）")


def 分类(码, 输出):
    结论词 = (r"项通过|通过数|都对得上|都画得出来|(?<!不)正常。|个能力和|与现场一致|处对不上"
         r"|\d+\s*/\s*\d+|通过\s*\d+\s*/\s*共")
    if 码 == 0:
        说跳过 = re.search(r"跳过|没验|未验", 输出)
        if 说跳过 and not re.search(结论词, 输出):
            return "跳过", "它自己说了跳过/没验"
        if not re.search(结论词, 输出):
            return "无计数", "退出码 0，但没有可解析的收尾行。要看一眼"
        if 说跳过:
            return "通过", "（它同时说了跳过/没验，自己看一眼那几句）"
        return "通过", ""
    if 码 == 3:
        return "跳过", "自检按约定用 3 表示跳过"
    if 码 == 124:
        return "超时", "超过 %d 秒被掐" % 超时秒
    return "失败", "退出码 %s" % 码


def main():
    只看失败 = "--只看失败" in sys.argv
    os.makedirs(日志目录, exist_ok=True)
    起服务()
    if os.path.isdir(保留目录):
        shutil.rmtree(保留目录, ignore_errors=True)
    脚本 = sorted(x for x in os.listdir(os.path.join(根, "脚本"))
                if x.startswith("检查_") and x.endswith(".py"))
    状态表 = []
    起 = time.time()
    for 名 in 脚本:
        命令 = [sys.executable, os.path.join("脚本", 名)]
        if 名.endswith(要确认的):
            命令.append("--确认")
        日志 = os.path.join(日志目录, 名[:-3] + ".log")
        try:
            with open(日志, "w", encoding="utf-8") as 文件:
                跑 = subprocess.Popen(命令, cwd=根, stdout=文件, stderr=subprocess.STDOUT)
                try:
                    码 = 跑.wait(timeout=超时秒)
                except subprocess.TimeoutExpired:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(跑.pid)],
                                   capture_output=True)
                    try:
                        跑.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        pass
                    码 = 124
        except OSError as 错:
            码 = 1
            print("  ！%s 起不来：%r" % (名, 错))
        输出 = ""
        if os.path.isfile(日志):
            with open(日志, encoding="utf-8", errors="replace") as 文件:
                输出 = 文件.read()
        状态, 说明 = 分类(码, 输出)
        尾行 = [x.strip() for x in 输出.splitlines() if x.strip()]
        状态表.append((名, 状态, 尾行[-1][:64] if 尾行 else "(没有输出)", 说明, 日志))
        if 状态 in ("失败", "超时", "无计数"):
            os.makedirs(保留目录, exist_ok=True)
            shutil.copy2(日志, os.path.join(保留目录, 名[:-3] + ".log"))

    计 = {}
    for _名, 状态, _尾, _说, _日 in 状态表:
        计[状态] = 计.get(状态, 0) + 1
    print("共 %d 条自检，用了 %.0f 秒" % (len(状态表), time.time() - 起))
    print("  " + "  ".join("%s %d" % (k, 计.get(k, 0)) for k in ("通过", "失败", "跳过", "超时", "无计数") if 计.get(k)))
    print()
    for 名, 状态, 尾, 说明, 日志 in 状态表:
        if 只看失败 and 状态 == "通过":
            continue
        记号 = {"通过": "✓", "失败": "✗", "跳过": "·", "超时": "…", "无计数": "?"}[状态]
        print("  %s %-28s %-4s %s%s" % (记号, 名, 状态, 尾, ("　← " + 说明) if 说明 else ""))
    if 计.get("失败") or 计.get("超时"):
        print("\n失败/超时的原文留在：%s" % 保留目录)
    if 计.get("跳过"):
        print("跳过的那几条不算通过：%s" % "、".join(
            名 for 名, 状态, _t, _s, _l in 状态表 if 状态 == "跳过"))
    关服务()
    return 1 if (计.get("失败") or 计.get("超时") or 计.get("无计数")) else 0


if __name__ == "__main__":
    sys.exit(main())
