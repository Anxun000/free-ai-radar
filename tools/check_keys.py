# -*- coding: utf-8 -*-
"""
API Key 连通性自检
================================================
用途：验证「密钥填写.txt」里的 key 是否真实可用。
安全：本脚本【绝不】打印密钥内容，只输出 HTTP 状态与判定结果。

运行：
  python tools/check_keys.py
"""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYFILE = ROOT / "密钥填写.txt"

# 已知密钥字段名。环境变量优先级高于本地文件，
# 以便在 GitHub Actions 中用 Secrets 注入而不落地任何文件。
KNOWN_FIELDS = (
    "OPENROUTER_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "NVIDIA_API_KEY",
    "MISTRAL_API_KEY", "COHERE_API_KEY", "HUGGINGFACE_API_KEY",
    "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN",
    "ZHIPU_API_KEY", "LONGCAT_API_KEY", "SENSENOVA_API_KEY", "AGNES_API_KEY",
)

TIMEOUT = 12

# ⚠️ 必须伪装成浏览器。Groq 等平台挂在 Cloudflare 后面，
# 非浏览器 UA 会被拦截并返回 403 + error code 1010（实测踩坑）。
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


def load_keys(path: Path = KEYFILE) -> dict:
    """先读文件，再用环境变量覆盖（环境变量优先，便于 CI 用 Secrets 注入）。"""
    keys = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            s = line.strip()
            if "=" not in s or s.startswith("#"):
                continue
            k, _, v = s.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if not k or not k.replace("_", "").isalnum():
                continue
            if v:
                keys[k] = v
    for k in KNOWN_FIELDS:
        v = (os.environ.get(k) or "").strip()
        if v:
            keys[k] = v
    return keys


def http(url: str, headers: dict | None = None, timeout: int = TIMEOUT):
    """返回 (status, body)。status=None 表示网络层失败。始终带浏览器 UA。"""
    merged = {"User-Agent": UA, "Accept": "application/json"}
    merged.update(headers or {})
    req = urllib.request.Request(url, headers=merged)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(4_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(800).decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def interpret(status, body: str) -> str:
    if status is None:
        return "网络不通"
    if "1010" in body:
        return "被 Cloudflare 拦截（UA 问题）"
    if status == 200:
        return "有效"
    if status == 401:
        return "密钥无效 / 已被删除"
    if status == 402:
        return "额度不足"
    if status == 403:
        return "拒绝访问：密钥无效、无权限，或填错密钥类型"
    if status == 404:
        return "端点不存在（密钥无法据此判定）"
    if status == 429:
        return "触发限流（密钥有效但请求过密）"
    return f"HTTP {status}"


def bearer(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


# ── 各平台探测端点 ────────────────────────────────────────────
# 统一优先探测「列模型」接口：不消耗 token，且能真实校验密钥。
PROBES = [
    (
        "OPENROUTER_API_KEY",
        "OpenRouter",
        lambda k: http("https://openrouter.ai/api/v1/key", bearer(k)),
    ),
    (
        "GEMINI_API_KEY",
        "Google Gemini",
        lambda k: http(
            f"https://generativelanguage.googleapis.com/v1beta/models?pageSize=3&key={k}"
        ),
    ),
    (
        "GROQ_API_KEY",
        "Groq",
        lambda k: http("https://api.groq.com/openai/v1/models", bearer(k)),
    ),
    (
        "NVIDIA_API_KEY",
        "NVIDIA NIM",
        lambda k: http("https://integrate.api.nvidia.com/v1/models", bearer(k)),
    ),
    (
        "ZHIPU_API_KEY",
        "智谱 BigModel",
        lambda k: http("https://open.bigmodel.cn/api/paas/v4/models", bearer(k)),
    ),
    (
        "LONGCAT_API_KEY",
        "美团 LongCat",
        lambda k: http("https://api.longcat.chat/openai/v1/models", bearer(k)),
    ),
    (
        "SENSENOVA_API_KEY",
        "商汤日日新",
        # ⚠️ 注意：正确域名是 token.sensenova.cn，不是 api.sensenova.cn
        lambda k: http("https://token.sensenova.cn/v1/models", bearer(k)),
    ),
    (
        "AGNES_API_KEY",
        "Agnes AI",
        lambda k: http("https://apihub.agnes-ai.com/v1/models", bearer(k)),
    ),
    (
        "CLOUDFLARE_ACCOUNT_ID",
        "Cloudflare Workers AI",
        None,  # 需要 account_id，单独处理
    ),
    (
        "MISTRAL_API_KEY",
        "Mistral",
        lambda k: http("https://api.mistral.ai/v1/models", bearer(k)),
    ),
    (
        "COHERE_API_KEY",
        "Cohere",
        lambda k: http("https://api.cohere.com/v1/models", bearer(k)),
    ),
    (
        "HUGGINGFACE_API_KEY",
        "Hugging Face",
        lambda k: http(
            "https://huggingface.co/api/whoami-v2", bearer(k)
        ),
    ),
]


def main() -> None:
    keys = load_keys(KEYFILE)
    print(f"密钥文件：{KEYFILE}")
    print(f"检测到 {len(keys)} 个已填写的密钥")
    print()
    print(f"{'平台':<22}{'字段':<26}{'HTTP':<7}{'判定'}")
    print("-" * 88)

    ok = 0
    for field, label, probe in PROBES:
        if field not in keys:
            print(f"{label:<22}{field:<26}{'-':<7}未填写")
            continue

        if probe is None:
            # Cloudflare 需要 account_id + token 两个值配套
            aid = keys.get("CLOUDFLARE_ACCOUNT_ID", "")
            tok = keys.get("CLOUDFLARE_API_TOKEN", "")
            bad_aid = len(aid) != 32 or not all(
                c in "0123456789abcdefABCDEF" for c in aid
            )
            bad_tok = not (35 <= len(tok) <= 45)
            if bad_aid or bad_tok:
                detail = []
                if bad_aid:
                    detail.append(f"account_id 应为 32 位十六进制，实为 {len(aid)} 字符")
                if not tok:
                    detail.append("token 未填写")
                elif bad_tok:
                    detail.append(f"token 应为约 40 位字母数字，实为 {len(tok)} 字符")
                print(f"{label:<22}{field:<26}{'-':<7}" + "；".join(detail))
                continue
            if not tok:
                print(f"{label:<22}{field:<26}{'-':<7}token 未填写")
                continue
            url = f"https://api.cloudflare.com/client/v4/accounts/{aid}/ai/models/search"
            status, body = http(url, bearer(tok))
            verdict = interpret(status, body)
            if status == 200:
                ok += 1
            code = str(status) if status is not None else "ERR"
            print(f"{label:<22}{field:<26}{code:<7}{verdict}")
            continue

        status, body = probe(keys[field])
        verdict = interpret(status, body)
        if status == 200:
            ok += 1
        code = str(status) if status is not None else "ERR"
        print(f"{label:<22}{field:<26}{code:<7}{verdict}")

    print("-" * 88)
    print(f"可用：{ok} 个")
    print()

    # 额外：OpenRouter 余额 / 限额明细（有助于确认额度策略是否生效）
    if "OPENROUTER_API_KEY" in keys:
        status, body = http(
            "https://openrouter.ai/api/v1/key", bearer(keys["OPENROUTER_API_KEY"])
        )
        if status == 200:
            try:
                d = json.loads(body).get("data", {})
                print("OpenRouter 密钥详情：")
                print(f"  标签      : {d.get('label')}")
                print(f"  额度上限  : {d.get('limit')}")
                print(f"  已用额度  : {d.get('usage')}")
                print(f"  免费额度档: {d.get('is_free_tier')}")
                print(f"  限速      : {d.get('rate_limit')}")
            except Exception as e:
                print(f"  （解析失败：{e}）")


if __name__ == "__main__":
    main()
