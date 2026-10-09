
import json
import os
import sys

默认 = 8765


def main():
    for 候选 in (os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "配置.json"),
                "配置.json"):
        try:
            with open(候选, encoding="utf-8") as 文件:
                配置 = json.load(文件)
            端口 = 配置.get("本地服务", {}).get("端口")
            print(int(端口) if 端口 else 默认)
            return 0
        except Exception:
            continue
    print(默认)
    return 0


if __name__ == "__main__":
    sys.exit(main())
