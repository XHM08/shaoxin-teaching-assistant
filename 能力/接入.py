import json
import os

from 地基 import 落盘, 注册表

根目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
清单路径 = os.path.join(根目录, "接入可选.json")
MCP路径 = os.path.join(根目录, "MCP服务器.json")


def 读清单():
    if not os.path.isfile(清单路径):
        return []
    with open(清单路径, encoding="utf-8") as 文件:
        return (json.load(文件).get("可选项") or [])


def 读MCP():
    if not os.path.isfile(MCP路径):
        return {"启用": False, "服务器们": []}
    try:
        with open(MCP路径, encoding="utf-8") as 文件:
            表 = json.load(文件)
    except ValueError:
        raise ValueError("MCP服务器.json 读不动（JSON 坏了）。先手工看一眼，别在这上面接着写。")
    if not isinstance(表, dict):
        raise ValueError("MCP服务器.json 顶层应当是个对象，实际是 " + type(表).__name__)
    表.setdefault("启用", False)
    表.setdefault("服务器们", [])
    return 表


def 写MCP(表):
    落盘.带时间备份(MCP路径)
    落盘.原子写文本(MCP路径, json.dumps(表, ensure_ascii=False, indent=2) + "\n")


def 处理清单():
    可选项 = 读清单()
    MCP = 读MCP()
    现装 = [一.get("名字") for 一 in (MCP.get("服务器们") or []) if isinstance(一, dict)]
    for 一 in 可选项:
        一["已装上"] = 一.get("名字") in 现装
    能装 = [一.get("名字") for 一 in 可选项 if 一.get("能装上")]
    提示 = "现在接了 %d 个；能装的有 %d 家：%s。" % (len(现装), len(能装), "、".join(能装))
    if not MCP.get("启用"):
        提示 += "（MCP服务器.json 里 启用=false：装上时会一并打开。）"
    return {
        "提示": 提示,
        "正文": ("这一页只列**核过来源**的接入，命令与出处都写在 接入可选.json 里。\n"
               "本机这套（地基/MCP.py）只支持 stdio 形态（命令 + 参数）；远程 HTTP + OAuth 的接不了，"
               "所以那几家标灰写明原因，不给按钮。\n"
               "装上之后要在 MCP服务器.json 里那条的 env 里把 token 填上 —— "
               "空着的话服务器起得来，但一调工具就会报没凭据。"),
        "接入清单": 可选项,
        "MCP启用": bool(MCP.get("启用")),
        "已装": 现装,
    }


def 处理装(接入名=None, 动作="装上", 确认="否"):
    名字 = str(接入名 or "").strip()
    动作 = str(动作 or "装上").strip()
    确认 = str(确认 or "").strip()
    可选项 = {一.get("名字"): 一 for 一 in 读清单()}
    if 名字 not in 可选项:
        raise ValueError("「接入名」要写清单里的名字。现在有：" + "、".join(可选项))
    一 = 可选项[名字]
    if 动作 not in ("装上", "卸下"):
        raise ValueError("「动作」只能写 装上 或 卸下，收到的是：" + 动作)

    if 确认 != "是":

        要做 = ("把它写进 MCP服务器.json 的 服务器们（并把 启用 打开）"
              if 动作 == "装上" else "把它从 MCP服务器.json 的 服务器们 里删掉")
        return {"提示": "这一步会改 MCP服务器.json，先跟你确认一下。", "需要确认": True,
                "接入": 一, "正文": ("要%s的是「%s」（形态：%s）。\n用处：%s\n前置：%s\n会做：%s\n"
                                 "出处：%s\n确认请把「确认」填成 是。"
                                 % (动作, 名字, 一.get("形态"), 一.get("用处") or "（没写）",
                                   一.get("前置") or "（没写）", 要做, 一.get("出处")))}

    if 动作 == "装上" and not 一.get("能装上"):

        raise ValueError("这家现在接不了：" + str(一.get("状态说明") or "没核到可用入口"))

    MCP = 读MCP()
    服务器们 = [s for s in (MCP.get("服务器们") or []) if isinstance(s, dict)]
    在不在 = any(s.get("名字") == 名字 for s in 服务器们)

    if 动作 == "卸下":
        if not 在不在:
            return {"提示": "「%s」本来就没装上，什么也没改。" % 名字, "接入": 一}
        服务器们 = [s for s in 服务器们 if s.get("名字") != 名字]
        MCP["服务器们"] = 服务器们
        写MCP(MCP)
        剩 = "还剩 %d 个。" % len(服务器们) if 服务器们 else "现在一个都没接。"
        return {"提示": "已卸下「%s」。" % 名字 + 剩, "接入": 一}

    if 在不在:
        return {"提示": "「%s」已经装上了，什么也没改。" % 名字, "接入": 一}
    服务器们.append({
        "名字": 名字, "命令": 一["命令"], "参数": list(一.get("参数") or []),
        "环境": dict(一.get("环境") or {}), "超时": 60,
    })
    MCP["服务器们"] = 服务器们
    MCP["启用"] = True
    写MCP(MCP)
    要填 = 一.get("要填") or []
    填 = ("记得去 MCP服务器.json 那条的 env 里把 %s 填上。" % "、".join(要填)) if 要填 else ""
    return {"提示": "已装上「%s」。%s" % (名字, 填), "接入": 一,
            "正文": "下次用工具时（或重启一次邵新）才会去起这个服务器。起不来的话，"
                  "看 电脑服务 页里的记录，或在对话里问「有哪些外部工具」。"}


注册表.登记(
    代号="可选接入",
    标题="可选接入",
    说明="列出「装了就能用」的外部服务（MCP）与现在接了哪些；只有 stdio 形态的能装",
    参数=[],
    处理函数=处理清单,
)

注册表.登记(
    代号="装接入",
    标题="装接入",
    说明="装上或卸下一个外部服务（MCP）；必须先传「确认=是」才真改 MCP服务器.json",
    参数=[
        {"代号": "接入名", "标签": "接入名", "类型": "text", "必填": True,
         "可选项": [一.get("名字") for 一 in 读清单()]},
        {"代号": "动作", "标签": "装上还是卸下", "类型": "text", "必填": False,
         "可选项": ["装上", "卸下"]},
        {"代号": "确认", "标签": "确认（是 / 否）", "类型": "text", "必填": False,
         "可选项": ["否", "是"]},
    ],
    处理函数=处理装,
)
