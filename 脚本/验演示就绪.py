
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

项目根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
产物目录 = os.path.join(项目根, "dist", "邵新")
exe路径 = os.path.join(产物目录, "邵新.exe")


def 空端口():
    套 = socket.socket()
    套.bind(("127.0.0.1", 0))
    口 = 套.getsockname()[1]
    套.close()
    return 口


def 读密钥们(目录):
    得 = []
    if not os.path.isdir(目录):
        return 得
    for 名 in sorted(os.listdir(目录)):
        if not 名.lower().endswith(".txt"):
            continue
        with open(os.path.join(目录, 名), encoding="utf-8", errors="replace") as 文件:
            文 = 文件.read().strip()
        if 文:
            得.append(文)
    return 得


def 问(口, 数据):
    请求 = urllib.request.Request(
        "http://127.0.0.1:%d/api/run" % 口,
        data=json.dumps(数据, ensure_ascii=False).encode("utf-8"),
        headers={"Origin": "http://127.0.0.1:%d" % 口,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(请求, timeout=30) as 答:
        return 答.status, json.loads(答.read().decode("utf-8"))


def 主程序():
    结论 = []

    结论.append(("产物里有 邵新.exe", os.path.isfile(exe路径)))
    配置路径 = os.path.join(产物目录, "服务商.json")
    结论.append(("产物里有 服务商.json", os.path.isfile(配置路径)))
    密钥们 = 读密钥们(os.path.join(产物目录, "密钥"))
    结论.append(("产物里 密钥/ 下有非空的 .txt（%d 个）" % len(密钥们), bool(密钥们)))
    if not all(过 for _名, 过 in 结论):
        return 报(结论, "前提就不齐，先补：\n"
                    "    copy 密钥 " + os.path.join("dist", "邵新", "密钥") + "\n"
                    "    copy 服务商.json " + os.path.join("dist", "邵新"))

    当前服务商 = ""
    try:
        with open(配置路径, encoding="utf-8") as 文件:
            表 = json.load(文件)
        当前服务商 = str(表.get("default") or "")
    except (OSError, ValueError) as 异常:
        结论.append(("服务商.json 能读能解析（%s）" % type(异常).__name__, False))
        return 报(结论, "服务商.json 读不出来，演示时点开会是空的")

    结论.append(("服务商.json 里写明了当前用哪家（%s）" % (当前服务商 or "空"), bool(当前服务商)))
    if not 当前服务商:
        return 报(结论, "服务商.json 里 default 是空的")

    口 = 空端口()
    把手 = open(os.path.join("C:/tmp", "演示就绪.log"), "w", encoding="utf-8")
    跑 = subprocess.Popen([exe路径, "服务"], cwd=产物目录,
                       env=dict(os.environ, SHAOXIN_PORT=str(口)),
                       stdout=把手, stderr=subprocess.STDOUT)
    try:
        期限 = time.time() + 40
        通了 = False
        while time.time() < 期限:
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/" % 口, timeout=2) as 答:
                    通了 = "邵新" in 答.read().decode("utf-8", "ignore")
            except Exception:
                pass
            if 通了:
                break
            time.sleep(1)
        结论.append(("包内服务在空端口 %d 上起来了" % 口, 通了))
        if not 通了:
            return 报(结论, "服务没起来，原文见 C:/tmp/演示就绪.log")

        _码, 果 = 问(口, {"能力": "模型配置", "参数": {}})
        正文 = json.dumps(果, ensure_ascii=False)
        条目 = 果.get("条目") or []

        当条 = [x for x in 条目 if x.get("当前") == "是"]
        结论.append(("「模型配置」列出了当前那家（%s）" % (当条[0]["代号"] if 当条 else "没有"),
                    len(当条) == 1))
        if 当条:
            状态 = str(当条[0].get("密钥") or "")
            结论.append(("当前那家（%s）的密钥状态是「%s」，不是未配置" % (当条[0]["代号"], 状态),
                        bool(状态) and "未配置" not in 状态))

        漏了 = [k for k in 密钥们 if k and k in 正文]
        结论.append(("返回的正文里不出现任何一把真密钥（比了 %d 把）" % len(密钥们), not 漏了))

        _码, 果2 = 问(口, {"能力": "环境配置", "参数": {}})
        结论.append(("「环境配置」也答得上来（没有「错误」字段）", "错误" not in 果2))
    except Exception as 异常:
        结论.append(("问能力时没抛异常（%s：%s）" % (type(异常).__name__, str(异常)[:60]), False))
    finally:
        if 跑.poll() is None:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(跑.pid)], capture_output=True)
        把手.close()

    过, 说明 = 不接管陌生服务()
    结论.append(("跑法不接管陌生服务（私人端口上装个冒充的，它应当拒绝并退出 2）" + 说明, 过))

    return 报(结论, "")


def 不接管陌生服务():
    出 = subprocess.run([sys.executable, os.path.join(项目根, "脚本", "验_不接管陌生服务.py")],
                      cwd=项目根, capture_output=True, text=True, encoding="utf-8",
                      errors="replace", timeout=240)
    if 出.returncode == 0:
        return True, ""
    尾 = [l.strip() for l in ((出.stdout or "") + (出.stderr or "")).splitlines() if l.strip()]
    return False, "｜" + (尾[-1][:70] if 尾 else "（它没有输出）")


def 报(结论, 尾):
    print()
    坏 = 0
    for 名, 过 in 结论:
        print(("  通过  " if 过 else "  失败  ") + 名)
        坏 += 0 if 过 else 1
    if 尾:
        print("  说明：" + 尾)
    print()
    print("演示就绪 %d 项全过" % len(结论) if not 坏 else "演示就绪 %d 项失败" % 坏)
    return 0 if not 坏 else 1


if __name__ == "__main__":
    sys.exit(主程序())
