# -*- coding: utf-8 -*-
"""
批量实测
=========================================================
对 data/callable.json 里所有判定为「可调用」的免费模型，
逐个发出【真实请求】，验证三项能力的真实可用性：

    1. 基础对话   —— 模型是否真的能调通
    2. 工具调用   —— 真的发一次 Function Calling，看是否返回 tool_calls
    3. 图片输入   —— 真的塞一张图片进去，看是否识别得出

产物写入 data/verified.json，供 build.py 渲染「逐项实测 N/3」徽章。

用法：
    python tools/verify_all.py                     # 增量跑（已有记录的跳过）
    python tools/verify_all.py --redo              # 全部重跑，覆盖旧结果
    python tools/verify_all.py --only qwen/qwen3.8-27b:free
    python tools/verify_all.py --workers 4 --interval 3.5
    python tools/verify_all.py --dry-run           # 只列目标，不发请求

安全：密钥仅用于请求头，不打印、不落盘。
"""
import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from check_keys import load_keys, KEYFILE  # noqa: E402
import verify_model as vm  # noqa: E402

# ---------------------------------------------------------------- 全局限流
# OpenRouter 免费层约 20 请求/分。这里用「最小间隔」令牌桶把请求节流，
# 避免并发把额度打爆后全线 429。
_lock = threading.Lock()
_last_at = [0.0]
_interval = [3.5]

_orig_post = vm.post


def _throttled_post(*a, **kw):
    with _lock:
        now = time.time()
        wait = _interval[0] - (now - _last_at[0])
        if wait > 0:
            time.sleep(wait)
        _last_at[0] = time.time()
    # 锁已释放，网络等待可以并发重叠
    return _orig_post(*a, **kw)


def _global_backoff(seconds: float):
    """遇到 429 时让所有 worker 一起停下来等一会。"""
    with _lock:
        _last_at[0] = time.time() + seconds


vm.post = _throttled_post


# ---------------------------------------------------------------- 单项测试
def _run_one(fn, base, key, model, retries=2, backoff=14):
    """跑一项测试，429 自动退避重试。"""
    ok, info = False, ""
    for attempt in range(retries + 1):
        ok, info = fn(base, key, model)
        if "HTTP 429" in info and attempt < retries:
            _global_backoff(backoff)
            continue
        return ok, info
    return ok, info


def verify_model(model: str, base: str, key: str, do_vision=True):
    """跑完三项，返回 (结果字典, 展示用明细)。"""
    detail = []

    ok, info = _run_one(vm.test_chat, base, key, model)
    detail.append(("基础对话", ok, info))
    chat = ok

    ok, info = _run_one(vm.test_tools, base, key, model)
    detail.append(("工具调用", ok, info))
    tools = ok

    if do_vision:
        ok, info = _run_one(vm.test_vision, base, key, model)
        detail.append(("图片输入", ok, info))
        vision = ok
    else:
        detail.append(("图片输入", None, "已跳过"))
        vision = None

    return {"chat": chat, "tools": tools, "vision": vision}, detail


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--redo", action="store_true", help="忽略已有结果，全部重跑")
    ap.add_argument("--only", default=None, help="只测指定模型 ID")
    ap.add_argument("--workers", type=int, default=4, help="并发数")
    ap.add_argument("--interval", type=float, default=3.5, help="请求最小间隔（秒）")
    ap.add_argument("--skip-vision", action="store_true", help="跳过图片输入测试")
    ap.add_argument("--dry-run", action="store_true", help="只列目标，不发请求")
    args = ap.parse_args()

    _interval[0] = args.interval

    cb_path = ROOT / "data" / "callable.json"
    if not cb_path.exists():
        raise SystemExit("缺少 data/callable.json，请先运行 collector/probe_callable.py")
    cb = json.loads(cb_path.read_text(encoding="utf-8"))

    # 只测判定为 callable 的
    targets = [m for m, v in (cb.get("results") or {}).items()
               if v.get("verdict") == "callable"]
    targets.sort()

    if args.only:
        targets = [t for t in targets if t == args.only] or [args.only]

    # 平台声明（来自 data.json），用于对照
    declared = {}
    dd_path = ROOT / "data" / "data.json"
    if dd_path.exists():
        dd = json.loads(dd_path.read_text(encoding="utf-8"))
        for m in dd.get("models", []):
            if m.get("platform") == "openrouter":
                declared[m["id"]] = m.get("caps") or {}

    # 已有实测结果
    vd_path = ROOT / "data" / "verified.json"
    existing = {}
    if vd_path.exists():
        try:
            existing = json.loads(vd_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    def key_of(m):
        return f"openrouter::{m}"

    todo = targets
    if not args.redo:
        todo = [m for m in targets if key_of(m) not in existing]

    print("=" * 78)
    print(f"批量实测 · 目标 {len(targets)} 个可调用模型，本次需跑 {len(todo)} 个")
    print(f"并发 {args.workers} · 请求间隔 {args.interval}s · 预计 ~{len(todo)*3*args.interval/args.workers:.0f}s")
    print("=" * 78)
    if not todo:
        print("无需实测（全部已有记录）。要重跑请加 --redo")
        return
    if args.dry_run:
        for m in todo:
            print("  ·", m)
        return

    keys = load_keys(KEYFILE)
    key = keys.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("密钥里没有 OPENROUTER_API_KEY，无法实测。")

    base = vm.PLATFORM_ROUTES["openrouter"][0]
    do_vision = not args.skip_vision

    results = {}
    done = [0]

    def work(m):
        res, detail = verify_model(m, base, key, do_vision=do_vision)
        return m, res, detail

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(work, m): m for m in todo}
        for fut in as_completed(futs):
            m = futs[fut]
            try:
                m, res, detail = fut.result()
            except Exception as e:  # noqa: BLE001
                print(f"  !! {m} 异常：{type(e).__name__}: {e}")
                continue

            done[0] += 1
            n_ok = sum(1 for _, o, _ in detail if o is True)
            n_tot = sum(1 for _, o, _ in detail if o is not None)
            print(f"\n[{done[0]}/{len(todo)}] {m}   →  {n_ok}/{n_tot} 通过")
            for name, ok, info in detail:
                mark = "✅" if ok else ("—" if ok is None else "❌")
                print(f"      {mark} {name}: {info}")

            results[key_of(m)] = {
                "model": m,
                "platform": "openrouter",
                "chat": res["chat"],
                "tools": res["tools"],
                "vision": res["vision"],
                "declared": {
                    "tools": (declared.get(m) or {}).get("tools"),
                    "vision": (declared.get(m) or {}).get("vision"),
                },
                "verified_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            }

    # 合并进 verified.json（保留未重跑的历史记录）
    existing.update(results)
    vd_path.parent.mkdir(parents=True, exist_ok=True)
    vd_path.write_text(json.dumps(existing, ensure_ascii=False, indent=1), encoding="utf-8")

    # ------------------------------------------------------------ 汇总对照
    print("\n" + "=" * 78)
    print("声明 vs 实测 对照表")
    print("=" * 78)
    print(f"{'模型':<46} {'对话':<5} {'工具(声明/实测)':<16} {'图片(声明/实测)':<16}")
    print("-" * 78)

    issues = []
    for k in sorted(results):
        r = results[k]
        d = r.get("declared") or {}
        mid = r["model"]

        def fmt(declared_v, actual_v):
            if actual_v is None:
                return "—"
            dv = "?" if declared_v is None else ("Y" if declared_v else "N")
            av = "Y" if actual_v else "N"
            return f"{dv}/{av}"

        tool_s = fmt(d.get("tools"), r["tools"])
        vis_s = fmt(d.get("vision"), r["vision"])
        print(f"{mid[:45]:<46} {'Y' if r['chat'] else 'N':<5} {tool_s:<16} {vis_s:<16}")

        # 只对「平台声称支持、实测失败」的记问题（虚标）
        if d.get("tools") and not r["tools"]:
            issues.append((mid, "工具调用 声明支持但实测失败"))
        if d.get("vision") and r["vision"] is False:
            issues.append((mid, "图片输入 声明支持但实测失败"))

    if issues:
        print("\n⚠ 声明与实测不一致（虚标嫌疑）：")
        for mid, msg in issues:
            print(f"   · {mid} —— {msg}")
    else:
        print("\n✅ 所有「平台声明支持」的能力均实测通过，无虚标。")

    print(f"\n已写入 {vd_path.name}（累计 {len(existing)} 个模型）")


if __name__ == "__main__":
    main()
