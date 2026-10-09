import os
import re
import shutil
import socket
import subprocess
import sys
import time

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)

from 地基 import 配置

出目录默认 = r"C:/tmp/浸泡5"


def 进程表():
    命令 = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
            "Select-Object ProcessId,CommandLine | ConvertTo-Csv -NoTypeInformation")
    try:
        出 = subprocess.run(["powershell.exe", "-NoProfile", "-Command", 命令],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if 出.returncode != 0 or not (出.stdout or "").strip():
        return None
    表 = []
    for 行 in 出.stdout.splitlines()[1:]:
        块 = re.findall(r'"((?:[^"]|"")*)"', 行)
        if len(块) >= 2 and 块[0].isdigit():
            表.append((int(块[0]), 块[1]))
    return 表


def 找出浸泡(表, 出目录):
    if 表 is None:
        return None
    中 = []
    for pid, 命令 in 表:
        if pid == os.getpid():
            continue
        c = 命令.replace("\\", "/").lower()
        if not re.search(r"(?<!看住)浸泡\.py", c):
            continue
        if 出目录.replace("\\", "/").lower() in c:
            中.append(pid)
    return 中


def 有人听(口, 超时=1.0):
    套 = socket.socket()
    套.settimeout(超时)
    try:
        套.connect(("127.0.0.1", 口))
        return True
    except OSError:
        return False
    finally:
        套.close()


def 听者的pid(口):
    出 = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    for 行 in (出.stdout or "").splitlines():
        if "LISTENING" in 行 and re.search(r":%d\s" % 口, 行):
            return int(行.split()[-1])
    return None


def 已跑几轮(出目录):
    若 = [f for f in os.listdir(出目录)
          if re.match(r"^第\d+轮\.log$", f)] if os.path.isdir(出目录) else []
    return len(若)


def 判断(泡着们, 口有人, 轮数):
    if 泡着们 is None:
        return "等人看一眼", "拿不到进程表（PowerShell/WMI 没给结果），不敢当它死了"
    if 泡着们 and 口有人:
        return "啥也不用做", "浸泡在跑（PID %s），端口上那个就是它这一轮起的服务" % 泡着们[0]
    if 泡着们:
        return "啥也不用做", "浸泡在跑（PID %s），此刻是轮间歇（端口空）" % 泡着们[0]
    if 口有人:
        return "等人看一眼", "浸泡不在了，但端口上有人听着，先别抢，等下一轮再看"
    return "重起", "浸泡不在了（原定 %d 轮），端口是空的，可以接着跑" % 轮数


def 备份日志(出目录):
    到 = "%s-已跑%d轮" % (出目录.rstrip("/\\"), 已跑几轮(出目录))
    到 = 到.replace("\\", "/")
    if os.path.isdir(到):
        到 += "-%s" % time.strftime("%H%M%S")
    shutil.copytree(出目录, 到)
    return 到


def 拿锁(出目录, 最多留秒=300):
    锁 = (出目录.rstrip("/\\") + ".看住.lock").replace("\\", "/")
    if os.path.isfile(锁):
        try:
            if time.time() - os.path.getmtime(锁) < 最多留秒:
                return None
        except OSError:
            pass
    try:
        with open(锁, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except OSError:
        return None
    return 锁


def 放锁(锁):
    if 锁:
        try:
            os.remove(锁)
        except OSError:
            pass


def 重起(出目录, 轮数, 间隔):
    cmd = ("Start-Process -FilePath '%s' -ArgumentList '%s','%d','%s','%s' "
           "-WorkingDirectory '%s' -WindowStyle Hidden "
           "-RedirectStandardOutput '%s-控制台.log' -RedirectStandardError '%s-控制台.err.log'"
           % (sys.executable, os.path.join("脚本", "浸泡.py"), 轮数, 间隔,
             出目录.replace("\\", "/"), os.path.abspath(根).replace("\\", "/"),
              出目录.replace("\\", "/"), 出目录.replace("\\", "/")))
    出 = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
    期限 = time.time() + 12
    while time.time() < 期限:
        if 找出浸泡(进程表(), 出目录):
            return True, ""
        time.sleep(0.5)
    return False, (出.stderr or "").strip()[:200]


def 自测():
    ok = [
        (判断([1234], True, 11), "啥也不用做"),
        (判断([1234], False, 11), "啥也不用做"),
        (判断([], False, 11), "重起"),
        (判断([], True, 11), "等人看一眼"),
        (判断(None, False, 11), "等人看一眼"),
    ]
    坏 = 0
    for (做, 说), 期望 in ok:
        print("  %s 期望「%s」，实得「%s」  %s" % ("✓" if 做 == 期望 else "✗", 期望, 做, 说))
        坏 += 0 if 做 == 期望 else 1
    假自己 = os.getpid()
    表 = [(假自己, "python.exe 脚本/看住浸泡.py --出目录 C:/tmp/浸泡5"),
          (999999, "python.exe 脚本/浸泡.py 11 25 C:/tmp/浸泡5")]
    找 = 找出浸泡(表, "C:/tmp/浸泡5")
    对 = 找 == [999999]
    print("  %s 找出浸泡：命令行里混着「看住浸泡.py」和「浸泡.py」时，只认后者（实得 %r）"
          % ("✓" if 对 else "✗", 找))
    坏 += 0 if 对 else 1
    if 坏:
        print("自测没过：判断() 或 找出浸泡() 在合成输入上给错了结论")
        return 1
    print("自测 6 条全过：在跑/轮间歇/该重起/端口被陌生人占/枚举失败/不认自己")
    return 0


def main():
    if "--自测" in sys.argv:
        return 自测()

    def 取值(名, 默认):
        return sys.argv[sys.argv.index(名) + 1] if 名 in sys.argv else 默认

    出目录 = 取值("--出目录", 出目录默认)
    轮数 = int(取值("--轮数", 11))
    间隔 = 取值("--间隔", "25")
    口 = int(取值("--端口", 配置.取端口()))

    锁 = 拿锁(出目录)
    try:
        泡着 = 找出浸泡(进程表(), 出目录)
        做, 说明 = 判断(泡着, 有人听(口), 轮数)
        print("浸泡：%s" % 说明)
        if os.path.isdir(出目录):
            print("进度：已跑 %d 轮 / 共 %d 轮（%s）"
                  % (已跑几轮(出目录), 轮数, os.path.join(出目录, "轮次表.tsv")))
        else:
            print("进度：出目录还没有（%s）" % 出目录)

        if 做 == "啥也不用做":
            return 0
        if 做 == "等人看一眼":
            pid = 听者的pid(口)
            print("  端口上那个 PID=%s。若它确实是邵新留下的孤儿（命令行是 本地服务.py），就收掉："
                  % pid)
            print("      taskkill /F /T /PID %s" % pid)
            return 1

        if 锁 is None:
            print("  另一个看住浸泡正在动手（锁还在），这次不动")
            return 0
        到 = 备份日志(出目录) if os.path.isdir(出目录) else None
        print("  已把已有日志备份到：%s" % (到 if 到 else "（还没有日志要备份）"))
        孤 = 听者的pid(口)
        if 孤:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(孤)], capture_output=True)
            print("  顺手收掉端口上的孤儿进程（PID %s）" % 孤)
        起了, 错 = 重起(出目录, 轮数, 间隔)
        print("  重起：%s" % ("成功" if 起了 else "没起来（看 %s-控制台.err.log）" % 出目录))
        if 错:
            print("  powershell 说：" + 错)
        return 0 if 起了 else 1
    finally:
        放锁(锁)


if __name__ == "__main__":
    sys.exit(main())
