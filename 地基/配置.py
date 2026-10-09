
import json
import os
import sys


def 取根目录(冻结=None):
    是冻结 = getattr(sys, "frozen", False) if 冻结 is None else 冻结
    if 是冻结:
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


根目录 = 取根目录()

默认配置 = {
    "服务商配置": "服务商.json",
    "目录": {
        "材料": "材料",
        "参考资料": "参考资料",
        "技能包": "技能包",
        "样例": "样例",
        "密钥": "密钥",
        "提示词": "提示词",
        "日志": "日志",
        "课件输出": "课件输出",
        "学生数据": "学生数据",
        "参考音": "语音/参考音",
        "教师数据": "教师数据",
    },
    "能力开关": {},
    "本地服务": {"主机": "127.0.0.1", "端口": 8765},
    "语音": {"地址": "http://127.0.0.1:9880"},
    "审计": True,
    "合规": {"同意书已签": False},
    "命令": {"需要确认": True, "超时秒数": 60},
}

配置文件 = os.path.join(根目录, "配置.json")


def 读取():
    配置表 = json.loads(json.dumps(默认配置))
    if not os.path.isfile(配置文件):
        return 配置表

    with open(配置文件, "r", encoding="utf-8") as 文件:
        自定义 = json.load(文件)

    配置表["目录"].update(自定义.get("目录", {}))
    for 键 in ("服务商配置", "能力开关", "本地服务", "审计", "合规", "命令"):
        if 键 in 自定义:
            配置表[键] = 自定义[键]
    return 配置表


def 取目录(目录名, 配置表=None):
    配置表 = 配置表 or 读取()
    if 目录名 not in 配置表["目录"]:
        raise KeyError(
            "配置里没有这个目录名：" + 目录名
            + "。可用的有：" + ", ".join(sorted(配置表["目录"]))
        )
    return os.path.join(根目录, 配置表["目录"][目录名])


def 服务商配置路径(配置表=None):
    配置表 = 配置表 or 读取()
    return os.path.join(根目录, 配置表["服务商配置"])


