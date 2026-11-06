
import argparse
import importlib.util
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFilter

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
服务 = "http://127.0.0.1:8188"
默认框 = (60, 140, 380, 280)

表情表 = {
    "微笑": ("the same girl, gentle closed mouth smile, relaxed eyebrows", 0.75),
    "开心": ("the same girl, happy laughing, big open smile, eyes curved like crescents", 0.90),
    "生气": ("the same girl, angry, eyebrows lowered and inward, mouth pressed tight", 0.88),
    "难过": ("the same girl, sad, eyebrows raised at the inner ends, mouth corners down", 0.85),
    "惊讶": ("the same girl, surprised, eyes wide open, small round open mouth", 0.90),
    "思考": ("the same girl, thinking, eyes looking up to one side, one eyebrow slightly raised", 0.80),
    "说话1": ("the same girl, mouth closed, neutral, about to speak", 0.70),
    "说话2": ("the same girl, mouth slightly open, speaking", 0.80),
    "说话3": ("the same girl, mouth wide open, talking loudly", 0.88),
    "闭眼": ("the same girl, eyes fully closed, calm neutral mouth", 0.90),
    "半闭眼": ("the same girl, eyes half closed, sleepy relaxed eyelids", 0.85),
}
负向 = ("multiple faces, extra eyes, distorted face, blurry, lowres, text, watermark, "
       "different person, changed hair, changed clothes")


def 载模块(名, 路):
    规格 = importlib.util.spec_from_file_location(名, 路)
    模 = importlib.util.module_from_spec(规格)
    规格.loader.exec_module(模)
    return 模


def 上传(字节, 名):
    边 = "----shaoxin"
    体 = []
    体.append(("--" + 边).encode())
    体.append(('Content-Disposition: form-data; name="image"; filename="%s"' % 名).encode())
    体.append(b"Content-Type: image/png")
    体.append(b"")
    体.append(字节)
    体.append(("--" + 边 + "--").encode())
    体.append(b"")
    数据 = b"\r\n".join(体)
    请 = urllib.request.Request(服务 + "/upload/image", 数据,
                                {"Content-Type": "multipart/form-data; boundary=" + 边})
    回 = json.load(urllib.request.urlopen(请, timeout=30))
    return 回["name"]


def 提交(节):
    体 = json.dumps({"prompt": 节}).encode("utf-8")
    请 = urllib.request.Request(服务 + "/prompt", 体, {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(请, timeout=30))["prompt_id"]


def 等完成(编号, 超时=420):
    起 = time.time()
    while time.time() - 起 < 超时:
        try:
            史 = json.load(urllib.request.urlopen(服务 + "/history/" + 编号, timeout=15))
        except Exception:
            史 = {}
        if 编号 in 史:
            记 = 史[编号]
            if 记.get("status", {}).get("completed"):
                图们 = []
                for 出 in 记.get("outputs", {}).values():
                    图们 += 出.get("images", [])
                return 图们, None
            if 记.get("status", {}).get("status_str") == "error":
                return [], str(记.get("status", {}).get("messages", ""))[:160]
        time.sleep(3)
    return [], "超时"


def 取图(信息):
    查 = ("?filename=" + urllib.parse.quote(信息["filename"])
          + "&subfolder=" + urllib.parse.quote(信息.get("subfolder", ""))
          + "&type=" + 信息.get("type", "output"))
    return urllib.request.urlopen(服务 + "/view" + 查, timeout=60).read()


def 工作流(底名, 蒙名, 提示词, 降噪, 前缀):
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": 底名}},
        "2": {"class_type": "LoadImage", "inputs": {"image": 蒙名}},
        "3": {"class_type": "ImageToMask", "inputs": {"image": ["2", 0], "channel": "red"}},
        "4": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"}},
        "5": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "stable_diffusion"}},
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": 提示词, "clip": ["5", 0]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": 负向, "clip": ["5", 0]}},
        "9": {"class_type": "VAEEncodeForInpaint",
              "inputs": {"pixels": ["1", 0], "vae": ["6", 0], "mask": ["3", 0], "grow_mask_by": 6}},
        "10": {"class_type": "KSampler",
               "inputs": {"seed": 20261103, "steps": 10, "cfg": 1.0,
                          "sampler_name": "euler", "scheduler": "simple",
                          "denoise": 降噪, "model": ["4", 0], "positive": ["7", 0],
                          "negative": ["8", 0], "latent_image": ["9", 0]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["6", 0]}},
        "12": {"class_type": "SaveImage",
               "inputs": {"filename_prefix": 前缀, "images": ["11", 0]}},
    }


def 主():
    解 = argparse.ArgumentParser()
    解.add_argument("--母图", default="")
    解.add_argument("--框", default="")
    解.add_argument("--只", default="")
    解.add_argument("--降噪", type=float, default=0.0)
    参 = 解.parse_args()

    母图 = 参.母图 or os.path.join(os.environ.get("AVATAR_HOME", ""), "母图", "定版-白底-1024.png")
    if not os.path.isfile(母图):
        raise SystemExit("找不到母图：" + (母图 or "（没设 AVATAR_HOME）"))
    出目录 = os.path.join(os.path.dirname(母图), "表情")
    os.makedirs(出目录, exist_ok=True)

    框 = 默认框
    if 参.框:
        框 = tuple(int(v) for v in 参.框.split(","))
    if len(框) != 4:
        raise SystemExit("--框 要四个整数，例如 60,140,380,280")

    底 = Image.open(母图).convert("RGB")
    蒙 = Image.new("L", 底.size, 0)
    画 = ImageDraw.Draw(蒙)
    画.rectangle(框, fill=255)
    蒙 = 蒙.filter(ImageFilter.GaussianBlur(6))

    with io.BytesIO() as 缓:
        底.save(缓, format="PNG")
        底名 = 上传(缓.getvalue(), "母图.png")
    with io.BytesIO() as 缓:
        蒙.save(缓, format="PNG")
        蒙名 = 上传(缓.getvalue(), "脸蒙版.png")

    定版模 = 载模块("形象定版_被用", os.path.join(根, "脚本", "形象定版.py"))
    要跑 = [参.只] if 参.只 else list(表情表)
    好, 坏 = [], []
    for 名 in 要跑:
        if 名 not in 表情表:
            raise SystemExit("没有这个表情：" + 名)
        词, 降 = 表情表[名]
        if 参.降噪:
            降 = 参.降噪
        编号 = 提交(工作流(底名, 蒙名, 词, 降, "expr_" + 名))
        起 = time.time()
        图们, 错 = 等完成(编号)
        if 错 or not 图们:
            坏.append("%s：%s" % (名, 错 or "没有输出"))
            print("  ✗ %s（%s）" % (名, 错 or "没有输出"))
            continue
        数据 = 取图(图们[0])
        路 = os.path.join(出目录, 名 + ".png")
        io.open(路, "wb").write(数据)
        透 = 定版模.透明化(Image.open(路).convert("RGB"), [253.5, 253.7, 253.2])
        透.save(os.path.join(出目录, 名 + "-透明.png"))
        好.append(路)
        print("  ✓ %s（%.0f 秒）" % (名, time.time() - 起))

    print("成 %d 张，败 %d 张" % (len(好), len(坏)))
    if 坏:
        print("失败：" + "；".join(坏))
    return 0 if 好 else 1


if __name__ == "__main__":
    sys.exit(主())
