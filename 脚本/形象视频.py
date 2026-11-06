
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

服务 = "http://127.0.0.1:8188"
工作流模板 = r"D:\1 谢海铭\xhmnb666\工作\minimax-h3\workflow_minimax_h3_i2v.json"


def 上传(路):
    字节 = io.open(路, "rb").read()
    边 = "----shaoxin"
    体 = [("--" + 边).encode(),
          ('Content-Disposition: form-data; name="image"; filename="%s"' % os.path.basename(路)).encode(),
          b"Content-Type: image/png", b"", 字节, ("--" + 边 + "--").encode(), b""]
    请 = urllib.request.Request(服务 + "/upload/image", b"\r\n".join(体),
                                {"Content-Type": "multipart/form-data; boundary=" + 边})
    return json.load(urllib.request.urlopen(请, timeout=60))["name"]


def 造工作流(图名, 提示, 宽, 高, 帧数, 种子, 步数):
    节 = json.load(io.open(工作流模板, encoding="utf-8"))
    节["6"]["inputs"]["image"] = 图名
    节["7"]["inputs"].update({"prompt": 提示, "width": 宽, "height": 高, "length": 帧数})
    节["9"]["inputs"].update({"seed": 种子, "steps": 步数})
    节["13"]["inputs"]["filename_prefix"] = "形象视频/原片"
    for 号 in ("5", "11", "14"):
        节.pop(号, None)
    return 节


def 提交(节):
    请 = urllib.request.Request(服务 + "/prompt", json.dumps({"prompt": 节}).encode("utf-8"),
                                {"Content-Type": "application/json"})
    回 = json.load(urllib.request.urlopen(请, timeout=60))
    if 回.get("node_errors"):
        raise SystemExit("工作流被拒：" + json.dumps(回["node_errors"], ensure_ascii=False)[:300])
    return 回["prompt_id"]


def 等完成(编号, 超时=3600):
    起 = time.time()
    while time.time() - 起 < 超时:
        try:
            史 = json.load(urllib.request.urlopen(服务 + "/history/" + 编号, timeout=20))
        except Exception:
            史 = {}
        if 编号 in 史:
            记 = 史[编号]
            if 记.get("status", {}).get("completed"):
                return 记.get("outputs", {}), None
            if 记.get("status", {}).get("status_str") == "error":
                return {}, str(记.get("status", {}).get("messages", ""))[:300]
        time.sleep(10)
    return {}, "超时"


def 取文件(信息):
    查 = ("?filename=" + urllib.parse.quote(信息["filename"])
          + "&subfolder=" + urllib.parse.quote(信息.get("subfolder", ""))
          + "&type=" + 信息.get("type", "output"))
    return urllib.request.urlopen(服务 + "/view" + 查, timeout=180).read()


def 抽帧(视频, 出目录, 每几帧, 最长边):
    扇贝 = shutil.which("ffmpeg")
    if not 扇贝:
        raise SystemExit("找不到 ffmpeg")
    图们 = sorted(os.listdir(出目录))
    for 名 in 图们:
        os.remove(os.path.join(出目录, 名))
    命 = [扇贝, "-y", "-hide_banner", "-loglevel", "error", "-i", 视频,
          "-vf", "select='not(mod(n\\,%d))',scale='min(%d,iw)':-2" % (每几帧, 最长边),
          "-vsync", "0", os.path.join(出目录, "帧%03d.png")]
    子 = subprocess.run(命, capture_output=True)
    if 子.returncode != 0:
        raise SystemExit("抽帧失败：" + 子.stderr.decode("utf-8", "replace")[:200])
    return sorted(os.listdir(出目录))


def 主():
    解 = argparse.ArgumentParser()
    解.add_argument("--提示", required=True)
    解.add_argument("--宽", type=int, default=432)
    解.add_argument("--高", type=int, default=1024)
    解.add_argument("--帧数", type=int, default=58)
    解.add_argument("--种子", type=int, default=42)
    解.add_argument("--步数", type=int, default=12)
    解.add_argument("--每帧数", type=int, default=4, help="每隔几帧抽一张")
    解.add_argument("--名", default="动作")
    参 = 解.parse_args()

    目录 = os.path.join(os.environ.get("AVATAR_HOME", ""), "母图")
    母 = os.path.join(目录, "定版-白底-1024.png")
    if not os.path.isfile(母):
        raise SystemExit("找不到母图（先设 AVATAR_HOME）")
    出目录 = os.path.join(目录, "视频")
    帧目录 = os.path.join(出目录, 参.名 + "-帧")
    os.makedirs(帧目录, exist_ok=True)

    图名 = 上传(母)
    print("已上传首帧：", 图名)
    编号 = 提交(造工作流(图名, 参.提示, 参.宽, 参.高, 参.帧数, 参.种子, 参.步数))
    print("已提交：", 编号, "（%d×%d，%d 帧）" % (参.宽, 参.高, 参.帧数))

    起 = time.time()
    出, 错 = 等完成(编号)
    if 错:
        raise SystemExit("生成失败：" + 错)
    视频们 = []
    for 节 in 出.values():
        视频们 += 节.get("videos", []) + 节.get("gifs", [])
    if not 视频们:
        raise SystemExit("没有视频输出：" + json.dumps(出, ensure_ascii=False)[:200])

    视频路 = os.path.join(出目录, 参.名 + ".mp4")
    io.open(视频路, "wb").write(取文件(视频们[0]))
    print("视频落盘：%s（%.0f 秒，%d KB）" % (视频路, time.time() - 起, os.path.getsize(视频路) // 1024))

    帧们 = 抽帧(视频路, 帧目录, 参.每帧数, 参.高)
    print("抽帧 %d 张 → %s" % (len(帧们), 帧目录))
    return 0


if __name__ == "__main__":
    sys.exit(主())
