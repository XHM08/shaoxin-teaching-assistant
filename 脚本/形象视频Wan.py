
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
高噪 = "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
低噪 = "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
文本编码 = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
VAE = "wan_2.1_vae.safetensors"


def 上传(路):
    字节 = io.open(路, "rb").read()
    边 = "----shaoxin"
    体 = [("--" + 边).encode(),
          ('Content-Disposition: form-data; name="image"; filename="%s"' % os.path.basename(路)).encode(),
          b"Content-Type: image/png", b"", 字节, ("--" + 边 + "--").encode(), b""]
    请 = urllib.request.Request(服务 + "/upload/image", b"\r\n".join(体),
                                {"Content-Type": "multipart/form-data; boundary=" + 边})
    return json.load(urllib.request.urlopen(请, timeout=60))["name"]


def 工作流(图名, 提示, 宽, 高, 帧数, 步数, 种子):
    负 = ("色调艳丽，过曝，静态，细节模糊不清，字幕，画面整体发灰，最差质量，低质量，"
         "JPEG 压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，"
         "畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走")
    半 = 步数 // 2
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": 高噪, "weight_dtype": "default"}},
        "2": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "3": {"class_type": "UNETLoader", "inputs": {"unet_name": 低噪, "weight_dtype": "default"}},
        "4": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["3", 0], "shift": 8.0}},
        "5": {"class_type": "CLIPLoader", "inputs": {"clip_name": 文本编码, "type": "wan"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": 提示, "clip": ["5", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": 负, "clip": ["5", 0]}},
        "8": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "9": {"class_type": "LoadImage", "inputs": {"image": 图名}},
        "10": {"class_type": "WanImageToVideo",
               "inputs": {"positive": ["6", 0], "negative": ["7", 0], "vae": ["8", 0],
                          "width": 宽, "height": 高, "length": 帧数, "batch_size": 1,
                          "start_image": ["9", 0]}},
        "11": {"class_type": "KSamplerAdvanced",
               "inputs": {"add_noise": "enable", "noise_seed": 种子, "steps": 步数, "cfg": 1.0,
                          "sampler_name": "euler", "scheduler": "simple",
                          "start_at_step": 0, "end_at_step": 半, "return_with_leftover_noise": "enable",
                          "model": ["2", 0], "positive": ["10", 0], "negative": ["10", 1],
                          "latent_image": ["10", 2]}},
        "12": {"class_type": "KSamplerAdvanced",
               "inputs": {"add_noise": "disable", "noise_seed": 种子, "steps": 步数, "cfg": 1.0,
                          "sampler_name": "euler", "scheduler": "simple",
                          "start_at_step": 半, "end_at_step": 步数, "return_with_leftover_noise": "disable",
                          "model": ["4", 0], "positive": ["10", 0], "negative": ["10", 1],
                          "latent_image": ["11", 0]}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["8", 0]}},
        "14": {"class_type": "SaveImage",
               "inputs": {"filename_prefix": "形象视频/wan帧", "images": ["13", 0]}},
    }


def 提交(节):
    请 = urllib.request.Request(服务 + "/prompt", json.dumps({"prompt": 节}).encode("utf-8"),
                                {"Content-Type": "application/json"})
    回 = json.load(urllib.request.urlopen(请, timeout=60))
    if 回.get("node_errors"):
        raise SystemExit("工作流被拒：" + json.dumps(回["node_errors"], ensure_ascii=False)[:400])
    return 回["prompt_id"]


def 等完成(编号, 超时=5400):
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
                错 = ""
                for 节 in 记.get("status", {}).get("messages", []):
                    if 节[0] == "execution_error":
                        错 = "%s @ %s：%s" % (节[1].get("exception_type"),
                                              节[1].get("node_type"),
                                              str(节[1].get("exception_message"))[:300])
                return {}, 错 or "未知错误"
        time.sleep(10)
    return {}, "超时"


def 取文件(信息):
    查 = ("?filename=" + urllib.parse.quote(信息["filename"])
          + "&subfolder=" + urllib.parse.quote(信息.get("subfolder", ""))
          + "&type=" + 信息.get("type", "output"))
    return urllib.request.urlopen(服务 + "/view" + 查, timeout=180).read()


def 主():
    解 = argparse.ArgumentParser()
    解.add_argument("--提示", required=True)
    解.add_argument("--宽", type=int, default=480)
    解.add_argument("--高", type=int, default=832)
    解.add_argument("--帧数", type=int, default=33)
    解.add_argument("--步数", type=int, default=8)
    解.add_argument("--种子", type=int, default=42)
    解.add_argument("--名", default="动作")
    参 = 解.parse_args()

    目录 = os.path.join(os.environ.get("AVATAR_HOME", ""), "母图")
    母 = os.path.join(目录, "定版-白底-1024.png")
    if not os.path.isfile(母):
        raise SystemExit("找不到母图（先设 AVATAR_HOME）")
    出 = os.path.join(目录, "视频")
    帧目录 = os.path.join(出, 参.名 + "-帧")
    os.makedirs(帧目录, exist_ok=True)

    图名 = 上传(母)
    编号 = 提交(工作流(图名, 参.提示, 参.宽, 参.高, 参.帧数, 参.步数, 参.种子))
    print("已提交 %s（%d×%d，%d 帧，%d 步）" % (编号, 参.宽, 参.高, 参.帧数, 参.步数))

    起 = time.time()
    输出, 错 = 等完成(编号)
    if 错:
        raise SystemExit("生成失败：" + 错)
    图们 = []
    for 节 in 输出.values():
        图们 += 节.get("images", [])
    if not 图们:
        raise SystemExit("没有图像输出")
    图们.sort(key=lambda 信: 信["filename"])
    for i, 信 in enumerate(图们):
        io.open(os.path.join(帧目录, "帧%03d.png" % i), "wb").write(取文件(信))
    print("落盘 %d 帧 → %s（耗时 %.0f 秒）" % (len(图们), 帧目录, time.time() - 起))

    if shutil.which("ffmpeg"):
        命 = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", "16",
              "-i", os.path.join(帧目录, "帧%03d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
              os.path.join(出, 参.名 + ".mp4")]
        子 = subprocess.run(命, capture_output=True)
        if 子.returncode == 0:
            print("预览视频：" + os.path.join(出, 参.名 + ".mp4"))
    return 0


if __name__ == "__main__":
    sys.exit(主())
