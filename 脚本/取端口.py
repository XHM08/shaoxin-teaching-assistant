
import os
import sys

默认 = 8765


def main():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from 地基 import 配置
        print(配置.取端口())
    except Exception as 错:
        print("（读不到配置，退回默认端口 %d：%r）" % (默认, 错), file=sys.stderr)
        print(默认)
    return 0


if __name__ == "__main__":
    sys.exit(main())
