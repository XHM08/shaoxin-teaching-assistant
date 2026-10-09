
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 语音

关键文件 = [
    ".venv/Scripts/python.exe",
    "GPT_SoVITS/pretrained_models/s2G488k.pth",
    "GPT_SoVITS/pretrained_models/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt",
    "GPT_SoVITS/pretrained_models/chinese-hubert-base/pytorch_model.bin",
    "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large/pytorch_model.bin",
    "GPT_SoVITS/text/G2PWModel/g2pW.onnx",
]

结果 = []


def 检查(名字, 通过, 说明=""):
    结果.append((名字, bool(通过), 说明))


print("  位置文件：" + 语音.程序目录文件())
try:
    目录 = 语音.读程序目录()
    读错 = ""
except ValueError as 异常:
    目录, 读错 = None, str(异常)
print("  里面写的是：%s" % (目录 or "（读不出来）"))
print()

if 读错:
    检查("能读到 GPT-SoVITS 的位置", False, 读错)
else:
    检查("GPT-SoVITS 目录在", os.path.isdir(目录), 目录)
    条目 = os.listdir(目录) if os.path.isdir(目录) else []
    检查("GPT-SoVITS 目录不是空的", bool(条目), "%d 项" % len(条目))
    缺的 = [名 for 名 in 关键文件 if not os.path.isfile(os.path.join(目录, 名.replace("/", os.sep)))]
    检查("关键文件都在（权重 + 两个 BERT + 中文前端）", not 缺的,
        ("缺：" + "、".join(缺的)) if 缺的 else "%d 项都在" % len(关键文件))

    if 缺的:
        检查("那个 venv 还能导入整条依赖链（搬盘没搬坏）", False, "关键文件不齐，先补齐再说")
    else:
        PY = os.path.join(目录, ".venv", "Scripts", "python.exe")
        探针 = ("import sys, os\n"
              "now = os.getcwd()\n"
              "sys.path += [now, os.path.join(now, 'GPT_SoVITS')]\n"
              "from GPT_SoVITS.TTS_infer_pack.TTS import TTS\n"
              "import torch\n"
              "print('IMPORT-OK', torch.__version__, torch.cuda.is_available())\n")
        try:
            跑 = subprocess.run([PY, "-c", 探针], cwd=目录, capture_output=True,
                              text=True, encoding="utf-8", timeout=300)
            出 = ((跑.stdout or "") + (跑.stderr or "")).strip().splitlines()
            检查("那个 venv 还能导入整条依赖链（搬盘没搬坏）",
                "IMPORT-OK" in (跑.stdout or ""), (出[-1][:100] if 出 else "没输出"))
        except subprocess.TimeoutExpired:
            检查("那个 venv 还能导入整条依赖链", False, "导入超时（300 秒）—— 它可能正在加载模型")
        except Exception as 异常:
            检查("那个 venv 还能导入整条依赖链", False, type(异常).__name__ + "：" + str(异常)[:80])

print()
坏 = 0
for 名字, 过, 说明 in 结果:
    print(("  通过  " if 过 else "  失败  ") + 名字 + ("　→　" + 说明 if 说明 else ""))
    坏 += 0 if 过 else 1

地址 = 语音.取地址()
if 语音.服务在吗():
    print("  提示 语音服务正在跑（%s），配音可以直接用。" % 地址)
else:
    print("  提示 语音服务没在跑（%s）—— 不配音时不用管；要用就双击 语音/启动语音服务.bat。" % 地址)

print("全部 %d 项通过" % len(结果) if not 坏 else "%d 项失败" % 坏)
sys.exit(0 if not 坏 else 1)
