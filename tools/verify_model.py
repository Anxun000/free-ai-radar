# -*- coding: utf-8 -*-
"""
单模型实测验证
=========================================================
对指定模型发出【真实请求】，验证它的能力到底是"平台声明"还是"真的能用"：
  1. 基础对话   —— 模型是否可调用
  2. 工具调用   —— 强制要求调用工具，看是否真的返回 tool_calls
  3. 图片输入   —— 真的传一张图片进去，看是否能识别

判定为【三态】，避免把"没测出来"误当成"不支持"：
  yes     = 实测通过
  no      = 模型/端点明确不支持
  unknown = 没测出来（上游限流、正文为空等），不计入分母

用法：
  python tools/verify_model.py thinkingmachines/inkling-small:free
  python tools/verify_model.py sensenova-6.8-flash-lite --platform sensenova

安全：密钥仅用于请求头，不打印、不落盘。
"""
import argparse
import base64
import json
import struct
import sys
import urllib.error
import urllib.request
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from check_keys import load_keys, UA, KEYFILE  # noqa: E402

# 平台 → (base_url, 取哪个 key)
PLATFORM_ROUTES = {
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "nvidia": ("https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY"),
    "zhipu": ("https://open.bigmodel.cn/api/paas/v4", "ZHIPU_API_KEY"),
    "longcat": ("https://api.longcat.chat/openai/v1", "LONGCAT_API_KEY"),
    "sensenova": ("https://token.sensenova.cn/v1", "SENSENOVA_API_KEY"),
    "agnes": ("https://apihub.agnes-ai.com/v1", "AGNES_API_KEY"),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
}

MARK = {"yes": "✅ 通过", "no": "❌ 不支持", "unknown": "⚠  未测出"}


def make_png(w: int, h: int, rgb: tuple) -> bytes:
    """纯标准库生成一张纯色 PNG，用于图片输入测试。"""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def post(url: str, key: str, body: dict, timeout: int = 90):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": UA, "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raw = e.read(600).decode("utf-8", "replace")
        try:
            raw = json.dumps(json.loads(raw), ensure_ascii=False)[:300]
        except Exception:
            raw = " ".join(raw.split())[:300]
        return e.code, {"_raw": raw}
    except Exception as e:
        return None, {"_raw": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------- 判定辅助
def _blob(d) -> str:
    try:
        return json.dumps(d, ensure_ascii=False).lower()
    except Exception:
        return str(d).lower()


def _is_limited(st, d) -> bool:
    """上游限流 —— 属于「没测出来」，不是「不支持」。"""
    if st == 429:
        return True
    b = _blob(d)
    return "rate-limited" in b or "rate limited" in b or "too many requests" in b


def _mentions(d, *words) -> bool:
    b = _blob(d)
    return any(w.lower() in b for w in words)


def _msg(d):
    return (d.get("choices") or [{}])[0].get("message", {}) or {}


# ---------------------------------------------------------------- 三项测试
def test_chat(base, key, model):
    """基础对话：能不能调通。max_tokens 给足，避免推理模型把额度用光。"""
    st, d = post(f"{base}/chat/completions", key, {
        "model": model, "max_tokens": 512,
        "messages": [{"role": "user", "content": "用一句话说明你是哪个模型。"}],
    })
    if st == 200:
        txt = (_msg(d).get("content") or _msg(d).get("reasoning_content") or "").strip()
        if not txt:
            return "unknown", "HTTP 200，但正文为空（推理可能占满了额度）"
        return "yes", txt[:110] + ("…" if len(txt) > 110 else "")
    if _is_limited(st, d):
        return "unknown", f"HTTP {st} · 上游限流，本次未测出"
    return "no", f"HTTP {st} · {d.get('_raw','')}"


TOOLS_SPEC = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询某个城市的当前天气",
        "parameters": {"type": "object",
                       "properties": {"city": {"type": "string", "description": "城市名"}},
                       "required": ["city"]},
    },
}]

TOOLS_ASK = "北京现在天气怎么样？请调用工具查询。"


def _tool_call(base, key, model, choice):
    return post(f"{base}/chat/completions", key, {
        "model": model, "max_tokens": 800,
        "messages": [{"role": "user", "content": TOOLS_ASK}],
        "tools": TOOLS_SPEC,
        "tool_choice": choice,
    })


def _extract_call(d):
    calls = _msg(d).get("tool_calls") or []
    if not calls:
        return None
    fn = calls[0].get("function", {}) or {}
    args = str(fn.get("arguments"))[:60]
    return f'{fn.get("name")}({args})'


def test_tools(base, key, model):
    """工具调用：先强制 tool_choice=required，没返回再用 auto 复核一次。"""
    st, d = _tool_call(base, key, model, "required")

    if st == 200:
        hit = _extract_call(d)
        if hit:
            return "yes", f"强制调用 → {hit}"
        # 200 但没调用 —— 可能是模型忽略了 required，用 auto 复核避免误判
        st2, d2 = _tool_call(base, key, model, "auto")
        if st2 == 200:
            hit2 = _extract_call(d2)
            if hit2:
                return "yes", f"自动选择 → {hit2}"
        return "no", "两次请求均未返回 tool_calls（该模型不支持函数调用）"

    if _is_limited(st, d):
        return "unknown", f"HTTP {st} · 上游限流，本次未测出"
    if _mentions(d, "tool use", "tool_choice", "no endpoints found that support"):
        return "no", f"HTTP {st} · 端点明确不支持工具调用"
    return "no", f"HTTP {st} · {d.get('_raw','')}"


def test_vision(base, key, model):
    """图片输入：真的塞一张红图进去，看能否识别出颜色。"""
    b64 = base64.b64encode(make_png(64, 64, (220, 30, 30))).decode()
    st, d = post(f"{base}/chat/completions", key, {
        "model": model, "max_tokens": 400,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "这张图是什么颜色？只回答颜色。"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]}],
    })
    if st == 200:
        txt = (_msg(d).get("content") or "").strip()
        if not txt:
            return "unknown", "HTTP 200，但正文为空，无法判断"
        hit = ("红" in txt) or ("red" in txt.lower())
        return ("yes" if hit else "no"), txt[:90] + ("" if hit else "  ← 没能识别出红色")
    if _is_limited(st, d):
        return "unknown", f"HTTP {st} · 上游限流，本次未测出"
    if _mentions(d, "image input", "support image", "no endpoints found that support"):
        return "no", f"HTTP {st} · 端点明确不支持图片输入"
    return "no", f"HTTP {st} · {d.get('_raw','')}"


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", help="模型 ID，例如 thinkingmachines/inkling-small:free")
    ap.add_argument("--platform", default="openrouter",
                    help="平台：openrouter / gemini / groq / nvidia / zhipu / longcat / sensenova / agnes")
    ap.add_argument("--skip-vision", action="store_true")
    args = ap.parse_args()

    if args.platform not in PLATFORM_ROUTES:
        raise SystemExit(f"不支持的平台：{args.platform}，可选：{', '.join(PLATFORM_ROUTES)}")
    base, env = PLATFORM_ROUTES[args.platform]
    key = load_keys(KEYFILE).get(env)
    if not key:
        raise SystemExit(f"密钥文件里没有 {env}，无法实测。")

    print(f"实测模型：{args.model}")
    print(f"平台    ：{args.platform}  ({base})")
    print("=" * 74)

    results = []
    print("\n[1/3] 基础对话 …")
    s, info = test_chat(base, key, args.model)
    results.append(("基础对话", s))
    print(f"      {MARK[s]}  {info}")

    print("\n[2/3] 工具调用 …")
    s, info = test_tools(base, key, args.model)
    results.append(("工具调用", s))
    print(f"      {MARK[s]}  {info}")

    if args.skip_vision:
        print("\n[3/3] 图片输入 …（已跳过）")
    else:
        print("\n[3/3] 图片输入 …")
        s, info = test_vision(base, key, args.model)
        results.append(("图片输入", s))
        print(f"      {MARK[s]}  {info}")

    print("\n" + "=" * 74)
    tested = [(n, s) for n, s in results if s != "unknown"]
    passed = [n for n, s in tested if s == "yes"]
    print(f"结论：{len(passed)}/{len(tested)} 项实测通过"
          + (f"（另有 {len(results)-len(tested)} 项未测出）" if len(results) > len(tested) else ""))
    for name, s in results:
        print(f"  {MARK[s]}  {name}")

    save_result(args.model, args.platform, results)


def save_result(model: str, platform: str, results):
    """写入 data/verified.json，供 build.py 渲染「逐项实测」徽章。"""
    from datetime import datetime, timezone

    path = ROOT / "data" / "verified.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    d = dict(results)
    rec = {"model": model, "platform": platform}
    for cn, en in (("基础对话", "chat"), ("工具调用", "tools"), ("图片输入", "vision")):
        v = d.get(cn)
        rec[en] = (v == "yes")
        rec.setdefault("tested", {})[en] = (v in ("yes", "no"))
    rec["verified_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    data[f"{platform}::{model}"] = rec
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已记录到 {path.name}（共 {len(data)} 个模型的实测结果）")


if __name__ == "__main__":
    main()
