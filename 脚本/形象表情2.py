
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

眼框 = (168, 144, 266, 176)
嘴框 = (198, 184, 238, 206)
眉框 = (170, 136, 264, 150)
臂框 = (266, 300, 412, 592)

表 = {
    "闭眼": ("the same girl, eyes fully closed, eyelashes visible", 0.95, [眼框]),
    "半闭眼": ("the same girl, eyes half closed, relaxed eyelids", 0.92, [眼框]),
    "说话1": ("the same girl, mouth slightly open, speaking", 0.70, [嘴框]),
    "说话2": ("the same girl, mouth open, speaking clearly", 0.85, [嘴框]),
    "说话3": ("the same girl, mouth wide open, talking loudly", 0.95, [嘴框]),
    "微笑": ("the same girl, gentle closed mouth smile", 0.92, [嘴框]),
    "开心": ("the same girl, big happy open smile, eyes curved", 0.92, [眼框, 嘴框]),
    "生气": ("the same girl, angry, eyebrows lowered inward, mouth pressed", 0.90, [眉框, 嘴框]),
    "难过": ("the same girl, sad, inner eyebrows raised, mouth corners down", 0.90, [眉框, 嘴框]),
    "惊讶": ("the same girl, surprised, eyes wide, small round open mouth", 0.92, [眼框, 嘴框]),
    "思考": ("the same girl, thinking, eyes looking up to one side", 0.85, [眼框]),
    "挥手": ("the same girl raising her left arm to wave hello, hand up beside her head, "
             "elbow bent naturally, sleeve follows the arm", 0.95, [臂框]),
    "挥手2": ("the same girl waving hello, left arm raised with the hand tilted outward to one side, "
              "palm open, elbow bent", 0.95, [(272, 250, 396, 500)]),
    "举手": ("the same girl raising her left hand straight up high above her head, "
             "arm fully extended, palm open", 0.95, [臂框]),
    "指向": ("the same girl pointing to her right with her left hand, arm extended sideways, "
             "index finger out", 0.95, [臂框]),
    "开心闭眼": ("the same girl, big happy open smile, eyes closed in happy upward arcs", 0.92, [眼框, 嘴框]),
    "开心半闭": ("the same girl, big happy open smile, eyes half closed", 0.90, [眼框, 嘴框]),
}
负向 = ("multiple faces, extra eyes, distorted face, blurry, lowres, text, watermark, "
       "different person, changed hair, changed clothes, changed background")


def 载模块(名, 路):
    规格 = importlib.util.spec_from_file_location(名, 路)
    模 = importlib.util.module_from_spec(规格)
    规格.loader.exec_module(模)
    return 模


def 上传(字节, 名):
    边 = "----shaoxin"
    体 = [("--" + 边).encode(),
          ('Content-Disposition: form-data; name="image"; filename="%s"' % 名).encode(),
          b"Content-Type: image/png", b"", 字节, ("--" + 边 + "--").encode(), b""]
    请 = urllib.request.Request(服务 + "/upload/image", b"\r\n".join(体),
                                {"Content-Type": "multipart/form-data; boundary=" + 边})
    return json.load(urllib.request.urlopen(请, timeout=30))["name"]


def 提交(节):
    请 = urllib.request.Request(服务 + "/prompt",
                                json.dumps({"prompt": 节}).encode("utf-8"),
                                {"Content-Type": "application/json"})
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


def 工作流(底名, 蒙名, 词, 降噪, 前缀, 种子=20261103):
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": 底名}},
        "2": {"class_type": "LoadImage", "inputs": {"image": 蒙名}},
        "3": {"class_type": "ImageToMask", "inputs": {"image": ["2", 0], "channel": "red"}},
        "4": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"}},
        "5": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "stable_diffusion"}},
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": 词, "clip": ["5", 0]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": 负向, "clip": ["5", 0]}},
        "9": {"class_type": "VAEEncodeForInpaint",
              "inputs": {"pixels": ["1", 0], "vae": ["6", 0], "mask": ["3", 0], "grow_mask_by": 4}},
        "10": {"class_type": "KSampler",
               "inputs": {"seed": 种子, "steps": 10, "cfg": 1.0,
                          "sampler_name": "euler", "scheduler": "simple", "denoise": 降噪,
                          "model": ["4", 0], "positive": ["7", 0], "negative": ["8", 0],
                          "latent_image": ["9", 0]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["6", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"filename_prefix": 前缀, "images": ["11", 0]}},
    }


def 框并(框们):
    左 = min(b[0] for b in 框们)
    上 = min(b[1] for b in 框们)
    右 = max(b[2] for b in 框们)
    下 = max(b[3] for b in 框们)
    return 左, 上, 右, 下


def 锁框外(原图, 生成图, 框们, 羽化=2):
    合 = 原图.copy()
    蒙 = Image.new("L", 原图.size, 0)
    画 = ImageDraw.Draw(蒙)
    for b in 框们:
        画.rectangle(b, fill=255)
    if 羽化:
        蒙 = 蒙.filter(ImageFilter.GaussianBlur(羽化))
    合.paste(生成图, (0, 0), 蒙)

    import numpy as np
    a = np.asarray(原图.convert("RGB")).astype(int)
    b2 = np.asarray(合.convert("RGB")).astype(int)
    差 = np.abs(a - b2).sum(axis=2)
    import numpy as np2
    外 = np.ones(差.shape, bool)
    for x0, y0, x1, y1 in 框们:
        外[max(0, y0 - 8):y1 + 8, max(0, x0 - 8):x1 + 8] = False
    框内 = ~外
    return 合, float(差[框内].mean()), int(差[外].max()), int((差[外] > 0).sum())


def 主():
    解 = argparse.ArgumentParser()
    解.add_argument("--只", default="")
    解.add_argument("--母图", default="")
    解.add_argument("--降噪", type=float, default=0.0)
    解.add_argument("--种子", type=int, default=20261103)
    解.add_argument("--另存", default="", help="另存成别的名字，方便同姿态多跑几个种子挑")
    参 = 解.parse_args()

    母图 = 参.母图 or os.path.join(os.environ.get("AVATAR_HOME", ""), "母图", "定版-白底-1024.png")
    if not os.path.isfile(母图):
        raise SystemExit("找不到母图：" + (母图 or "（没设 AVATAR_HOME）"))
    出目录 = os.path.join(os.path.dirname(母图), "部件")
    os.makedirs(出目录, exist_ok=True)

    定版模 = 载模块("形象定版_被用", os.path.join(根, "脚本", "形象定版.py"))
    原 = Image.open(母图).convert("RGB")

    with io.BytesIO() as 缓:
        原.save(缓, format="PNG")
        底名 = 上传(缓.getvalue(), "母图.png")

    要跑 = [参.只] if 参.只 else list(表)
    好, 坏 = [], []
    for 名 in 要跑:
        if 名 not in 表:
            raise SystemExit("没有这个表情：" + 名)
        词, 降, 框们 = 表[名]
        if 参.降噪:
            降 = 参.降噪
        蒙图 = Image.new("L", 原.size, 0)
        画 = ImageDraw.Draw(蒙图)
        for b in 框们:
            画.rectangle(b, fill=255)
        with io.BytesIO() as 缓:
            蒙图.save(缓, format="PNG")
            蒙名 = 上传(缓.getvalue(), "部件蒙版.png")

        编号 = 提交(工作流(底名, 蒙名, 词, 降, "part_" + 名, 参.种子))
        图们, 错 = 等完成(编号)
        if 错 or not 图们:
            坏.append("%s：%s" % (名, 错 or "没有输出"))
            print("  ✗ %s（%s）" % (名, 错 or "没有输出"))
            continue
        数据 = 取图(图们[0])
        临时 = os.path.join(出目录, "_raw_%s.png" % 名)
        io.open(临时, "wb").write(数据)
        生成 = Image.open(临时).convert("RGB")
        if 生成.size != 原.size:
            os.remove(临时)
            坏.append("%s：尺寸 %s 与母图 %s 不一致" % (名, 生成.size, 原.size))
            continue

        合, 框内差, 框外最大, 框外像素 = 锁框外(原, 生成, 框们)
        os.remove(临时)
        存名 = 参.另存 or 名
        路 = os.path.join(出目录, 存名 + ".png")
        合.save(路)
        定版模.透明化(合, [253.5, 253.7, 253.2]).save(os.path.join(出目录, 存名 + "-透明.png"))

        合格 = 框外最大 == 0
        print("  %s %-4s 框内差 %5.0f  框外最大差 %d  框外被改像素 %d"
              % ("✓" if 合格 else "✗", 名, 框内差, 框外最大, 框外像素))
        好.append(名) if 合格 else 坏.append("%s：框外被改 %d 像素" % (名, 框外像素))

    print("成 %d，败 %d" % (len(好), len(坏)))
    if 坏:
        print("失败：" + "；".join(坏))
    return 0 if 好 and not 坏 else 1


if __name__ == "__main__":
    sys.exit(主())
