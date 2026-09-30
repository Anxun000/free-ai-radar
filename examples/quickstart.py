# -*- coding: utf-8 -*-
"""
快速上手示例
=========================================================
演示：从「免费 AI 模型雷达」里挑一个模型，用你的 key 真的跑起来。

运行：
  python examples/quickstart.py                            # 用默认模型
  python examples/quickstart.py stealth/space-bunny-alpha  # 指定模型
  python examples/quickstart.py <模型ID> "你想问的问题"

模型 ID 就是应用卡片标题下面那行灰色小字，直接复制过来即可。
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from check_keys import load_keys, KEYFILE  # noqa: E402

# ── 默认模型：在应用里标着「✅ 实测可调用」 ─────────────────
DEFAULT_MODEL = "google/gemma-4-26b-a4b-it:free"
DEFAULT_PROMPT = "用一句话解释什么是「免费 AI 模型雷达」。"

# ── 从卡片上抄下来的固定项，一般不用改 ──────────────────────
BASE_URL = "https://openrouter.ai/api/v1"
KEY_NAME = "OPENROUTER_API_KEY"


def explain(code: int, body: str) -> str:
    """把常见错误翻译成人话。"""
    if code == 429:
        return ("\n\n💡 429 是【限流】，不是代码问题。通常是两种情况之一："
                "\n   ① 该免费模型的上游供应方正在拥堵（如 Google AI Studio）→ 换个模型，或过几分钟重试"
                "\n   ② OpenRouter 免费档的每日额度用完（50 请求/日）→ 等次日重置"
                "\n   规避思路：如果这个模型平台自己也有免费档，优先走平台直连，不绕 OpenRouter。")
    if code == 403 and "agentic harnesses" in body:
        return ("\n\n💡 这个模型被限制为【只能在 Agent 客户端内使用】，普通 API 调不通。"
                "\n   请换一个在应用里标着「✅ 实测可调用」的模型。")
    if code == 403:
        return "\n\n💡 403：密钥无效 / 无权限，检查一下 key 是否复制完整。"
    if code == 401:
        return "\n\n💡 401：密钥无效或已被删除，去平台后台重新生成一个。"
    return ""


def call_raw(api_key: str, model: str, prompt: str) -> bool:
    """不依赖任何第三方库的写法。返回是否成功。"""
    import json
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
        }).encode(),
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read(800).decode("utf-8", "replace")
        print(f"❌ 调用失败 HTTP {e.code}{explain(e.code, body)}")
        print(f"\n原始返回：{body[:300]}")
        return False
    except Exception as e:
        print(f"❌ 网络异常：{type(e).__name__}: {e}")
        return False

    show(d)
    return True


def call_sdk(api_key: str, model: str, prompt: str) -> bool:
    """用官方 openai 库的写法（推荐，装了 openai 才会走这条）。"""
    from openai import OpenAI

    client = OpenAI(base_url=BASE_URL, api_key=api_key)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
    except Exception as e:
        code = getattr(e, "status_code", None) or 0
        body = str(e)
        print(f"❌ 调用失败 {type(e).__name__}{explain(code, body)}")
        print(f"\n原始信息：{body[:300]}")
        return False

    d = {"choices": [{"message": {
        "content": resp.choices[0].message.content,
        "reasoning": getattr(resp.choices[0].message, "reasoning", None),
    }}], "usage": (resp.usage.model_dump() if resp.usage else None),
         "model": resp.model}
    show(d)
    return True


def show(d: dict):
    """打印模型回复。有些推理模型会把思考过程单独放在 reasoning 字段里。"""
    msg = (d.get("choices") or [{}])[0].get("message", {}) or {}
    content = (msg.get("content") or "").strip()
    reasoning = (msg.get("reasoning") or "").strip()

    if reasoning:
        head = reasoning[:220].replace("\n", " ")
        print(f"🧠 思考过程（截断）：{head}{'…' if len(reasoning) > 220 else ''}")
        print()
    print("模型回答：")
    print(content if content else "（该模型本次没有输出正文，可能把内容都放在思考过程里了）")
    print("-" * 62)

    usage = d.get("usage") or {}
    if usage:
        print(f"tokens：输入 {usage.get('prompt_tokens')} / "
              f"输出 {usage.get('completion_tokens')} / "
              f"合计 {usage.get('total_tokens')}")
    print(f"实际服务方：{d.get('model')}")


def main():
    ap = argparse.ArgumentParser(description="免费 AI 模型快速上手示例")
    ap.add_argument("model", nargs="?", default=DEFAULT_MODEL,
                    help=f"模型 ID（默认 {DEFAULT_MODEL}）")
    ap.add_argument("prompt", nargs="?", default=DEFAULT_PROMPT, help="要问的问题")
    args = ap.parse_args()

    keys = load_keys(KEYFILE)
    api_key = keys.get(KEY_NAME)
    if not api_key:
        print(f"❌ 密钥文件里没找到 {KEY_NAME}")
        print(f"   请打开 {KEYFILE} 填写后重试。")
        return

    print(f"模型  ：{args.model}")
    print(f"接口  ：{BASE_URL}")
    print(f"密钥  ：已读取（长度 {len(api_key)}，不显示内容）")
    print("-" * 62)

    try:
        import openai  # noqa: F401
        ok = call_sdk(api_key, args.model, args.prompt)
    except ImportError:
        print("（未安装 openai 库，改用标准库直接发请求 —— 效果完全一样）\n")
        ok = call_raw(api_key, args.model, args.prompt)

    if ok:
        print("\n✅ 跑通了。换模型只需在执行时带上模型 ID。")


if __name__ == "__main__":
    main()
