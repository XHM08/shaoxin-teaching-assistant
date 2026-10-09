
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 配置, 幻灯片

临时名 = "_自检用课件.pptx"
该返回的类型 = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def 服务活着(端口):
    try:
        urllib.request.urlopen("http://127.0.0.1:%d/" % 端口, timeout=5).read(1)
        return True
    except Exception:
        return False


def main():
    课件目录 = 配置.取目录("课件输出")
    os.makedirs(课件目录, exist_ok=True)
    端口 = 配置.取端口()

    if not 服务活着(端口):
        print("  服务没起（127.0.0.1:%d 连不上）。先启动服务再跑这个检查。" % 端口)
        return 1

    临时课件 = os.path.join(课件目录, 临时名)
    问题 = []
    try:
        幻灯片.写出({"title": "自检",
                     "pages": [{"title": "第一页", "points": ["要点一"], "script": "讲稿"}]},
                    临时课件)
        该有的大小 = os.path.getsize(临时课件)
        地址 = "http://127.0.0.1:%d%s" % (端口, quote("/课件/" + 临时名))
        print("  请求：", 地址)

        with urllib.request.urlopen(地址, timeout=30) as 响应:
            数据 = 响应.read()
            类型 = 响应.headers.get("Content-Type", "")
            处置 = 响应.headers.get("Content-Disposition", "")
            print("  状态码             :", 响应.status)
            print("  Content-Type       :", 类型)
            print("  Content-Disposition:", 处置)
            print("  收到字节           :", len(数据), "（磁盘上", 该有的大小, "）")

        if 类型 != 该返回的类型:
            问题.append("内容类型不对：" + 类型)
        if "attachment" not in 处置:
            问题.append("响应头里没有 attachment")
        if "filename*=UTF-8''" not in 处置:
            问题.append("真名没走 RFC 5987（filename*）")
        if len(数据) != 该有的大小:
            问题.append("收到的字节和磁盘上的不一致")
        if 数据[:2] != b"PK":
            问题.append("下回来的不是 PPTX（头两字节不是 PK，说明发错了文件）")
        try:
            处置.encode("latin-1")
        except UnicodeEncodeError:
            问题.append("Content-Disposition 里有非 latin-1 字符。响应会被写成半截")
    except urllib.error.HTTPError as 异常:
        问题.append("HTTP " + str(异常.code) + "：" + 异常.read().decode("utf-8", "replace")[:120])
    except urllib.error.URLError as 异常:
        问题.append("连不上服务：" + str(异常.reason))
    except Exception as 异常:
        问题.append(type(异常).__name__ + ": " + str(异常) + "  ← 响应很可能被写坏了")
    finally:
        if os.path.isfile(临时课件):
            try:
                os.remove(临时课件)
            except OSError:
                pass

    if 问题:
        print("\n  课件下载有问题：")
        for 一条 in 问题:
            print("    " + 一条)
        return 1
    print("\n  课件下载正常。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
