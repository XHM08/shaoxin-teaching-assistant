
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

项目根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
产物目录 = os.path.join(项目根, "dist", "邵新")
exe路径 = os.path.join(产物目录, "邵新.exe")

必须有 = [
    "邵新.exe",
    os.path.join("网页", "首页.html"),
    os.path.join("网页", "样式.css"),
    os.path.join("地基", "版本.py"),
    os.path.join("地基", "本机OCR.ps1"),
    os.path.join("能力", "课件生成.py"),
    os.path.join("提示词", "课件生成.md"),
    os.path.join("语音", "启动语音服务.py"),
    os.path.join("语音", "说明.md"),
    "MicrosoftEdgeWebview2Setup.exe",
    "邵新.ico",
]
绝不能有 = ["密钥", "学生数据", "材料", "课件输出", "技能包", "日志", "教师数据",
        "设计", ".git", os.path.join("语音", "参考音")]

发布版配置 = '{\n  "合规": {\n    "同意书已签": false\n  }\n}\n'


def 跑打包(干净=False):
    if 干净:
        for 处 in (os.path.join(项目根, "build"), 产物目录):
            shutil.rmtree(处, ignore_errors=True)
    命令 = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
           os.path.join(项目根, "邵新.spec")]
    print("跑：" + " ".join(命令))
    return subprocess.run(命令, cwd=项目根).returncode


def 换发布版配置():
    路径 = os.path.join(产物目录, "配置.json")
    with open(路径, "w", encoding="utf-8", newline="\n") as 文件:
        文件.write(发布版配置)
    return 路径


def 核对():
    坏的 = []
    for 相对 in 必须有:
        if not os.path.exists(os.path.join(产物目录, 相对)):
            坏的.append("缺少：" + 相对)
    for 相对 in 绝不能有:
        if os.path.exists(os.path.join(产物目录, 相对)):
            坏的.append("不该有的东西在里面：" + 相对)
    if not os.path.isfile(exe路径):
        坏的.append("没有 exe：" + exe路径)
    elif os.path.getsize(exe路径) < 1024 * 1024:
        坏的.append("exe 太小（%d 字节），像是打包被截断了"
                   % os.path.getsize(exe路径))

    配置路径 = os.path.join(产物目录, "配置.json")
    if not os.path.isfile(配置路径):
        坏的.append("包内没有 配置.json")
    else:
        try:
            表 = json.loads(open(配置路径, encoding="utf-8").read())
        except (OSError, ValueError) as 异常:
            表 = None
            坏的.append("包内 配置.json 读不出来：" + str(异常))
        if isinstance(表, dict):
            原文 = open(配置路径, encoding="utf-8").read()
            if (表.get("命令") or {}).get("默认档位"):
                坏的.append("包内 配置.json 还带着「默认档位」。别人一装就什么都不问")
            if (表.get("合规") or {}).get("同意书已签") is not False:
                坏的.append("包内 同意书已签 不是 false（不该继承开发机的状态）")
            if "C:/Users/" in 原文 or "C:\\\\Users\\\\" in 原文:
                坏的.append("包内 配置.json 带着开发机路径")
    return 坏的


def 空端口():
    套 = socket.socket()
    套.bind(("127.0.0.1", 0))
    口 = 套.getsockname()[1]
    套.close()
    return 口


def 收掉树(跑):
    if 跑.poll() is not None:
        return
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(跑.pid)],
                   capture_output=True)
    try:
        跑.wait(timeout=8)
    except subprocess.TimeoutExpired:
        跑.kill()


def 冒烟服务():
    口 = 空端口()
    日志 = r"C:/tmp/打包冒烟.log"
    把手 = open(日志, "w", encoding="utf-8")
    跑 = subprocess.Popen([exe路径, "服务"], cwd=产物目录,
                       env=dict(os.environ, SHAOXIN_PORT=str(口)),
                       stdout=把手, stderr=subprocess.STDOUT)
    try:
        期限 = time.time() + 30
        while time.time() < 期限:
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/" % 口, timeout=2) as 答:
                    if "邵新" in 答.read().decode("utf-8", "ignore"):
                        return True, "「服务」在空端口 %d 上应答了" % 口
            except Exception:
                pass
            time.sleep(0.5)
        return False, "「服务」30 秒没应答（原文见 " + 日志 + "）"
    finally:
        收掉树(跑)
        把手.close()


def 冒烟客户端():
    口 = 空端口()
    日志 = r"C:/tmp/客户端冒烟.log"
    把手 = open(日志, "w", encoding="utf-8")
    跑 = subprocess.Popen([exe路径], cwd=产物目录,
                       env=dict(os.environ, SHAOXIN_PORT=str(口)),
                       stdout=把手, stderr=subprocess.STDOUT)
    try:
        time.sleep(10)
        码 = 跑.poll()
        if 码 is None:
            return True, "第 10 秒还活着（窗口这会儿是开着的）"
        原文 = open(日志, encoding="utf-8", errors="replace").read().strip()
        return False, "第 10 秒前就退了，退出码 %s；它说：%s" % (码, 原文[:200] or "（没输出）")
    finally:
        收掉树(跑)
        把手.close()


def 主程序():
    码 = 跑打包(干净="--干净" in sys.argv)
    if 码 != 0:
        print("PyInstaller 退出码 %s，打包没成。" % 码)
        return 1

    换发布版配置()
    坏的 = 核对()
    if 坏的:
        print("产物核对不通过：")
        for 一条 in 坏的:
            print("  " + 一条)
        return 1

    总 = sum(os.path.getsize(os.path.join(根, 名))
           for 根, _目录们, 文件们 in os.walk(产物目录) for 名 in 文件们)
    print("产物：" + 产物目录)
    print("%d 项必须有都在，%d 项不该有的都不在，配置也是发布版，都对得上"
          % (len(必须有), len(绝不能有)))
    print("体积 %.1f MB" % (总 / 1024.0 / 1024.0))

    if "--冒烟" in sys.argv:
        坏 = 0
        for 名字, 函数 in (("服务", 冒烟服务), ("客户端", 冒烟客户端)):
            成, 说明 = 函数()
            print(("冒烟通过「%s」：" % 名字 if 成 else "冒烟失败「%s」：" % 名字) + 说明)
            坏 += 0 if 成 else 1
        码 = subprocess.run([sys.executable,
                         os.path.join(项目根, "脚本", "验客户端生命周期.py")]).returncode
        print(("冒烟通过「关窗清理」" if 码 == 0 else "冒烟失败「关窗清理」")
              + "：见上面的逐项结果")
        坏 += 0 if 码 == 0 else 1
        if 坏:
            return 1
    else:
        print("（没跑 --冒烟；加上它才会真起一次「服务」和「客户端」，并验关窗清理）")
    return 0


if __name__ == "__main__":
    sys.exit(主程序())
