
import os
import sys


def main():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from 地基 import 配置
        print(配置.取端口())
    except Exception as 错:


        print("（读不到端口：%r。检查 地基/配置.py 与 配置.json）" % (错,), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
