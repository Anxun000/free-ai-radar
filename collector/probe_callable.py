# -*- coding: utf-8 -*-
"""
免费模型「可直接调用」探针
=========================================================
背景：OpenRouter 上部分免费模型被限制为「仅可在 Agent 客户端中使用」，
      声明字段一切正常，但用普通 API 调用会返回
      403 "is only available on agentic harnesses"。
      这类模型必须在应用里单独标出来，否则用户会白折腾。

本脚本对每个免费模型发一次最小请求，判定三态：
  callable      可直接 API 调用
  agentic_only  仅限 Agent 客户端（第三方 coding agent / 生产力应用）
  error         其他错误

产出：data/callable.json
用法：python collector/probe_callable.py
"""
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from check_keys import load_keys, UA, KEYFILE  # noqa: E402

OUT = ROOT / "data" / "callable.json"
BASE = "https://openrouter.ai/api/v1"


def probe(key: str, model: str, timeout: int = 60, retry_429: bool = True):
    """返回 (verdict, http, message)。verdict ∈ callable/agentic_only/congested/not_chat/error"""
    body = json.dumps({
        "model": model, "max_tokens": 5,
        "messages": [{"role": "user", "content": "hi"}],
    }).encode()
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": UA},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            json.loads(r.read().decode("utf-8", "replace"))
            return "callable", r.status, ""
    except urllib.error.HTTPError as e:
        raw = e.read(900).decode("utf-8", "replace")
        try:
            msg = json.loads(raw).get("error", {}).get("message", "")
        except Exception:
            msg = " ".join(raw.split())[:200]
        if "agentic harnesses" in msg:
            return "agentic_only", e.code, msg
        # 429 是限流，不代表模型不可用 —— 稍等后重试一次
        if e.code == 429 and retry_429:
            time.sleep(4)
            return probe(key, model, timeout, retry_429=False)
        if e.code == 429:
            return "congested", e.code, msg[:200]
        return "error", e.code, msg[:200]
    except Exception as e:
        return "error", None, f"{type(e).__name__}: {e}"


VERDICT_LABEL = {
    "callable": "✅ 可直接调用",
    "agentic_only": "🔒 仅限 Agent 客户端",
    "congested": "⏳ 限流中（可重试）",
    "not_chat": "🎵 非对话模型（接口不同）",
    "error": "❌ 调用失败",
}


def main():
    keys = load_keys(KEYFILE)
    key = keys.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("缺少 OPENROUTER_API_KEY")

    # 拉取免费模型清单
    req = urllib.request.Request(f"{BASE}/models", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        models = json.loads(r.read().decode())["data"]
    free = [m for m in models
            if str(m.get("pricing", {}).get("prompt")) == "0"
            and str(m.get("pricing", {}).get("completion")) == "0"]

    print(f"对 {len(free)} 个免费模型逐个发起真实调用探测…\n")
    print(f"{'模型':<46}{'HTTP':<7}{'判定'}")
    print("-" * 92)

    results = {k: 0 for k in VERDICT_LABEL}
    results_out = {}
    for m in free:
        mid = m["id"]
        out_mods = ((m.get("architecture") or {}).get("output_modalities")) or []
        # 输出含音频的（如 Lyria 音乐生成）走的是另一套接口，对话接口不适用，不探测
        if out_mods and ("text" not in out_mods or "audio" in out_mods):
            verdict, code, msg = "not_chat", None, f'输出模态：{", ".join(out_mods)}（需专用接口）'
        else:
            verdict, code, msg = probe(key, mid)
        results[verdict] += 1
        results_out[mid] = {"verdict": verdict, "http": code, "message": msg,
                            "name": m.get("name")}
        print(f"{mid[:45]:<46}{str(code or '—'):<7}{VERDICT_LABEL[verdict]}")
        time.sleep(0.4)

    print("-" * 92)
    print(" · ".join(f"{VERDICT_LABEL[k].split(' ',1)[1]} {v}"
                     for k, v in results.items() if v))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "probed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "counts": results, "results": results_out,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写入 {OUT}")


if __name__ == "__main__":
    main()
