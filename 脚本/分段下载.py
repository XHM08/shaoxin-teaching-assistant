
import json
import os
import shutil
import struct
import sys
import threading
import time
import urllib.request

块大小 = 32 * 1024 * 1024
最少合理长度 = 1024 * 1024
临时根 = os.path.join(os.environ.get("TEMP", "C:/tmp"), "分段下载")


def 探长(url):
    请求 = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(请求, timeout=30) as 回:
        支持 = (回.headers.get("Accept-Ranges") or "").lower()
        长 = 回.headers.get("X-Linked-Size") or 回.headers.get("Content-Length")
    if not 长:
        raise SystemExit("服务器没给文件长度，换一个地址")
    长 = int(长)
    if 长 < 最少合理长度:
        raise SystemExit("拿到的长度只有 %d 字节，多半是错误页或跳转体，先自己 curl -I 看一眼" % 长)
    return 长


def 下一段(url, 起, 止, 路, 记录, 重试=8):
    应长 = 止 - 起 + 1
    最后错 = ""
    for 第 in range(重试):
        要 = 起
        if os.path.isfile(路):
            要 = 起 + os.path.getsize(路)
        if 要 > 止:
            return True, ""
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers={"Range": "bytes=%d-%d" % (要, 止)}),
                    timeout=60) as 回:
                if 回.status != 206:
                    raise RuntimeError("服务器没按范围返回（HTTP %d），这条地址不支持分段" % 回.status)
                段 = 回.headers.get("Content-Range", "")
                if not 段.startswith("bytes %d-" % 要):
                    raise RuntimeError("Content-Range 对不上：%s" % 段)
                with open(路, "ab") as 文件:
                    while True:
                        b = 回.read(262144)
                        if not b:
                            break
                        文件.write(b)
        except Exception as 异:
            最后错 = "%s %s" % (type(异).__name__, str(异)[:120])
            time.sleep(min(30, 2 + 第 * 3))
    已 = os.path.getsize(路) if os.path.isfile(路) else 0
    return False, "下了 %d/%d 字节，最后错误：%s" % (已, 应长, 最后错)


def 校验(路):
    try:
        with open(路, "rb") as f:
            头长 = struct.unpack("<Q", f.read(8))[0]
            头 = json.loads(f.read(头长))
        头.pop("__metadata__", None)
        末 = max(v["data_offsets"][1] for v in 头.values())
        return 8 + 头长 + 末
    except Exception as 异:
        raise SystemExit("读 safetensors 头部失败（%s），文件多半是坏的" % type(异).__name__)


def 主():
    if len(sys.argv) < 3:
        raise SystemExit("用法：python 脚本/分段下载.py <url> <目标文件> [连接数]")
    url, 目标 = sys.argv[1], sys.argv[2]
    线 = int(sys.argv[3]) if len(sys.argv) > 3 else 12

    总 = 探长(url)
    段们, 起 = [], 0
    while 起 < 总:
        止 = min(起 + 块大小 - 1, 总 - 1)
        段们.append((起, 止))
        起 = 止 + 1

    临时 = os.path.join(临时根, os.path.basename(目标).replace(".", "_"))
    os.makedirs(临时, exist_ok=True)
    print("总长 %.2f GB，切成 %d 段，%d 线并发，分片放 %s"
          % (总 / 1073741824.0, len(段们), 线, 临时))

    待做 = list(enumerate(段们))
    锁 = threading.Lock()
    已完字节 = [0]
    失败们 = {}

    def 干():
        while True:
            with 锁:
                if not 待做:
                    return
                号, (起, 止) = 待做.pop(0)
            路 = os.path.join(临时, "%05d.part" % 号)
            成, 错 = 下一段(url, 起, 止, 路)
            with 锁:
                if 成:
                    已完字节[0] += 止 - 起 + 1
                    print("  %.2f / %.2f GB" % (已完字节[0] / 1073741824.0, 总 / 1073741824.0), flush=True)
                else:
                    失败们[号] = 错

    线程们 = [threading.Thread(target=干) for _ in range(线)]
    起时 = time.time()
    for t in 线程们:
        t.start()
    for t in 线程们:
        t.join()

    缺点 = [(i, 段们[i]) for i in range(len(段们))
            if not os.path.isfile(os.path.join(临时, "%05d.part" % i))
            or os.path.getsize(os.path.join(临时, "%05d.part" % i)) != 段们[i][1] - 段们[i][0] + 1]
    if 缺点:
        for 号, _ in 缺点[:5]:
            print("  第 %d 段没下完：%s" % (号, 失败们.get(号, "长度不足")))
        raise SystemExit("有 %d 段不完整，分片留在 %s，重跑本命令会续传" % (len(缺点), 临时))

    with open(目标, "wb") as 出:
        for i in range(len(段们)):
            with open(os.path.join(临时, "%05d.part" % i), "rb") as 源:
                shutil.copyfileobj(源, 出, 1024 * 1024)

    应 = 校验(目标)
    实 = os.path.getsize(目标)
    秒 = max(1, time.time() - 起时)
    if 实 != 应:
        raise SystemExit("长度不符：实际 %d，头部算出 %d；分片留在 %s" % (实, 应, 临时))
    print("落盘 %.2f GB，用时 %.0f 秒，均速 %.0f KB/s，头部校验通过"
          % (实 / 1073741824.0, 秒, 实 / 1024.0 / 秒))
    shutil.rmtree(临时, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(主())
