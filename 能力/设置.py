
import json
import os

from 地基 import 配置, 大模型, 注册表


def 密钥状态(服务商条目):
    环境变量名 = str(服务商条目.get("key_env", "")).strip()
    if not 环境变量名:
        return "未设置"
    if os.environ.get(环境变量名, "").strip():
        return "已配置（环境变量）"
    if 大模型.读密钥文件(环境变量名):
        return "已配置（本地文件）"
    return "未配置"


def 处理列表():
    配置表 = 大模型.读配置()
    服务商表 = 配置表.get("providers", {})
    当前 = 配置表.get("default", "")
    条目 = []
    for 名字 in sorted(服务商表):
        服务商条目 = 服务商表[名字]
        条目.append({
            "代号": 名字,
            "当前": "是" if 名字 == 当前 else "",
            "模型": 服务商条目.get("model", ""),
            "接口地址": 服务商条目.get("base_url", ""),
            "密钥": 密钥状态(服务商条目),
        })
    return {
        "提示": "当前使用：" + (当前 or "未指定") + "。密钥只显示状态，不显示内容。",
        "条目": 条目,
        "正文": "",
    }


def 读或初始化():
    路径 = 配置.服务商配置路径()
    if os.path.isfile(路径):
        with open(路径, "r", encoding="utf-8") as 文件:
            return 路径, json.load(文件)

    示例 = os.path.join(配置.根目录, "服务商.示例.json")
    if not os.path.isfile(示例):
        raise ValueError("既没有 服务商.json 也没有 服务商.示例.json，无法初始化。")
    with open(示例, "r", encoding="utf-8") as 文件:
        return 路径, json.load(文件)


def 处理保存(服务商, 模型="", 接口地址="", 密钥变量名="", 密钥="", 设为当前="是"):
    服务商 = str(服务商).strip()
    if not 服务商:
        raise ValueError("请先选一个服务商。")

    路径, 配置表 = 读或初始化()

    服务商表 = 配置表.setdefault("providers", {})
    if 服务商 not in 服务商表:
        raise ValueError("配置里没有这个服务商：" + 服务商)
    条目 = 服务商表[服务商]

    for 字段, 值 in (("model", 模型), ("base_url", 接口地址), ("key_env", 密钥变量名)):
        值 = str(值).strip()
        if not 值:
            continue
        if 字段 == "key_env":
            大模型.查环境变量名(值)
        条目[字段] = 值

    写入的变量名 = ""
    if str(密钥).strip():
        环境变量名 = str(条目.get("key_env", "")).strip()
        if not 环境变量名:
            raise ValueError("要保存密钥，得先填「密钥环境变量名」。")
        大模型.查环境变量名(环境变量名)
        os.makedirs(配置.取目录("密钥"), exist_ok=True)
        with open(os.path.join(配置.取目录("密钥"), 环境变量名 + ".txt"),
                  "w", encoding="utf-8") as 文件:
            文件.write(str(密钥).strip() + "\n")
        写入的变量名 = 环境变量名

    if str(设为当前).strip() in ("是", "true", "True", "1"):
        配置表["default"] = 服务商

    with open(路径, "w", encoding="utf-8") as 文件:
        json.dump(配置表, 文件, ensure_ascii=False, indent=2)

    提示 = "已保存：" + 服务商
    if 写入的变量名:
        提示 += "；密钥写入 密钥/" + 写入的变量名 + ".txt"
    return {"提示": 提示, "正文": "", "条目": []}


注册表.登记(
    代号="模型配置",
    标题="模型配置",
    说明="查看与修改大模型服务商（改了立即生效，不用重启）",
    参数=[],
    处理函数=处理列表,
)

注册表.登记(
    代号="保存模型配置",
    标题="保存模型配置",
    说明="写入某家服务商的模型、接口地址、密钥，并可设为当前使用",
    参数=[
        {"代号": "服务商", "标签": "服务商", "类型": "text", "必填": True,
         "可选项来源": "providers"},
        {"代号": "模型", "标签": "模型名", "类型": "text", "必填": False},
        {"代号": "接口地址", "标签": "接口地址", "类型": "text", "必填": False},
        {"代号": "密钥变量名", "标签": "密钥环境变量名", "类型": "text", "必填": False},
        {"代号": "密钥", "标签": "密钥（留空则不改）", "类型": "password", "必填": False},
        {"代号": "设为当前", "标签": "设为当前使用", "类型": "text", "必填": False,
         "可选项": ["是", "否"]},
    ],
    处理函数=处理保存,
)
