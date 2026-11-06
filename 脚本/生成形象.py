
import argparse
import io
import json
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request

服务 = "http://127.0.0.1:8188"
输出根 = os.environ.get("AVATAR_OUT", "")

规格 = {
    "正向": ("anime visual novel character design, one high school girl, 16 to 18 years old, "
           "short shoulder length dark blue hair, large expressive eyes, "
           "white sailor shirt with navy blue collar, blue ribbon tie, navy pleated skirt, "
           "knee high socks, standing full body, front view, arms relaxed at sides, "
           "gentle friendly smile, clean cel shading, crisp lineart, flat colors, "
           "plain white background, character centered, no text"),
    "负向": ("multiple girls, multiple views, text, watermark, logo, signature, cropped, "
           "out of frame, extra limbs, bad hands, blurry, lowres, photo, realistic, 3d render"),
    "宽": 832,
    "高": 1216,
    "步数": 8,
    "cfg": 1.0,
    "采样器": "euler",
    "调度": "simple",
}

模型表 = {
    "newbie": {"装载": "双", "文1": "gemma_3_4b_it_bf16.safetensors",
              "文2": "jina_clip_v2_bf16.safetensors", "类型": "newbie",
              "unet": "NewBie-Image-Exp0.1-bf16.safetensors", "步数": 24, "cfg": 4.0},
    "zimage": {"装载": "单", "文1": "qwen_3_4b.safetensors", "类型": "stable_diffusion",
               "unet": "z_image_turbo_bf16.safetensors", "步数": 8, "cfg": 1.0},
}


def 工作流(型号, 种子, 前缀):
    配 = 模型表[型号]
    节 = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": 配["unet"], "weight_dtype": "default"}},
        "2": ({"class_type": "DualCLIPLoader",
               "inputs": {"clip_name1": 配["文1"], "clip_name2": 配["文2"], "type": 配["类型"]}}
              if 配["装载"] == "双" else
              {"class_type": "CLIPLoader",
               "inputs": {"clip_name": 配["文1"], "type": 配["类型"]}}),
        "3": {"class_type": "CLIPTextEncode",
              "inputs": {"text": 规格["正向"], "clip": ["2", 0]}},
        "4": {"class_type": "CLIPTextEncode",
              "inputs": {"text": 规格["负向"], "clip": ["2", 0]}},
        "5": {"class_type": "EmptySD3LatentImage",
              "inputs": {"width": 规格["宽"], "height": 规格["高"], "batch_size": 1}},
        "6": {"class_type": "KSampler",
              "inputs": {"seed": 种子, "steps": 配["步数"], "cfg": 配["cfg"],
                         "sampler_name": 规格["采样器"], "scheduler": 规格["调度"],
                         "denoise": 1.0, "model": ["1", 0], "positive": ["3", 0],
                         "negative": ["4", 0], "latent_image": ["5", 0]}},
        "7": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["7", 0]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"filename_prefix": 前缀 + "_" + 型号 + "_" + str(种子), "images": ["8", 0]}},
    }
    return 节


def 提交(节):
    体 = json.dumps({"prompt": 节}).encode("utf-8")
    请 = urllib.request.Request(服务 + "/prompt", 体, {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(请, timeout=30))["prompt_id"]


def 等完成(编号, 超时=600):
    起 = time.time()
    while time.time() - 起 < 超时:
        try:
            历史 = json.load(urllib.request.urlopen(服务 + "/history/" + 编号, timeout=15))
        except Exception:
            历史 = {}
        if 编号 in 历史:
            记录 = 历史[编号]
            状态 = 记录.get("status", {})
            if 状态.get("completed"):
                图们 = []
                for 出 in 记录.get("outputs", {}).values():
                    图们 += 出.get("images", [])
                return 图们, None
            if 状态.get("status_str") == "error":
                return [], str(状态.get("messages", ""))[:200]
        time.sleep(4)
    return [], "超时"


def 取图(信息):
    查 = ("?filename=" + urllib.parse.quote(信息["filename"])
          + "&subfolder=" + urllib.parse.quote(信息.get("subfolder", ""))
          + "&type=" + 信息.get("type", "output"))
    return urllib.request.urlopen(服务 + "/view" + 查, timeout=60).read()


def 主():
    解 = argparse.ArgumentParser()
    解.add_argument("--批", default=time.strftime("%Y%m%d-%H%M%S"))
    解.add_argument("--模型", default="两个", choices=("newbie", "zimage", "两个"))
    解.add_argument("--种子", default="20261103,17,23")
    解.add_argument("--正向", default="", help="换掉默认正向提示词")
    解.add_argument("--负向", default="", help="换掉默认负向提示词")
    参 = 解.parse_args()
    if 参.正向:
        规格["正向"] = 参.正向
    if 参.负向:
        规格["负向"] = 参.负向
    if not 输出根:
        raise SystemExit("没设输出目录：先 export AVATAR_OUT=<形象目录>")

    型号们 = ["newbie", "zimage"] if 参.模型 == "两个" else [参.模型]
    种子们 = [int(一) for 一 in 参.种子.split(",") if 一.strip()]
    目录 = os.path.join(输出根, 参.批)
    os.makedirs(目录, exist_ok=True)

    print("批名 %s | 模型 %s | 种子 %s | %d×%d"
          % (参.批, 型号们, 种子们, 规格["宽"], 规格["高"]))
    成, 败 = [], []
    for 型号 in 型号们:
        for 种子 in 种子们:
            前缀 = "avatar_" + 参.批
            编号 = 提交(工作流(型号, 种子, 前缀))
            起 = time.time()
            图们, 错 = 等完成(编号)
            if 错:
                败.append("%s/%s：%s" % (型号, 种子, 错))
                print("  ✗ %s %s（%s）" % (型号, 种子, 错))
                continue
            for 信息 in 图们:
                数据 = 取图(信息)
                名 = "%s_%s_%d.png" % (型号, 种子, int(time.time()) % 1000)
                路 = os.path.join(目录, 名)
                io.open(路, "wb").write(数据)
                成.append(路)
                print("  ✓ %s（%.0f 秒，%d KB）" % (路, time.time() - 起, len(数据) // 1024))

    桌面 = os.path.join(os.path.expanduser("~"), "Desktop", "形象候选-" + 参.批)
    if 成:
        os.makedirs(桌面, exist_ok=True)
        for 路 in 成:
            shutil.copy2(路, 桌面)
        print("成图 %d 张，已拷到 %s" % (len(成), 桌面))
    if 败:
        print("失败 %d 条：%s" % (len(败), "；".join(败)))
    return 0 if 成 else 1


if __name__ == "__main__":
    sys.exit(主())
