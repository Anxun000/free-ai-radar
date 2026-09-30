# -*- coding: utf-8 -*-
"""
构建脚本
=========================================================
把 data/data.json 内嵌进单文件 HTML。
产出：dist/免费AI模型雷达.html —— 双击即用，离线可看，零依赖。

用法：
  python build.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "data" / "data.json"
OUT_DIR = ROOT / "dist"
OUT = OUT_DIR / "免费AI模型雷达.html"

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>免费 AI 模型雷达</title>
<style>
:root{
  --bg:#fbfbf9; --card:#fff; --line:#e7e5de; --line2:#d5d2c8;
  --tx:#22211e; --tx2:#6b6960; --tx3:#96938a;
  --acc:#185fa5; --acc-bg:#e6f1fb;
  --ok:#0f6e56; --ok-bg:#e1f5ee;
  --warn:#854f0b; --warn-bg:#faeeda;
  --danger:#a32d2d; --danger-bg:#fcebeb;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--bg); color:var(--tx);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
  font-size:14px; line-height:1.6;
}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
.hdr{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap}
a.golink{display:inline-block;background:var(--acc);color:#fff;text-decoration:none;
  padding:9px 18px;border-radius:10px;font-size:13.5px;white-space:nowrap}
a.golink:hover{opacity:.9}
h1{font-size:22px;font-weight:600;margin:0 0 4px}
.sub{color:var(--tx2);font-size:13px}
.stats{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 6px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;min-width:96px}
.stat b{display:block;font-size:19px;font-weight:600;line-height:1.2}
.stat span{color:var(--tx2);font-size:12px}

.radar{margin:16px 0;border:1px solid var(--line2);border-radius:12px;background:var(--warn-bg);padding:14px 16px}
.radar h2{font-size:14px;margin:0 0 8px;font-weight:600;color:var(--warn)}
.radar.bl{background:#f1efe8}
.radar.bl h2{color:var(--tx2)}
.radar .row{font-size:13px;margin:3px 0}
.tag{display:inline-block;padding:1px 7px;border-radius:5px;font-size:12px;margin-right:6px;font-weight:500}
.t-add{background:var(--ok-bg);color:var(--ok)}
.t-rm{background:var(--danger-bg);color:var(--danger)}
.t-ch{background:var(--acc-bg);color:var(--acc)}

.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:16px 0}
.fld{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 12px}
.fld:last-child{margin-bottom:0}
.fld>label{font-size:12px;color:var(--tx2);min-width:62px;flex:0 0 auto}
input[type=search],select{
  font:inherit;font-size:13px;padding:6px 10px;border:1px solid var(--line2);
  border-radius:8px;background:#fff;color:var(--tx);outline:none
}
input[type=search]{flex:1;min-width:180px}
input[type=search]:focus,select:focus{border-color:var(--acc)}
.chip{
  border:1px solid var(--line2);background:#fff;color:var(--tx2);
  padding:5px 11px;border-radius:999px;font-size:12.5px;cursor:pointer;user-select:none
}
.chip:hover{border-color:var(--tx3)}
.chip.on{background:var(--acc);border-color:var(--acc);color:#fff}
.chip.cap.on{background:var(--ok);border-color:var(--ok)}
.chip .n{opacity:.7;font-size:11px;margin-left:4px}

.list{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px;margin-top:4px}
.m{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 15px;display:flex;flex-direction:column}
.m:hover{border-color:var(--line2)}
.m .top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.m .nm{font-size:14.5px;font-weight:600;margin:0 0 2px;line-height:1.35}
.m .id{font-family:ui-monospace,Consolas,monospace;font-size:11.5px;color:var(--tx3);word-break:break-all}
.m .plat{font-size:12px;color:var(--tx2);margin:7px 0 0}
.badges{display:flex;flex-wrap:wrap;gap:5px;margin:9px 0 0}
.b{font-size:11.5px;padding:2px 7px;border-radius:5px;background:#f1efe8;color:var(--tx2);white-space:nowrap}
.b.on{background:var(--ok-bg);color:var(--ok)}
.b.off{background:#f1efe8;color:var(--tx3);text-decoration:line-through;opacity:.75}
.b.k-permanent{background:var(--ok-bg);color:var(--ok)}
.b.k-monthly{background:var(--acc-bg);color:var(--acc)}
.b.k-limited{background:var(--warn-bg);color:var(--warn)}
.b.k-signup{background:#faece7;color:#993c1d}
.b.k-offline{background:#f1efe8;color:var(--tx3)}
.b.src{background:#eeedfe;color:#534ab7}
.b.c-ok{background:var(--ok-bg);color:var(--ok)}
.b.c-lock{background:var(--danger-bg);color:var(--danger)}
.b.c-warn{background:var(--warn-bg);color:var(--warn)}
.b.c-bad{background:var(--danger-bg);color:var(--danger)}
.m.locked{opacity:.72}
.m .why{font-size:12px;color:var(--danger);margin:8px 0 0;padding:7px 10px;
  background:var(--danger-bg);border-radius:7px;line-height:1.5}
button[disabled]{opacity:.5;cursor:not-allowed}
.meta{font-size:12px;color:var(--tx2);margin:9px 0 0;display:flex;flex-wrap:wrap;gap:10px}
.acts{display:flex;gap:7px;margin:12px 0 0;padding-top:11px;border-top:1px solid var(--line);margin-top:auto}
button{font:inherit;font-size:12.5px;padding:6px 12px;border-radius:8px;cursor:pointer;
  border:1px solid var(--line2);background:#fff;color:var(--tx)}
button:hover{border-color:var(--tx3)}
button.pri{background:var(--acc);border-color:var(--acc);color:#fff}
button.pri:hover{opacity:.9}
.empty{text-align:center;color:var(--tx2);padding:48px 0}
h3.sec{font-size:15px;margin:30px 0 10px;font-weight:600}
.off{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.off .it{padding:12px 16px;border-bottom:1px solid var(--line)}
.off .it:last-child{border-bottom:0}
.off .n{font-weight:600;font-size:13.5px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.off .d{color:var(--tx2);font-size:12.5px;margin-top:3px}
footer{margin-top:34px;padding-top:16px;border-top:1px solid var(--line);color:var(--tx3);font-size:12px}
.toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%) translateY(60px);
  background:#22211e;color:#fff;padding:9px 18px;border-radius:9px;font-size:13px;
  opacity:0;transition:all .2s;pointer-events:none;z-index:99}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;
  align-items:center;justify-content:center;z-index:200;padding:24px}
.modal.show{display:flex}
.mbox{background:var(--card);border:1px solid var(--line2);border-radius:14px;
  padding:18px;max-width:640px;width:100%}
.mhd{font-size:13.5px;margin:0 0 10px;color:var(--tx2);line-height:1.6}
.mbox textarea{width:100%;height:230px;font-family:ui-monospace,Consolas,monospace;
  font-size:12.5px;line-height:1.65;border:1px solid var(--line2);border-radius:9px;
  padding:11px;background:var(--bg);color:var(--tx);resize:vertical;box-sizing:border-box}
.mft{display:flex;gap:8px;margin-top:12px;justify-content:flex-end}
@media(prefers-color-scheme:dark){
  :root{--bg:#191918;--card:#232322;--line:#32322f;--line2:#46453f;--tx:#f1efe8;
        --tx2:#a8a59b;--tx3:#7d7a72;--acc:#85b7eb;--acc-bg:#0c447c;--ok:#5dcaa5;
        --ok-bg:#085041;--warn:#ef9f27;--warn-bg:#412402;--danger:#f09595;--danger-bg:#501313}
  input[type=search],select,button{background:#232322;color:var(--tx)}
  .b,.chip{background:#2c2c2a}
  .b.src{background:#3c3489;color:#cecbf6}
  .radar.bl{background:#2c2c2a}
  .toast{background:#f1efe8;color:#191918}
}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <div>
      <h1>免费 AI 模型雷达</h1>
      <div class="sub" id="sub"></div>
    </div>
    <a class="golink" href="%E5%85%8D%E8%B4%B9AI%E6%A8%A1%E5%9E%8B%E8%81%8A%E5%A4%A9.html">直接开聊 →</a>
  </div>
  <div class="stats" id="stats"></div>
  <div id="radar"></div>

  <div class="panel">
    <div class="fld">
      <label>搜索</label>
      <input type="search" id="q" placeholder="模型名或模型 ID，例如 qwen / gemma / longcat">
      <select id="sort">
        <option value="ctx">按上下文长度</option>
        <option value="name">按名称</option>
        <option value="plat">按平台</option>
      </select>
    </div>
    <div class="fld"><label>地区</label><span id="f-region"></span></div>
    <div class="fld"><label>平台</label><span id="f-plat"></span></div>
    <div class="fld"><label>能力</label><span id="f-cap"></span></div>
    <div class="fld"><label>免费类型</label><span id="f-kind"></span></div>
    <div class="fld"><label>可调用性</label><span id="f-call"></span></div>
    <div class="fld"><label>上下文</label><span id="f-ctx"></span>
      <span style="margin-left:auto;color:var(--tx2);font-size:12px" id="count"></span>
    </div>
  </div>

  <div class="list" id="list"></div>

  <h3 class="sec">已下线 / 不再免费（防踩坑）</h3>
  <div class="off" id="off"></div>

  <footer id="foot"></footer>
</div>
<div class="toast" id="toast"></div>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
const D = JSON.parse(document.getElementById('payload').textContent);
const CAPS = [["tools","工具调用"],["vision","图片输入"],["reasoning","推理"],["json","结构化 JSON"]];
const EXTRA = [["video","视频输入"],["audio","语音"],["websearch","联网搜索"]];
const KIND = {permanent:["🟢","永久免费"],monthly:["🔵","每月赠额"],limited:["🟡","限时免费"],
              signup:["🟠","注册赠送"],offline:["⚫","已下线"]};
const SRC = {api:["平台声明","src"],doc:["官方文档","src"],unknown:["未公开",""]};
const CALL = {
  callable:["✅","实测可调用","c-ok"],
  agentic_only:["🔒","仅限 Agent 客户端","c-lock"],
  congested:["⏳","实测限流中","c-warn"],
  not_chat:["🎵","非对话模型","c-warn"],
  error:["❌","实测失败","c-bad"],
  unprobed:["—","未实测",""]};

const st = {region:new Set(), plat:new Set(), cap:new Set(), kind:new Set(), call:new Set(), ctx:0, q:""};

function fmtCtx(n){ if(!n) return "未公开";
  if(n>=1000000) return (n/1000000).toFixed(1).replace(/\.0$/,"")+"M";
  return Math.round(n/1000)+"K"; }

/* 统计 */
(function(){
  const s=D.stats;
  document.getElementById('sub').textContent =
    `数据生成于 ${D.generated_at.replace('T',' ').slice(0,16)} · ` +
    `${s.platforms_ok} 个平台已采集 · 共 ${s.total_models} 个模型`;
  const items=[["模型总数",s.total_models],["支持工具调用",s.with_tools],
    ["支持图片输入",s.with_vision],["两者兼得",s.with_tools_and_vision],
    ["支持推理",s.with_reasoning],["结构化 JSON",s.with_json]];
  document.getElementById('stats').innerHTML =
    items.map(([k,v])=>`<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');
})();

/* 变更雷达 */
(function(){
  const el=document.getElementById('radar'), r=D.radar||{};
  if(r.baseline){
    el.innerHTML=`<div class="radar bl"><h2>变更雷达 · 已建立基准</h2>
      <div class="row">这是第一次采集，已存为基准快照。从明天起会自动比对出
      <b>新增 / 消失 / 能力变化</b>，并在这里标红提醒。</div></div>`;
    return;
  }
  const blk=(t,cls,arr,fmt)=> arr.length
    ? `<div class="row">${arr.map(a=>`<span class="tag ${cls}">${t}</span>${fmt(a)}`).join('<br>')}</div>` : "";
  const html = blk("新增","t-add",r.added,a=>`${a.platform} · ${a.name}`)
    + blk("消失","t-rm",r.removed,a=>`${a.platform} · ${a.name}`)
    + blk("变化","t-ch",r.changed,a=>`${a.platform} · ${a.name} — ${a.diffs.join("，")}`);
  el.innerHTML = html
    ? `<div class="radar"><h2>变更雷达 · 对比 ${D.prev_snapshot}</h2>${html}</div>`
    : `<div class="radar bl"><h2>变更雷达 · 对比 ${D.prev_snapshot}</h2>
       <div class="row">免费政策无变化。</div></div>`;
})();

/* 筛选器 */
function buildChips(host, values, set, cls, labelFn){
  host.innerHTML = values.map(v=>{
    const n = v.count!==undefined ? `<span class="n">${v.count}</span>` : "";
    return `<span class="chip ${cls||''}" data-v="${v.key}">${labelFn(v)}${n}</span>`;
  }).join(" ");
  host.querySelectorAll(".chip").forEach(c=>c.onclick=()=>{
    const v=c.dataset.v; set.has(v)?set.delete(v):set.add(v); c.classList.toggle("on"); render();
  });
}
(function(){
  const regs=[{key:"国内",label:"国内直连"},{key:"国际",label:"需代理"}];
  const rc={}; D.models.forEach(m=>rc[m.region]=(rc[m.region]||0)+1);
  buildChips(document.getElementById('f-region'),
    regs.map(r=>({...r,count:rc[r.key]||0})), st.region, "", v=>v.label);

  const pc={}; D.models.forEach(m=>pc[m.platform_label]=(pc[m.platform_label]||0)+1);
  buildChips(document.getElementById('f-plat'),
    Object.keys(pc).sort().map(k=>({key:k,count:pc[k]})), st.plat, "", v=>v.key);

  buildChips(document.getElementById('f-cap'),
    CAPS.map(([k,l])=>({key:k,label:l})), st.cap, "cap", v=>v.label);

  const kc={}; D.models.forEach(m=>kc[m.free_kind]=(kc[m.free_kind]||0)+1);
  buildChips(document.getElementById('f-kind'),
    Object.keys(kc).map(k=>({key:k,count:kc[k]})), st.kind, "", v=>KIND[v.key][1]);

  const cc={}; D.models.forEach(m=>{const c=m.callable||"unprobed"; cc[c]=(cc[c]||0)+1;});
  buildChips(document.getElementById('f-call'),
    ["callable","agentic_only","congested","not_chat","unprobed"]
      .filter(k=>cc[k]).map(k=>({key:k,count:cc[k]})), st.call, "", v=>CALL[v.key][1]);

  const ctxs=[[0,"不限"],[32768,"32K+"],[131072,"128K+"],[262144,"256K+"],[1048576,"1M"]];
  const host=document.getElementById('f-ctx');
  host.innerHTML=ctxs.map(([v,l])=>`<span class="chip${v===0?' on':''}" data-v="${v}">${l}</span>`).join(" ");
  host.querySelectorAll(".chip").forEach(c=>c.onclick=()=>{
    st.ctx=+c.dataset.v; host.querySelectorAll(".chip").forEach(x=>x.classList.remove("on"));
    c.classList.add("on"); render();
  });
})();

document.getElementById('q').oninput = e=>{ st.q=e.target.value.trim().toLowerCase(); render(); };
document.getElementById('sort').onchange = render;

/* 渲染 */
function render(){
  let arr = D.models.filter(m=>{
    if(st.region.size && !st.region.has(m.region)) return false;
    if(st.plat.size && !st.plat.has(m.platform_label)) return false;
    if(st.kind.size && !st.kind.has(m.free_kind)) return false;
    if(st.call.size && !st.call.has(m.callable||"unprobed")) return false;
    if(st.ctx && !(m.context>=st.ctx)) return false;
    for(const c of st.cap) if(!m.caps[c]) return false;
    if(st.q){
      const hay=(m.name+" "+m.id+" "+m.platform_label).toLowerCase();
      if(!hay.includes(st.q)) return false;
    }
    return true;
  });
  const sort=document.getElementById('sort').value;
  arr.sort((a,b)=> sort==="name" ? a.name.localeCompare(b.name)
    : sort==="plat" ? (a.platform_label.localeCompare(b.platform_label)||(b.context||0)-(a.context||0))
    : (b.context||0)-(a.context||0));

  document.getElementById('count').textContent = `显示 ${arr.length} / ${D.models.length} 个模型`;
  const L=document.getElementById('list');
  if(!arr.length){ L.innerHTML='<div class="empty">没有符合条件的模型，试着放宽筛选。</div>'; return; }

  L.innerHTML = arr.map((m,i)=>{
    const k=KIND[m.free_kind]||["",""];
    const cl=CALL[m.callable||"unprobed"]||CALL.unprobed;
    const blocked = ["agentic_only","not_chat","error"].includes(m.callable);
    const caps = CAPS.map(([c,l])=>`<span class="b ${m.caps[c]?'on':'off'}">${l}</span>`)
      .concat(EXTRA.filter(([c])=>m.caps[c]).map(([c,l])=>`<span class="b on">${l}</span>`))
      .join("");
    const sr=SRC[m.cap_source]||SRC.unknown;
    return `<div class="m${blocked?' locked':''}">
      <div class="top">
        <div style="min-width:0">
          <div class="nm">${esc(m.name)}</div>
          <div class="id">${esc(m.id)}</div>
        </div>
      </div>
      <div class="plat">${esc(m.platform_label)} · ${m.region==="国内"?"国内直连":"需代理"}</div>
      <div class="badges">
        <span class="b k-${m.free_kind}">${k[0]} ${k[1]}</span>
        <span class="b ${cl[2]}">${cl[0]} ${cl[1]}</span>
        ${m.verified?`<span class="b c-ok">逐项实测 ${[m.verified.chat,m.verified.tools,m.verified.vision].filter(Boolean).length}/3</span>`:""}
        <span class="b src">能力来源：${sr[0]}</span>
        ${m.needs_card?'<span class="b">需绑卡</span>':'<span class="b on">免绑卡</span>'}
      </div>
      <div class="badges">${caps}</div>
      <div class="meta">
        <span>上下文 <b>${fmtCtx(m.context)}</b></span>
        ${m.max_out?`<span>最大输出 ${fmtCtx(m.max_out)}</span>`:""}
      </div>
      ${blocked&&m.callable_note?`<div class="why">实测无法直接调用：${esc(m.callable_note.slice(0,220))}</div>`:""}
      <div class="acts">
        <button class="pri" data-copy="${i}" ${blocked?'disabled title="该模型无法直接调用，复制代码也跑不通"':""}>复制接入配置</button>
        <button data-open="${esc(m.signup_url)}">申请入口</button>
      </div>
    </div>`;
  }).join("");

  L.querySelectorAll("[data-copy]").forEach(b=>b.onclick=()=>{
    const m=arr[+b.dataset.copy];
    const code =
`from openai import OpenAI

client = OpenAI(
    base_url="${m.base_url}",
    api_key="在这里填你的 ${m.platform_label} Key",
)

resp = client.chat.completions.create(
    model="${m.id}",
    messages=[{"role": "user", "content": "你好"}],
)
print(resp.choices[0].message.content)`;
    copyText(code);
  });
  L.querySelectorAll("[data-open]").forEach(b=>b.onclick=()=>window.open(b.dataset.open,"_blank"));
}
function esc(s){ return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
function toast(t){
  const el=document.getElementById('toast'); el.textContent=t; el.classList.add('show');
  clearTimeout(el._t); el._t=setTimeout(()=>el.classList.remove('show'),1600);
}
/* 复制：file:// 下 navigator.clipboard 不可用，必须回退到 execCommand */
function legacyCopy(text){
  try{
    const ta=document.createElement('textarea');
    ta.value=text;
    ta.style.position='fixed'; ta.style.top='-2000px'; ta.style.opacity='0';
    document.body.appendChild(ta);
    ta.focus(); ta.select(); ta.setSelectionRange(0, text.length);
    const ok=document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  }catch(e){ return false; }
}
function copyText(text){
  const done=()=>toast("已复制，可以直接粘到代码里");
  const fallback=()=>legacyCopy(text)?done():showCopyModal(text);
  if(navigator.clipboard && window.isSecureContext){
    navigator.clipboard.writeText(text).then(done).catch(fallback);
  }else{
    fallback();
  }
}
function showCopyModal(text){
  let m=document.getElementById('copyModal');
  if(!m){
    m=document.createElement('div');
    m.id='copyModal'; m.className='modal';
    m.innerHTML='<div class="mbox">'
      +'<div class="mhd">浏览器拦住了自动复制。代码已全选好，直接按 <b>Ctrl+C</b>（Mac 按 ⌘C）即可复制。</div>'
      +'<textarea id="copyArea" readonly spellcheck="false"></textarea>'
      +'<div class="mft"><button class="pri" id="mclose">知道了</button></div></div>';
    document.body.appendChild(m);
    m.querySelector('#mclose').onclick=()=>m.classList.remove('show');
    m.onclick=e=>{ if(e.target===m) m.classList.remove('show'); };
  }
  const ta=m.querySelector('#copyArea');
  ta.value=text;
  m.classList.add('show');
  ta.focus(); ta.select();
}

/* 黑名单 */
document.getElementById('off').innerHTML = D.offline_blacklist.map(o=>
  `<div class="it"><div class="n">⚫ ${esc(o.label)}
     <span class="b k-offline">${esc(o.what)}</span></div>
   <div class="d">${esc(o.detail)}</div></div>`).join('');

/* 页脚 */
(function(){
  const err = (D.errors&&D.errors.length)
    ? `<br>采集失败的平台：${D.errors.map(esc).join("；")}` : "";
  const cm = D.callable_meta||{};
  const cml = (cm.probed_at)
    ? `<br><b>可调用性</b>为真实调用探测结果（${esc(cm.probed_at.slice(0,16).replace('T',' '))}）：
       对每个免费模型实际发一次请求。标记「仅限 Agent 客户端」的模型虽然声明支持全部能力，
       但 OpenRouter 限制其只能在第三方 Agent 应用内使用，<b>无法通过普通 API 调用</b>。
       未实测的模型显示「未实测」（其他平台未做逐个探测）。`
    : "";
  document.getElementById('foot').innerHTML =
    `数据来源：OpenRouter / Hugging Face / GitHub 公开接口 + 各平台官方文档人工核对。
     能力字段中「平台声明」来自接口，「官方文档」为人工核对，「未公开」表示该平台未提供该信息。${cml}<br>
     生成时间：${esc(D.generated_at)} · 快照 ${esc(D.generated_date)} · 本页为单文件离线版，不发送任何数据${err}`;
})();

render();
</script>
</body>
</html>
"""


def main():
    if not SRC.exists():
        raise SystemExit(f"找不到 {SRC}，请先运行 python collector/collect.py")
    payload = json.loads(SRC.read_text(encoding="utf-8"))

    # 合入「可调用性」实测结果（由 collector/probe_callable.py 产出）
    cp = ROOT / "data" / "callable.json"
    probed = 0
    if cp.exists():
        cl = json.loads(cp.read_text(encoding="utf-8"))
        res = cl.get("results", {})
        for m in payload["models"]:
            r = res.get(m["id"])
            if r:
                m["callable"] = r["verdict"]
                m["callable_note"] = r.get("message", "")
                probed += 1
    for m in payload["models"]:
        m.setdefault("callable", "unprobed")
    payload["callable_meta"] = {
        "probed_at": (cl.get("probed_at") if cp.exists() else None),
        "counts": (cl.get("counts") if cp.exists() else {}),
        "probed_models": probed,
    }

    # 合入「逐项能力实测」结果（由 tools/verify_model.py 产出）
    vp = ROOT / "data" / "verified.json"
    verified = 0
    if vp.exists():
        vd = json.loads(vp.read_text(encoding="utf-8"))
        for m in payload["models"]:
            r = vd.get(f'{m["platform"]}::{m["id"]}')
            if r:
                m["verified"] = r
                verified += 1
    payload["verified_count"] = verified

    raw = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__PAYLOAD__", raw)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")

    # 同时生成聊天页（双击即用，OpenRouter 允许浏览器直连）
    chat_tpl = ROOT / "templates" / "chat.html"
    chat_out = None
    if chat_tpl.exists():
        chat_out = OUT_DIR / "免费AI模型聊天.html"
        chat_out.write_text(
            chat_tpl.read_text(encoding="utf-8").replace("__PAYLOAD__", raw),
            encoding="utf-8")

    kb = len(html.encode("utf-8")) / 1024
    s = payload["stats"]
    print(f"已生成：{OUT}")
    print(f"  体积 {kb:.0f} KB · 内嵌 {s['total_models']} 个模型 · {s['platforms_ok']} 个平台")
    if probed:
        c = payload["callable_meta"]["counts"]
        print(f"  可调用性实测：{probed} 个模型 → "
              + " / ".join(f"{k} {v}" for k, v in c.items() if v))
    if chat_out:
        print(f"已生成：{chat_out}")
        print(f"  ★ 双击这个就能直接和免费模型聊天，不用写任何代码")
    print("  双击即可打开，无需联网、无需服务器。")


if __name__ == "__main__":
    main()
