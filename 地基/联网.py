
import json
import urllib.error
import urllib.request

from 地基 import 大模型

搜索端点 = "/v1/tools/search"
抓取端点 = "/v1/tools/fetch"
超时 = 25
最多条数 = 10

错误说明 = {
    401: "密钥不对（401）。去「模型配置」检查 API Key。",
    402: "账户余额不足（402）。搜索按次计费，充值后才能用。",
    403: "被安全策略拦了（403）。这条请求可能不合规，换个问法试试。",
    404: "没抓到内容（404）。网址可能已经失效。",
    429: "请求太快被限流（429）。每个账号每秒最多 5 次，等一秒再试。",
}


def 取通道(服务商=None):
    名字, 条目 = 大模型.选服务商(大模型.读配置(), 服务商)
    地址 = str(条目.get("base_url") or "").strip().rstrip("/")
    主机 = 地址.split("//")[-1].split("/")[0].lower()
    if 主机 != "api.deepseek.com":
        raise RuntimeError(
            "联网查证只支持 DeepSeek 官方接口（api.deepseek.com），当前服务商是 "
            + repr(名字) + "（" + 地址 + "）。去「模型配置」切到 deepseek 再用。")
    return 地址, 大模型.取密钥(名字, 条目)


def 发请求(端点, 请求体, 服务商=None):
    地址, 密钥 = 取通道(服务商)
    请求 = urllib.request.Request(
        地址 + 端点,
        data=json.dumps(请求体, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + 密钥})
    try:
        with urllib.request.urlopen(请求, timeout=超时) as 响应:
            return json.loads(响应.read().decode("utf-8"))
    except urllib.error.HTTPError as 异常:
        说明 = 错误说明.get(异常.code)
        if 说明:
            raise RuntimeError(说明) from None
        raise RuntimeError("联网接口回了 HTTP %s：%s"
                           % (异常.code, 异常.read().decode("utf-8", "replace")[:160])) from None
    except urllib.error.URLError as 异常:
        raise RuntimeError("连不上 DeepSeek（%s）。检查网络或代理。" % 异常.reason) from None


def 搜索(查询, 条数=5, 时效="", 要正文=False, 服务商=None):
    查询 = (查询 or "").strip()
    if not 查询:
        raise ValueError("要搜什么？查询不能为空")
    if len(查询) > 128:
        raise ValueError("查询最多 128 个字符，现在 %d 个" % len(查询))
    try:
        数 = int(条数 or 5)
    except (TypeError, ValueError):
        数 = 5
    请求体 = {"query": 查询, "count": max(1, min(最多条数, 数))}
    if 时效:
        请求体["freshness"] = str(时效)
    if 要正文:
        请求体["need_content"] = True
    return 发请求(搜索端点, 请求体, 服务商)


def 抓取(网址, 服务商=None):
    网址 = (网址 or "").strip()
    if not 网址.lower().startswith(("http://", "https://")):
        raise ValueError("网址要以 http:// 或 https:// 开头")
    if len(网址) > 8192:
        raise ValueError("网址太长（上限 8192 字符）")
    return 发请求(抓取端点, {"url": 网址}, 服务商)


def 整理结果(原始, 上限=5):
    条目 = []
    for 一 in (原始.get("results") or [])[:上限]:
        条目.append({
            "标题": 一.get("title") or "（无标题）",
            "网址": 一.get("url") or "",
            "时间": 一.get("date") or "",
            "权威": 一.get("authority"),
            "摘要": (一.get("summary") or 一.get("snippet") or "").strip(),
        })
    return 条目
