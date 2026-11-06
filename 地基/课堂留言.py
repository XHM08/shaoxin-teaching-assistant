
import threading
import time

条数上限 = 500
内容上限 = 200
谁的上限 = 20
重复窗口秒 = 5

_锁 = threading.Lock()
_表 = []
_下个序号 = 1
_丢过 = 0


def 洗(文字):
    return "".join(字符 for 字符 in str(文字 or "") if 字符 >= " " or 字符 == "\t").replace("\t", " ").strip()


def 收拾(文字, 上限):
    干净 = 洗(文字)
    return (干净[:上限] + "…") if len(干净) > 上限 else 干净


def 记一条(谁, 内容, 来源="窗口"):
    global _下个序号, _丢过
    内容 = 洗(内容)
    if not 内容:
        raise ValueError("内容是空的：说点什么再发")
    if len(内容) > 内容上限:
        raise ValueError("太长了（%d 个字，一次最多 %d 个字）。拆成几句分开发"
                         % (len(内容), 内容上限))
    谁 = 收拾(谁, 谁的上限) or "同学"
    现在 = time.time()
    with _锁:
        表尾 = _表[-1] if _表 else None
        if 表尾 and 表尾["谁"] == 谁 and 表尾["内容"] == 内容 and 现在 - 表尾["时刻"] < 重复窗口秒:
            return dict(表尾)
        一条 = {"序号": _下个序号, "时刻": 现在,
              "时间": time.strftime("%H:%M:%S", time.localtime(现在)),
              "谁": 谁, "内容": 内容, "来源": 收拾(来源, 10) or "窗口"}
        _下个序号 += 1
        _表.append(一条)
        while len(_表) > 条数上限:
            _表.pop(0)
            _丢过 += 1
        return dict(一条)


def 从设备记一条(设备, 文字):
    设备 = 收拾(设备, 谁的上限) or "麦克风"
    return 记一条(设备, 文字, 来源=设备)


def 取新的(自序号=0):
    try:
        自序号 = int(自序号)
    except (TypeError, ValueError):
        自序号 = 0
    with _锁:
        新的 = [dict(一条) for 一条 in _表 if 一条["序号"] > 自序号]
        总数 = _下个序号 - 1
        丢过 = _丢过
    return {"留言": 新的, "共": 总数, "丢过": 丢过}


def 清空():
    global _表, _下个序号, _丢过
    with _锁:
        _表 = []
        _丢过 = 0
