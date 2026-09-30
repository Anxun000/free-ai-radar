# -*- coding: utf-8 -*-
"""
单模型实测验证
=========================================================
对指定模型发出【真实请求】，验证它的能力到底是"平台声明"还是"真的能用"：
  1. 基础对话   —— 模型是否可调用
  2. 工具调用   —— 真的发一次 Function Calling
  3. 图片输入   —— 真的传一张图片进去

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
        body = e.read(600).decode("utf-8", "replace")
        try:
            body = json.dumps(json.loads(body), ensure_ascii=False)[:300]
        except Exception:
            body = " ".join(body.split())[:300]
        return e.code, {"_raw": body}
    except Exception as e:
        return None, {"_raw": f"{type(e).__name__}: {e}"}


def test_chat(base, key, model):
    st, d = post(f"{base}/chat/completions", key, {
        "model": model, "max_tokens": 60,
        "messages": [{"role": "user", "content": "用一句话说明你是哪个模型。"}],
    })
    if st != 200:
        return False, f"HTTP {st} · {d.get('_raw','')}"
    msg = (d.get("choices") or [{}])[0].get("message", {}) or {}
    txt = (msg.get("content") or msg.get("reasoning_content") or "").strip()
    return True, (txt[:110] + ("…" if len(txt) > 110 else "")) or "(返回内容为空)"


def test_tools(base, key, model):
    st, d = post(f"{base}/chat/completions", key, {
        "model": model, "max_tokens": 200,
        "messages": [{"role": "user", "content": "北京现在天气怎么样？请调用工具查询。"}],
        "tools": [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "查询某个城市的当前天气",
                "parameters": {"type": "object",
                               "properties": {"city": {"type": "string", "description": "城市名"}},
                               "required": ["city"]},
            },
        }],
        "tool_choice": "auto",
    })
    if st != 200:
        return False, f"HTTP {st} · {d.get('_raw','')}"
    msg = (d.get("choices") or [{}])[0].get("message", {}) or {}
    calls = msg.get("tool_calls") or []
    if calls:
        fn = calls[0].get("function", {})
        return True, f'返回 tool_calls → {fn.get("name")}({fn.get("arguments")})'
    return False, f"未返回 tool_calls（模型选择直接回答）：{(msg.get('content') or '')[:70]}"


def test_vision(base, key, model):
    b64 = base64.b64encode(make_png(64, 64, (220, 30, 30))).decode()
    st, d = post(f"{base}/chat/completions", key, {
        "model": model, "max_tokens": 80,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "这张图是什么颜色？只回答颜色。"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]}],
    })
    if st != 200:
        return False, f"HTTP {st} · {d.get('_raw','')}"
    msg = (d.get("choices") or [{}])[0].get("message", {}) or {}
    txt = (msg.get("content") or "").strip()
    hit = ("红" in txt) or ("red" in txt.lower())
    return hit, (txt[:90] or "(空)") + ("" if hit else "  ← 未能识别出红色")


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
    keys = load_keys(KEYFILE)
    key = keys.get(env)
    if not key:
        raise SystemExit(f"密钥文件里没有 {env}，无法实测。")

    print(f"实测模型：{args.model}")
    print(f"平台    ：{args.platform}  ({base})")
    print("=" * 70)

    results = []
    print("\n[1/3] 基础对话 …")
    ok, info = test_chat(base, key, args.model)
    results.append(("基础对话", ok))
    print(f"      {'✅ 通过' if ok else '❌ 未通过'}  {info}")

    print("\n[2/3] 工具调用 …")
    ok, info = test_tools(base, key, args.model)
    results.append(("工具调用", ok))
    print(f"      {'✅ 通过' if ok else '❌ 未通过'}  {info}")

    if args.skip_vision:
        print("\n[3/3] 图片输入 …（已跳过）")
    else:
        print("\n[3/3] 图片输入 …")
        ok, info = test_vision(base, key, args.model)
        results.append(("图片输入", ok))
        print(f"      {'✅ 通过' if ok else '❌ 未通过'}  {info}")

    print("\n" + "=" * 70)
    passed = sum(1 for _, o in results if o)
    print(f"结论：{passed}/{len(results)} 项实测通过")
    for name, o in results:
        print(f"  {'✅' if o else '❌'} {name}")

    save_result(args.model, args.platform, results)


def save_result(model: str, platform: str, results):
    """把实测结果写入 data/verified.json，供 build.py 合成「实测通过」徽章。"""
    import json
    from datetime import datetime, timezone

    path = ROOT / "data" / "verified.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    key = f"{platform}::{model}"
    data[key] = {
        "model": model,
        "platform": platform,
        "chat": dict(results).get("基础对话", False),
        "tools": dict(results).get("工具调用", False),
        "vision": dict(results).get("图片输入", False),
        "verified_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已记录到 {path.name}（共 {len(data)} 个模型的实测结果）")


if __name__ == "__main__":
    main()
