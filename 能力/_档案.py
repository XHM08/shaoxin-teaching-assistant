
import json
import os
import threading
import time

from 地基 import 落盘, 配置

档案锁 = threading.RLock()

保留设备名 = ({"CON", "PRN", "AUX", "NUL", "CLOCK$"}
            | {"COM%d" % 号 for 号 in range(1, 10)}
            | {"LPT%d" % 号 for 号 in range(1, 10)})

名册文件名 = "名册.json"
记录文件名 = "记录.jsonl"
对照表目录名 = "对照表"
对照表文件名 = "姓名对照表.json"

保留目录 = {对照表目录名}

阻断说明 = (
    "本模块涉及学生数据。\n"
    "《学生数据处理约定》要求：采集任何学生数据，都需先取得监护人签署的《家长知情同意书》。\n"
    "目前同意书尚未签署，因此不能注册学生、不能记录问答、也不展示任何学生数据。\n"
    "同意书签署后，把 配置.json 里的 合规.同意书已签 改为 true 即开放。"
)


def 同意书已签():
    return bool(配置.读取().get("合规", {}).get("同意书已签", False))


def 要求已签():
    if not 同意书已签():
        raise ValueError(阻断说明)


def 数据目录():
    return 配置.取目录("学生数据")


def 名册路径():
    return os.path.join(数据目录(), 名册文件名)


def 学生目录(编号):
    return os.path.join(数据目录(), 编号)


def 记录路径(编号):
    return os.path.join(学生目录(编号), 记录文件名)


def 对照表目录():
    return os.path.join(数据目录(), 对照表目录名)


def 对照表路径():
    return os.path.join(对照表目录(), 对照表文件名)


def 原子写(路径, 文本):
    落盘.原子写文本(路径, 文本)


def 读JSON(路径, 空值, 名字, 期望类型):
    if not os.path.isfile(路径):
        return 空值
    with open(路径, "r", encoding="utf-8") as 文件:
        原文 = 文件.read()
    if not 原文.strip():
        raise ValueError(
            名字 + " 是空的（0 字节）：\n" + 路径
            + "\n软件不会覆盖它 —— 请先人工核对；确实要当「还没登记」就从备份恢复或删掉它。"
        )
    try:
        内容 = json.loads(原文)
    except json.JSONDecodeError as 异常:
        raise ValueError(
            名字 + " 读不出来（多半是上次写盘被打断留下的半截文件）：\n" + 路径
            + "\n软件不会覆盖它 —— 请先人工核对或从备份恢复这个文件。"
        ) from 异常
    if not isinstance(内容, 期望类型):
        raise ValueError(
            名字 + " 的内容不是预期的形状（期望 " + 期望类型.__name__ + "）：\n" + 路径
            + "\n软件不敢往下写，怕把别的条目冲掉。"
        )
    return 内容


def 校验编号(编号):
    编号 = str(编号 or "").strip().upper()
    if not 编号:
        raise ValueError("学生编号不能为空。")
    if any(字符 in 编号 for 字符 in ("/", "\\", ":", "*", "?", '"', "<", ">", "|", ".", " ")):
        raise ValueError("学生编号不能带空格或这些符号 / \\ : * ? \" < > | . ：" + repr(编号))
    if len(编号) > 12:
        raise ValueError("学生编号太长了（最多 12 个字符）：" + 编号)
    if 编号 in 保留目录:
        raise ValueError("这个编号是系统占用的目录名，换一个：" + 编号)
    if 编号 in 保留设备名:
        raise ValueError("这个编号是 Windows 的保留设备名，建不出文件夹，换一个：" + 编号)
    return 编号


def 读名册():
    return 读JSON(名册路径(), [], 名册文件名, list)


def 写名册(名册):
    原子写(名册路径(), json.dumps(名册, ensure_ascii=False, indent=2))


def 已注册(编号):
    return any(一条.get("编号") == 编号 for 一条 in 读名册())


def 读对照表():
    return 读JSON(对照表路径(), {}, 对照表文件名, dict)


def 写对照表(表):
    原子写(对照表路径(), json.dumps(表, ensure_ascii=False, indent=2))


def 学生信息(编号):
    return dict(读对照表().get(校验编号(编号), {}))


def 姓名字样(编号):
    信息 = 学生信息(编号)
    return [值.strip() for 值 in (信息.get("姓名", ""), 信息.get("学号", ""))
            if isinstance(值, str) and 值.strip()]


def 注册(编号, 姓名="", 学号="", 年级="", 班级="", 备注="", 家长同意书="未签回"):
    要求已签()
    编号 = 校验编号(编号)
    if not str(姓名 or "").strip():
        raise ValueError("姓名不能为空。")
    with 档案锁:
        if 已注册(编号):
            raise ValueError("这个编号已经注册过了：" + 编号)

        名册 = 读名册()
        名册.append({"编号": 编号, "注册时间": time.strftime("%Y-%m-%d %H:%M:%S")})
        os.makedirs(数据目录(), exist_ok=True)
        写名册(名册)
        os.makedirs(学生目录(编号), exist_ok=True)
        记资料(编号, 姓名, 学号, 年级, 班级, 备注, 家长同意书)
    return 编号


def 记资料(编号, 姓名, 学号="", 年级="", 班级="", 备注="", 家长同意书=""):
    要求已签()
    编号 = 校验编号(编号)
    if not 已注册(编号):
        raise ValueError("这个编号还没注册：" + 编号 + "，先注册再填资料。")
    if not str(姓名 or "").strip():
        raise ValueError("姓名不能为空 —— 对照表就靠它认人，不许用空值覆盖。")

    with 档案锁:
        旧 = 学生信息(编号)
        原名 = 旧.get("姓名", "")

        def 新或旧(字段, 新值):
            新值 = str(新值 or "").strip()
            return 新值 if 新值 else str(旧.get(字段, "") or "").strip()

        对照表 = 读对照表()
        对照表[编号] = {
            "姓名": str(姓名).strip(),
            "学号": 新或旧("学号", 学号),
            "年级": 新或旧("年级", 年级),
            "班级": 新或旧("班级", 班级),
            "备注": 新或旧("备注", 备注),
            "家长同意书": 新或旧("家长同意书", 家长同意书),
            "录入时间": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        写对照表(对照表)
    return 原名


def 记一条(编号, 内容):
    要求已签()
    编号 = 校验编号(编号)
    原文 = json.dumps(内容, ensure_ascii=False)
    一条 = dict(内容)
    一条.setdefault("时间", time.strftime("%Y-%m-%d %H:%M:%S"))

    with 档案锁:
        撞上的 = [值 for 值 in 姓名字样(编号) if len(值) >= 2 and 值 in 原文]
        if 撞上的:
            raise ValueError(
                "拒绝写入：这条记录里出现了学生的姓名或学号（" + "、".join(撞上的) + "）。\n"
                "《学生数据处理约定》4.1 只收题目文字 / 作答内容 / 错误类型，4.3 不收姓名、学号。"
            )
        os.makedirs(学生目录(编号), exist_ok=True)
        with open(记录路径(编号), "a", encoding="utf-8") as 文件:
            文件.write(json.dumps(一条, ensure_ascii=False) + "\n")
    return 一条


def 读记录(编号, 条数上限=500):
    路径 = 记录路径(校验编号(编号))
    if not os.path.isfile(路径):
        return []
    结果 = []
    with open(路径, "r", encoding="utf-8") as 文件:
        for 行 in 文件:
            行 = 行.strip()
            if not 行:
                continue
            try:
                结果.append(json.loads(行))
            except json.JSONDecodeError:
                continue
    return 结果[-条数上限:]


def 全部学生():
    目录 = 数据目录()
    编号集 = {一条.get("编号") for 一条 in 读名册() if 一条.get("编号")}
    if os.path.isdir(目录):
        for 名字 in os.listdir(目录):
            if 名字 in 保留目录:
                continue
            if os.path.isdir(os.path.join(目录, 名字)):
                编号集.add(名字)
    return sorted(编号集)


def 档案一览():
    对照表 = 读对照表()
    条目 = []
    for 编号 in 全部学生():
        记录 = 读记录(编号)
        信息 = 对照表.get(编号, {})
        条目.append({
            "编号": 编号,
            "姓名": 信息.get("姓名") or "（未填）",
            "学号": 信息.get("学号", ""),
            "年级": 信息.get("年级", ""),
            "班级": 信息.get("班级", ""),
            "家长同意书": 信息.get("家长同意书", ""),
            "记录条数": len(记录),
            "最近一条": (记录[-1].get("时间") or "—") if 记录 else "—",
        })
    return 条目
