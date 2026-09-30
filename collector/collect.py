# -*- coding: utf-8 -*-
"""
采集器
=========================================================
从各平台公开接口抓取模型清单，归一化为统一结构，产出：
  data/data.json               —— 当前数据
  data/snapshots/YYYY-MM-DD.json —— 每日快照（用于变更雷达 diff）

用法：
  python collector/collect.py

安全：密钥从「密钥填写.txt」读取，仅用于请求头，绝不写入任何输出文件。
"""
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "collector"))

from check_keys import load_keys, http, bearer, KEYFILE, UA  # noqa: E402
import registry as R  # noqa: E402

DATA_DIR = ROOT / "data"
SNAP_DIR = DATA_DIR / "snapshots"

CAP_KEYS = ("tools", "vision", "reasoning", "json", "audio", "video", "websearch")


def blank_caps():
    return {k: False for k in CAP_KEYS}


def merge_caps(base, extra):
    out = dict(base)
    for k, v in (extra or {}).items():
        if k in out and v:
            out[k] = True
    return out


def mk(platform, mid, name, context=None, max_out=None, caps=None,
       input_modalities=None, source="doc", extra=None):
    """构造一个归一化模型记录。"""
    return {
        "platform": platform,
        "id": mid,
        "name": name or mid,
        "context": context,
        "max_out": max_out,
        "caps": merge_caps(blank_caps(), caps),
        "input_modalities": input_modalities or [],
        "cap_source": source,          # api / doc / unknown
        **({"extra": extra} if extra else {}),
    }


# ── 各平台解析器 ────────────────────────────────────────────

def parse_openrouter(models):
    out = []
    for m in models:
        p = m.get("pricing") or {}
        if str(p.get("prompt")) != "0" or str(p.get("completion")) != "0":
            continue  # 只保留真正 0 价
        sp = m.get("supported_parameters") or []
        im = ((m.get("architecture") or {}).get("input_modalities")) or []
        caps = {
            "tools": "tools" in sp,
            "json": ("response_format" in sp) or ("structured_outputs" in sp),
            "reasoning": bool(m.get("reasoning")),
            "vision": "image" in im,
            "video": "video" in im,
            "audio": "audio" in im,
            "websearch": "web_search_options" in sp,
        }
        out.append(mk(
            "openrouter", m["id"], m.get("name"), m.get("context_length"),
            (m.get("top_provider") or {}).get("max_completion_tokens"),
            caps, im, "api",
            {"expiration": m.get("expiration_date"),
             "knowledge_cutoff": m.get("knowledge_cutoff"),
             "hf_id": m.get("hugging_face_id")},
        ))
    return out


def parse_gemini(models, notes):
    out = []
    for m in models:
        methods = m.get("supportedGenerationMethods") or []
        if "generateContent" not in methods:
            continue
        mid = m["name"].replace("models/", "")
        n = notes.get(mid) or notes.get("_default") or {}
        caps = dict(n.get("caps") or {})
        if m.get("thinking"):
            caps["reasoning"] = True
        im = ["text"] + (["image"] if caps.get("vision") else [])
        out.append(mk(
            "gemini", mid, m.get("displayName"), m.get("inputTokenLimit"),
            m.get("outputTokenLimit"), caps, im,
            n.get("source", "doc"),
        ))
    return out


def parse_openai_style(models, plat, notes, ctx_keys=("context_window", "context_length"),
                       out_keys=("max_completion_tokens", "max_output_tokens", "max_output_length")):
    """适用于 Groq / NVIDIA / 智谱 / LongCat / Agnes 这类 OpenAI 风格返回。"""
    out = []
    for m in models:
        mid = m.get("id")
        if not mid:
            continue
        ctx = next((m[k] for k in ctx_keys if m.get(k)), None)
        mx = next((m[k] for k in out_keys if m.get(k)), None)
        im = m.get("input_modalities") or []
        feats = m.get("supported_features") or []

        n = notes.get(mid) or notes.get("_default") or {}
        caps = dict(n.get("caps") or {})
        # 接口字段优先
        if feats:
            caps["tools"] = caps.get("tools") or ("tools" in feats)
            caps["json"] = caps.get("json") or ("json_mode" in feats)
            caps["reasoning"] = caps.get("reasoning") or ("reasoning" in feats)
        if im:
            caps["vision"] = caps.get("vision") or ("image" in im)
            caps["video"] = caps.get("video") or ("video" in im)
            caps["audio"] = caps.get("audio") or ("audio" in im)

        src = "api" if (feats or im) else n.get("source", "unknown")
        out.append(mk(plat, mid, m.get("name") or m.get("display_name") or mid,
                      ctx, mx, caps, im, src))
    return out


def parse_sensenova(models):
    out = []
    for m in models:
        feats = m.get("supported_features") or []
        im = m.get("input_modalities") or []
        p = m.get("pricing") or {}
        caps = {
            "tools": "tools" in feats,
            "json": "json_mode" in feats,
            "reasoning": "reasoning" in feats,
            "vision": "image" in im,
            "video": "video" in im,
            "audio": "audio" in im,
        }
        out.append(mk("sensenova", m["id"], m.get("name") or m["id"],
                      m.get("context_length"), m.get("max_output_length"),
                      caps, im, "api",
                      {"free_by_price": str(p.get("prompt")) == "0",
                       "quantization": m.get("quantization")}))
    return out


# ── 主流程 ─────────────────────────────────────────────────

FETCHERS = {
    "openrouter": lambda k, meta: parse_openrouter(
        json.loads(http(meta["probe"], {})[1]).get("data", [])),
    "gemini": lambda k, meta: parse_gemini(
        json.loads(http(f'{meta["probe"]}?key={k}', {})[1]).get("models", []),
        R.MODEL_NOTES.get("gemini", {})),
    "groq": lambda k, meta: parse_openai_style(
        json.loads(http(meta["probe"], bearer(k))[1]).get("data", []),
        "groq", R.MODEL_NOTES.get("groq", {})),
    "nvidia": lambda k, meta: parse_openai_style(
        json.loads(http(meta["probe"], bearer(k))[1]).get("data", []),
        "nvidia", R.MODEL_NOTES.get("nvidia", {})),
    "zhipu": lambda k, meta: parse_openai_style(
        json.loads(http(meta["probe"], bearer(k))[1]).get("data", []),
        "zhipu", R.MODEL_NOTES.get("zhipu", {})),
    "longcat": lambda k, meta: parse_openai_style(
        json.loads(http(meta["probe"], bearer(k))[1]).get("data", []),
        "longcat", R.MODEL_NOTES.get("longcat", {})),
    "sensenova": lambda k, meta: parse_sensenova(
        json.loads(http(meta["probe"], bearer(k))[1]).get("data", [])),
    "agnes": lambda k, meta: parse_openai_style(
        json.loads(http(meta["probe"], bearer(k))[1]).get("data", []),
        "agnes", R.MODEL_NOTES.get("agnes", {})),
    "mistral": lambda k, meta: parse_openai_style(
        json.loads(http(meta["probe"], bearer(k))[1]).get("data", []),
        "mistral", {}),
}


def fingerprint(rec):
    """用于 diff 的稳定指纹：只包含会变且有意义的字段。"""
    return hashlib.sha256(json.dumps(
        [rec["context"], rec["max_out"], rec["caps"]], sort_keys=True
    ).encode()).hexdigest()[:12]


def load_prev_snapshot():
    if not SNAP_DIR.exists():
        return None, None
    snaps = sorted(SNAP_DIR.glob("*.json"))
    if not snaps:
        return None, None
    p = snaps[-1]
    return p.stem, json.loads(p.read_text(encoding="utf-8"))


def build_radar(cur_models, prev):
    """变更雷达：新增 / 消失 / 能力或上下文变化。"""
    cur = {f'{m["platform"]}::{m["id"]}': m for m in cur_models}
    if not prev:
        return {"baseline": True, "added": [], "removed": [], "changed": []}
    old = {f'{m["platform"]}::{m["id"]}': m for m in prev.get("models", [])}

    added = [{"key": k, "name": v["name"], "platform": v["platform"]}
             for k, v in cur.items() if k not in old]
    removed = [{"key": k, "name": v["name"], "platform": v["platform"]}
               for k, v in old.items() if k not in cur]
    changed = []
    for k, v in cur.items():
        o = old.get(k)
        if not o:
            continue
        diffs = []
        if o.get("context") != v.get("context"):
            diffs.append(f'上下文 {o.get("context")} → {v.get("context")}')
        oc, vc = o.get("caps") or {}, v.get("caps") or {}
        for cap in CAP_KEYS:
            if bool(oc.get(cap)) != bool(vc.get(cap)):
                diffs.append(f'{cap} {"+" if vc.get(cap) else "-"}')
        if diffs:
            changed.append({"key": k, "name": v["name"],
                            "platform": v["platform"], "diffs": diffs})
    return {"baseline": False, "added": added, "removed": removed, "changed": changed}


def main():
    keys = load_keys(KEYFILE)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)

    all_models, plat_out, errors = [], {}, []

    for slug, meta in R.PLATFORMS.items():
        env = meta.get("key_env")
        configured = bool(keys.get(env)) and meta.get("probe")
        if slug == "cloudflare":
            configured = bool(keys.get("CLOUDFLARE_API_TOKEN")) and bool(
                keys.get("CLOUDFLARE_ACCOUNT_ID"))
        entry = {k: v for k, v in meta.items() if k != "probe"}
        entry["configured"] = configured

        if not configured or slug not in FETCHERS:
            entry["model_count"] = 0
            entry["fetch"] = "skipped"
            plat_out[slug] = entry
            print(f"  [跳过] {meta['label']}（{'未配置' if not configured else '无采集器'}）")
            continue

        try:
            recs = FETCHERS[slug](keys.get(env), meta)
            for r in recs:
                r["free_kind"] = meta["kind"]
                r["base_url"] = meta["base_url"]
                r["signup_url"] = meta["signup_url"]
                r["needs_card"] = meta["needs_card"]
                r["needs_vpn"] = meta["needs_vpn"]
                r["region"] = meta["region"]
                r["quota"] = meta["quota"]
                r["platform_label"] = meta["label"]
                r["fp"] = fingerprint(r)
            all_models.extend(recs)
            entry["model_count"] = len(recs)
            entry["fetch"] = "ok"
            print(f"  [成功] {meta['label']}: {len(recs)} 个模型")
        except Exception as e:
            entry["model_count"] = 0
            entry["fetch"] = "error"
            entry["error"] = f"{type(e).__name__}: {e}"
            errors.append(f"{meta['label']}: {e}")
            print(f"  [失败] {meta['label']}: {e}")
        plat_out[slug] = entry

    prev_date, prev = load_prev_snapshot()
    radar = build_radar(all_models, prev)

    payload = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generated_date": date.today().isoformat(),
        "prev_snapshot": prev_date,
        "stats": {
            "platforms_configured": sum(1 for v in plat_out.values() if v["configured"]),
            "platforms_ok": sum(1 for v in plat_out.values() if v.get("fetch") == "ok"),
            "total_models": len(all_models),
            "with_tools": sum(1 for m in all_models if m["caps"]["tools"]),
            "with_vision": sum(1 for m in all_models if m["caps"]["vision"]),
            "with_reasoning": sum(1 for m in all_models if m["caps"]["reasoning"]),
            "with_json": sum(1 for m in all_models if m["caps"]["json"]),
            "with_tools_and_vision": sum(
                1 for m in all_models if m["caps"]["tools"] and m["caps"]["vision"]),
        },
        "platforms": plat_out,
        "models": all_models,
        "radar": radar,
        "offline_blacklist": R.OFFLINE_BLACKLIST,
        "errors": errors,
    }

    (DATA_DIR / "data.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    snap = SNAP_DIR / f'{date.today().isoformat()}.json'
    snap.write_text(json.dumps(
        {"generated_date": payload["generated_date"], "models": all_models},
        ensure_ascii=False, indent=1), encoding="utf-8")

    s = payload["stats"]
    print()
    print(f'采集完成：{s["platforms_ok"]} 个平台 / {s["total_models"]} 个模型')
    print(f'  支持工具调用 {s["with_tools"]} · 支持图片输入 {s["with_vision"]} · '
          f'两者兼得 {s["with_tools_and_vision"]}')
    print(f'  快照：{snap.name}   基准快照：{prev_date or "无（首次采集）"}')
    r = radar
    if not r["baseline"]:
        print(f'  变更雷达：新增 {len(r["added"])} / 消失 {len(r["removed"])} / 变化 {len(r["changed"])}')
    print(f'  数据文件：{DATA_DIR / "data.json"}')


if __name__ == "__main__":
    main()
