
import os
import shutil
import tempfile
import time


def 原子写文本(路径, 文本):
    目录 = os.path.dirname(os.path.abspath(路径))
    os.makedirs(目录, exist_ok=True)
    句柄, 临时 = tempfile.mkstemp(dir=目录,
                               prefix=os.path.basename(路径) + ".",
                               suffix=".tmp")
    try:
        with os.fdopen(句柄, "w", encoding="utf-8") as 文件:
            文件.write(文本)
            文件.flush()
            os.fsync(文件.fileno())
        os.replace(临时, 路径)
    except Exception:
        try:
            os.remove(临时)
        except OSError:
            pass
        raise


def 带时间备份(路径):
    if not os.path.isfile(路径):
        return ""
    目录 = os.path.join(os.path.dirname(os.path.abspath(路径)), "_历史")
    os.makedirs(目录, exist_ok=True)
    文件名 = os.path.basename(路径)
    戳 = time.strftime("%Y%m%d-%H%M%S")
    目标 = os.path.join(目录, 文件名 + "." + 戳)
    序号 = 1
    while os.path.exists(目标):
        目标 = os.path.join(目录, 文件名 + "." + 戳 + "-" + str(序号))
        序号 += 1
    shutil.copy2(路径, 目标)
    return 目标
