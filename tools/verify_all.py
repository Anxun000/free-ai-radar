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
_budget_out = threading.Event()   # 疑似撞到当日额度上限时置位，后续请求不再重试

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
    """跑一项测试；遇「未测出」（上游限流等）自动退避重试。"""
    if _budget_out.is_set():
        retries = 0          # 已经判断额度耗尽，不再白等
    status, info = "unknown", ""
    for attempt in range(retries + 1):
        status, info = fn(base, key, model)
        if status == "unknown" and attempt < retries:
            _global_backoff(backoff)
            continue
        return status, info
    return status, info


def run_three(model: str, base: str, key: str, do_vision=True):
    """跑完三项，返回 (三态结果, 展示用明细)。"""
    detail, res = [], {}

    for cn, en, fn in (("基础对话", "chat", vm.test_chat),
                       ("工具调用", "tools", vm.test_tools)):
        s, info = _run_one(fn, base, key, model)
        detail.append((cn, s, info))
        res[en] = s

    if do_vision:
        s, info = _run_one(vm.test_vision, base, key, model)
        detail.append(("图片输入", s, info))
        res["vision"] = s
    else:
        detail.append(("图片输入", None, "已跳过"))
        res["vision"] = None

    return res, detail


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--redo", action="store_true", help="忽略已有结果，全部重跑")
    ap.add_argument("--only", default=None, help="只测指定模型 ID")
    ap.add_argument("--workers", type=int, default=4, help="并发数")
    ap.add_argument("--interval", type=float, default=3.5, help="请求最小间隔（秒）")
    ap.add_argument("--skip-vision", action="store_true", help="跳过图片输入测试")
    ap.add_argument("--limit", type=int, default=0,
                    help="本次最多测几个模型（0 = 不限）。用于分摊每日额度，见 README")
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

    # 优先补测「没有结果」或「有项未测出」的模型，把已测全的排到最后。
    # 配合 --limit，就能把全量实测摊到几天里跑完，不会一次性撞爆每日额度。
    def incomplete(m):
        r = existing.get(key_of(m))
        if not r:
            return True
        t = r.get("tested") or {}
        return not all(t.get(k) for k in ("chat", "tools", "vision"))

    todo.sort(key=lambda m: (not incomplete(m), m))
    if args.limit > 0:
        todo = todo[:args.limit]

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
    consecutive = [0]

    def work(m):
        res, detail = run_three(m, base, key, do_vision=do_vision)
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
            n_tested = sum(1 for _, s, _ in detail if s in ("yes", "no"))
            n_ok = sum(1 for _, s, _ in detail if s == "yes")
            print(f"\n[{done[0]}/{len(todo)}] {m}   →  {n_ok}/{n_tested} 通过")
            for name, s, info in detail:
                print(f"      {vm.MARK.get(s, '— 已跳过')} {name}: {info}")

            results[key_of(m)] = {
                "model": m,
                "platform": "openrouter",
                "chat": res["chat"] == "yes",
                "tools": res["tools"] == "yes",
                "vision": res["vision"] == "yes",
                "tested": {
                    "chat": res["chat"] in ("yes", "no"),
                    "tools": res["tools"] in ("yes", "no"),
                    "vision": res["vision"] in ("yes", "no"),
                },
                "declared": {
                    "tools": (declared.get(m) or {}).get("tools"),
                    "vision": (declared.get(m) or {}).get("vision"),
                },
                "verified_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            }

            # 连续多个模型连「基础对话」都测不出来，基本可断定是撞到当日额度上限了
            if res.get("chat") == "unknown" and res.get("tools") == "unknown":
                consecutive[0] += 1
                if consecutive[0] >= 3 and not _budget_out.is_set():
                    _budget_out.set()
                    print("\n  ⚠ 连续 3 个模型均未测出，疑似已达当日额度上限。")
                    print("     后续模型不再重试；本次没测到的，下次运行会自动优先补测。")
            else:
                consecutive[0] = 0

    # 合并进 verified.json（保留未重跑的历史记录）
    existing.update(results)
    vd_path.parent.mkdir(parents=True, exist_ok=True)
    vd_path.write_text(json.dumps(existing, ensure_ascii=False, indent=1), encoding="utf-8")

    # ------------------------------------------------------------ 汇总对照
    print("\n" + "=" * 78)
    print("声明 vs 实测 对照表")
    print("=" * 78)
    print(f"{'模型':<43} {'对话':<7} {'工具(声明/实测)':<17} {'图片(声明/实测)':<17}")
    print("-" * 86)

    issues = []
    not_done = []
    for k in sorted(results):
        r = results[k]
        d = r.get("declared") or {}
        t = r.get("tested") or {}
        mid = r["model"]

        def cell(declared_v, actual_v, was_tested):
            if not was_tested:
                return "未测出"
            dv = "?" if declared_v is None else ("Y" if declared_v else "N")
            av = "Y" if actual_v else "N"
            return f"{dv}/{av}"

        chat_s = "Y" if r["chat"] else ("N" if t.get("chat") else "未测出")
        tool_s = cell(d.get("tools"), r["tools"], t.get("tools"))
        vis_s = cell(d.get("vision"), r["vision"], t.get("vision"))
        print(f"{mid[:42]:<43} {chat_s:<7} {tool_s:<17} {vis_s:<17}")

        # 只对「平台声称支持 + 确实测出来了 + 但失败」判定为虚标
        if d.get("tools") and t.get("tools") and not r["tools"]:
            issues.append((mid, "工具调用 —— 声明支持，实测不支持"))
        if d.get("vision") and t.get("vision") and not r["vision"]:
            issues.append((mid, "图片输入 —— 声明支持，实测不支持"))

        if not all(t.get(x) for x in ("chat", "tools", "vision")):
            not_done.append(mid)

    print("\n注：单元格 = 平台声明/实测结果；Y=支持 N=不支持 ?=未声明")

    if issues:
        print("\n⚠ 声明与实测不一致（虚标，共 %d 条）：" % len(issues))
        for mid, msg in issues:
            print(f"   · {mid} —— {msg}")
    else:
        print("\n✅ 所有「平台声明支持」的能力均实测通过，无虚标。")

    if not_done:
        print("\nℹ 部分项未能测出（多为上游限流，非模型问题）：")
        for mid in not_done:
            print(f"   · {mid}")

    print(f"\n已写入 {vd_path.name}（累计 {len(existing)} 个模型）")


if __name__ == "__main__":
    main()
