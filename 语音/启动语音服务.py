
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 地基 import 语音

必须的 = [
    ("GPT_SoVITS/pretrained_models/s2G488k.pth", "预训练权重"),
    ("GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s2G2333k.pth", "v2 的生成权重"),
    ("GPT_SoVITS/text/G2PWModel/g2pW.onnx", "中文前端（G2PW）"),
]


def main():
    try:
        目录 = 语音.读程序目录()
    except ValueError as 异常:
        print("[语音] " + str(异常))
        return 2

    PY = os.path.join(目录, ".venv", "Scripts", "python.exe")
    if not os.path.isfile(PY):
        print("[语音] 在下面这个位置没找到 GPT-SoVITS 的环境：")
        print("       " + 目录)
        print("       期望看到：" + PY)
        print()
        print("       刚搬到别处？改 语音/程序目录.txt（只改那一行），再双击本文件。")
        print("       还没装？见 语音/说明.md（模型约 5 GB，只需装一次）。")
        print("       想确认现在这套还能不能用：在 样本 目录跑")
        print("           python 脚本/检查_语音安装.py")
        return 2

    缺的 = [说明 + "（" + 相对 + "）" for 相对, 说明 in 必须的
           if not os.path.isfile(os.path.join(目录, 相对.replace("/", os.sep)))]
    if 缺的:
        print("[语音] 模型好像还没放齐，少这些：")
        for 一条 in 缺的:
            print("       " + 一条)
        print("       怎么放见 语音/说明.md；也可以跑 python 脚本/检查_语音安装.py 看缺什么。")
        return 2

    端口 = 语音.读端口()
    print("[语音] 正在启动，端口 %d ……" % 端口)
    print("[语音] 起来之后**这个黑窗口别关**（关了服务就停）。要停止就按 Ctrl+C。")
    print("[语音] 它和邵新是两个进程：不配音的时候不需要开它。")
    try:
        码 = subprocess.call([PY, "api_v2.py", "-a", "127.0.0.1", "-p", str(端口)], cwd=目录)
    except KeyboardInterrupt:
        print("\n[语音] 已停止。")
        return 0
    print()
    print("[语音] 服务已退出（退出码 %d）。" % 码)
    return 码


if __name__ == "__main__":
    sys.exit(main())
