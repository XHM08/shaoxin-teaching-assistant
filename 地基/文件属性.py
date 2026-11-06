
import os

流名 = "XR"
默认等级 = "C"
合法等级 = ("A", "B", "C", "D")


def _流路(路径):
    return str(路径) + ":" + 流名


def 支持吗(路径=None):
    根 = os.path.abspath(路径 or os.getcwd())
    while not os.path.isdir(根):
        上级 = os.path.dirname(根)
        if 上级 == 根:
            break
        根 = 上级
    试 = os.path.join(根, "_XR能力探测.tmp")
    try:
        with open(试, "w", encoding="utf-8") as 文件:
            文件.write("x")
        with open(_流路(试), "w", encoding="utf-8") as 流:
            流.write("probe")
        回 = ""
        with open(_流路(试), "r", encoding="utf-8") as 流:
            回 = 流.read()
        return 回 == "probe"
    except OSError:
        return False
    finally:
        for 路 in (_流路(试), 试):
            try:
                os.remove(路)
            except OSError:
                pass


def 写XR(路径, 等级=默认等级):
    等级 = str(等级 or 默认等级).strip().upper()
    if 等级 not in 合法等级:
        raise ValueError("XR 只能是 " + " / ".join(合法等级) + "，现在给的是：" + 等级)
    if not os.path.isfile(路径):
        raise ValueError("文件不在，写不了属性：" + str(路径))
    标记 = "XR: " + 等级
    try:
        with open(_流路(路径), "w", encoding="utf-8") as 流:
            流.write(标记)
    except OSError as 异常:
        raise ValueError("这个位置写不了文件属性（%s）：%s" % (type(异常).__name__, 路径))
    回 = 读XR(路径)
    if 回 != 标记:
        raise ValueError("属性写完读回来是 %r，不是 %r：%s" % (回, 标记, 路径))
    return 标记


def 读XR(路径):
    try:
        with open(_流路(路径), "r", encoding="utf-8") as 流:
            return 流.read().strip()
    except (OSError, UnicodeDecodeError):
        return ""
