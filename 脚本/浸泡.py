import io
import os
import re
import shutil
import socket
import subprocess
import sys
import time

根 = r"C:/Users/25768/Desktop/样本"
出目录 = r"C:/tmp/浸泡4"
失败源 = r"C:/tmp/跑全部_失败"

sys.path.insert(0, 根)
from 地基 import 配置

口 = 配置.取端口()
口语音 = 9880


def 有人听吗(端口=None, 超时=1.0):
    套 = socket.socket()
    套.settimeout(超时)
    try:
        套.connect(("127.0.0.1", 端口 or 口))
        return True
    except OSError:
        return False
    finally:
        套.close()


def 等端口空(最多秒=60):
    期限 = time.time() + 最多秒
    while time.time() < 期限:
        if not 有人听吗():
            return True
        time.sleep(2)
    return not 有人听吗()


def 主程序():
    global 出目录
    轮数 = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    间隔分 = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0
    if len(sys.argv) > 3:
        出目录 = sys.argv[3]

    os.makedirs(出目录, exist_ok=True)
    表 = os.path.join(出目录, "轮次表.tsv")
    首行 = ["轮次", "开始时间", "用了秒", "共", "通过", "失败", "跳过", "超时",
           "无计数", "跑前8765", "跑后8765", "退出码"]
    if not os.path.isfile(表):
        with io.open(表, "w", encoding="utf-8", newline="") as f:
            f.write("\t".join(首行) + "\n")
    现场表 = os.path.join(出目录, "端口现场.tsv")
    if not os.path.isfile(现场表):
        with io.open(现场表, "w", encoding="utf-8", newline="") as f:
            f.write("轮次\t跑前8765\t跑后8765\t跑前9880\t跑后9880\n")

    摘要 = re.compile(r"共\s*(\d+)\s*条自检，用了\s*(\d+)\s*秒")

    for i in range(1, 轮数 + 1):
        开始 = time.strftime("%m-%d %H:%M:%S")
        这轮起 = time.time()
        print("[第 %d/%d 轮] %s" % (i, 轮数, 开始), flush=True)

        跑前有 = 有人听吗()
        跑前语音 = 有人听吗(口语音)
        if 跑前有:
            print("  跑前 %d 上有东西，等它空出来（最多 60 秒）" % 口, flush=True)
            等端口空(60)

        码 = None
        原 = ""
        超时秒 = 900
        try:
            跑 = subprocess.Popen(
                [sys.executable, os.path.join("脚本", "跑全部自检.py")],
                cwd=根, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace")
            try:
                原 = 跑.communicate(timeout=超时秒)[0] or ""
                码 = 跑.returncode
            except subprocess.TimeoutExpired:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(跑.pid)],
                               capture_output=True)
                try:
                    原 = 跑.communicate(timeout=15)[0] or ""
                except Exception:
                    pass
                码 = 124
        except Exception as 错:
            码 = -1
            原 = "本轮跑法异常：%r" % (错,)

        日志 = os.path.join(出目录, "第%02d轮.log" % i)
        with io.open(日志, "w", encoding="utf-8", newline="") as f:
            f.write(原)

        共 = 用了 = ""
        m = 摘要.search(原)
        if m:
            共, 用了 = m.group(1), m.group(2)
        四 = {"通过": "0", "失败": "0", "跳过": "0", "超时": "0", "无计数": "0"}
        汇总行 = ""
        行们 = 原.splitlines()
        for j, l in enumerate(行们):
            if 摘要.search(l):
                for k in 行们[j + 1:]:
                    if k.strip():
                        汇总行 = k
                        break
                break
        抓到 = dict(re.findall(r"(通过|失败|跳过|超时|无计数)\s*(\d+)", 汇总行))
        四.update(抓到)
        解析不出 = not 抓到
        if 解析不出:
            四 = {k: "" for k in 四}

        跑后有 = 有人听吗()
        跑后语音 = 有人听吗(口语音)

        有失败 = 解析不出 or any(v and v != "0" for k, v in 四.items() if k != "通过")
        if 有失败 or 码 not in (0, None):
            到 = os.path.join(出目录, "失败日志", "第%02d轮" % i)
            os.makedirs(到, exist_ok=True)
            if os.path.isdir(失败源):
                for 名 in os.listdir(失败源):
                    try:
                        shutil.copy2(os.path.join(失败源, 名), os.path.join(到, 名))
                    except OSError:
                        pass
            print("  这一轮有非绿：%s（原文 %s）" % (四, 到), flush=True)
        else:
            print("  全绿：共 %s 条，通过 %s，用了 %s 秒" % (共, 四["通过"], 用了), flush=True)

        with io.open(表, "a", encoding="utf-8", newline="") as f:
            f.write("\t".join([
                str(i), 开始, str(用了), str(共), str(四["通过"]), str(四["失败"]),
                str(四["跳过"]), str(四["超时"]), str(四["无计数"]),
                "有" if 跑前有 else "空", "有" if 跑后有 else "空", str(码)]) + "\n")
        with io.open(现场表, "a", encoding="utf-8", newline="") as f:
            f.write("\t".join([str(i), "有" if 跑前有 else "空", "有" if 跑后有 else "空",
                               "有" if 跑前语音 else "空",
                               "有" if 跑后语音 else "空"]) + "\n")

        if i < 轮数:
            睡 = max(0.0, 间隔分 * 60 - (time.time() - 这轮起))
            print("  下一轮隔 %.1f 分钟" % (睡 / 60.0), flush=True)
            time.sleep(睡)

    print("浸泡结束，轮次表：" + 表, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(主程序())
