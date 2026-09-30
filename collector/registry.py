# -*- coding: utf-8 -*-
"""
平台元数据注册表
=========================================================
这里放【接口拿不到、必须人工维护】的信息：
免费额度、限速、是否需绑卡、是否需代理、申请入口、免费类型分级、能力兜底。

接口能自动拿到的能力字段（如 OpenRouter 的 supported_parameters）优先级更高，
本文件只在接口缺失时兜底。

维护约定：改动任一平台的免费政策后，请同步更新 verified 日期。
"""
from datetime import date

TODAY = date.today().isoformat()

# 免费类型分级
PERMANENT = "permanent"   # 🟢 永久免费（有速率限制）
MONTHLY = "monthly"       # 🔵 每月赠额
LIMITED = "limited"       # 🟡 限时免费
SIGNUP = "signup"         # 🟠 注册赠送
OFFLINE = "offline"       # ⚫ 已下线

PLATFORMS = {
    "openrouter": {
        "label": "OpenRouter",
        "kind": PERMANENT,
        "region": "国际",
        "needs_vpn": True,
        "needs_card": False,
        "base_url": "https://openrouter.ai/api/v1",
        "signup_url": "https://openrouter.ai/keys",
        "quota": "20 请求/分；50 请求/日（一次性充 $10 后升至 1000/日）",
        "note": "单 key 聚合 20 个月费为 0 的模型，另有 openrouter/free 路由自动挑选可用免费模型",
        "key_env": "OPENROUTER_API_KEY",
        "probe": "https://openrouter.ai/api/v1/models",
        "api_gives": "full",   # 接口自带完整能力字段
        "verified": TODAY,
    },
    "gemini": {
        "label": "Google AI Studio",
        "kind": PERMANENT,
        "region": "国际",
        "needs_vpn": True,
        "needs_card": False,
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "signup_url": "https://aistudio.google.com/apikey",
        "quota": "免费档限速官方不公布，在 AI Studio 内按项目显示",
        "note": "免绑卡。注意：免费档的数据可能被用于改进产品（欧洲经济区/英国/瑞士除外）",
        "key_env": "GEMINI_API_KEY",
        "probe": "https://generativelanguage.googleapis.com/v1beta/models",
        "api_gives": "partial",
        "verified": TODAY,
    },
    "groq": {
        "label": "Groq",
        "kind": PERMANENT,
        "region": "国际",
        "needs_vpn": True,
        "needs_card": False,
        "base_url": "https://api.groq.com/openai/v1",
        "signup_url": "https://console.groq.com/keys",
        "quota": "30 请求/分；1000 请求/日；8K tokens/分；20 万 tokens/日（每模型）",
        "note": "推理速度最快的免费档之一。默认不保留数据，可开启零数据保留",
        "key_env": "GROQ_API_KEY",
        "probe": "https://api.groq.com/openai/v1/models",
        "api_gives": "partial",
        "verified": TODAY,
    },
    "nvidia": {
        "label": "NVIDIA NIM",
        "kind": PERMANENT,
        "region": "国际",
        "needs_vpn": True,
        "needs_card": False,
        "base_url": "https://integrate.api.nvidia.com/v1",
        "signup_url": "https://build.nvidia.com/",
        "quota": "约 40 请求/分（官方未公布确切数值）",
        "note": "托管大量开源模型。注册需手机号验证。会话内容不存储",
        "key_env": "NVIDIA_API_KEY",
        "probe": "https://integrate.api.nvidia.com/v1/models",
        "api_gives": "minimal",
        "verified": TODAY,
    },
    "zhipu": {
        "label": "智谱 BigModel",
        "kind": PERMANENT,
        "region": "国内",
        "needs_vpn": False,
        "needs_card": False,
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "signup_url": "https://open.bigmodel.cn/",
        "quota": "GLM-Flash 系列计费 ¥0；其余模型按量计费",
        "note": "国内直连。GLM 的 Flash 系列是长期免费的轻量档",
        "key_env": "ZHIPU_API_KEY",
        "probe": "https://open.bigmodel.cn/api/paas/v4/models",
        "api_gives": "minimal",
        "verified": TODAY,
    },
    "longcat": {
        "label": "美团 LongCat",
        "kind": SIGNUP,
        "region": "国内",
        "needs_vpn": False,
        "needs_card": False,
        "base_url": "https://api.longcat.chat/openai/v1",
        "signup_url": "https://longcat.chat/platform",
        "quota": "注册赠 500 万 tokens（LongCat-2.5-Preview 上线时对现有用户发放）",
        "note": "国内直连。LongCat-2.5-Preview：1.6T 总参 / 约 48B 激活 / 1M 上下文 / 原生多模态，强化 Coding",
        "key_env": "LONGCAT_API_KEY",
        "probe": "https://api.longcat.chat/openai/v1/models",
        "api_gives": "partial",
        "verified": TODAY,
    },
    "sensenova": {
        "label": "商汤日日新",
        "kind": LIMITED,
        "region": "国内",
        "needs_vpn": False,
        "needs_card": False,
        "base_url": "https://token.sensenova.cn/v1",
        "signup_url": "https://platform.sensenova.cn/console/keys",
        "quota": "公测期全免费；滚动 5 小时通用积分 6 万、周额度 60 万；Flash-Lite 约 1500 次/5小时",
        "note": "国内直连。同时提供 OpenAI 兼容端点与 Anthropic Messages 兼容端点（/v1/messages）",
        "key_env": "SENSENOVA_API_KEY",
        "probe": "https://token.sensenova.cn/v1/models",
        "api_gives": "full",
        "verified": TODAY,
    },
    "agnes": {
        "label": "Agnes AI",
        "kind": PERMANENT,
        "region": "国内",
        "needs_vpn": False,
        "needs_card": False,
        "base_url": "https://apihub.agnes-ai.com/v1",
        "signup_url": "https://apihub.agnes-ai.com/",
        "quota": "永久免费，20 请求/分",
        "note": "国内直连。含文本、图像、视频生成模型",
        "key_env": "AGNES_API_KEY",
        "probe": "https://apihub.agnes-ai.com/v1/models",
        "api_gives": "minimal",
        "verified": TODAY,
    },
    # ── 未配置 key，仅按官方文档列入 ─────────────────────────
    "cloudflare": {
        "label": "Cloudflare Workers AI",
        "kind": PERMANENT,
        "region": "国际",
        "needs_vpn": True,
        "needs_card": False,
        "base_url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
        "signup_url": "https://dash.cloudflare.com/profile/api-tokens",
        "quota": "10,000 Neurons/日；300 请求/分；UTC 0 点重置",
        "note": "需要 account_id + API Token 两个值配套。数据不用于训练",
        "key_env": "CLOUDFLARE_API_TOKEN",
        "probe": None,
        "api_gives": "minimal",
        "verified": TODAY,
        "configured": False,
    },
    "mistral": {
        "label": "Mistral",
        "kind": MONTHLY,
        "region": "国际",
        "needs_vpn": True,
        "needs_card": False,
        "base_url": "https://api.mistral.ai/v1",
        "signup_url": "https://console.mistral.ai/",
        "quota": "每月 $10 API 额度（Experiment 免费档）",
        "note": "默认用你的数据训练模型，可在后台关闭",
        "key_env": "MISTRAL_API_KEY",
        "probe": "https://api.mistral.ai/v1/models",
        "api_gives": "minimal",
        "verified": TODAY,
        "configured": False,
    },
    "cohere": {
        "label": "Cohere",
        "kind": MONTHLY,
        "region": "国际",
        "needs_vpn": True,
        "needs_card": False,
        "base_url": "https://api.cohere.com/v1",
        "signup_url": "https://dashboard.cohere.com/api-keys",
        "quota": "trial key：20 请求/分；约 1000 次/月",
        "note": "仅限开发/评估用途",
        "key_env": "COHERE_API_KEY",
        "probe": "https://api.cohere.com/v1/models",
        "api_gives": "minimal",
        "verified": TODAY,
        "configured": False,
    },
    "huggingface": {
        "label": "Hugging Face",
        "kind": PERMANENT,
        "region": "国际",
        "needs_vpn": True,
        "needs_card": False,
        "base_url": "https://router.huggingface.co/v1",
        "signup_url": "https://huggingface.co/settings/tokens",
        "quota": "$0.10/月 推理额度（PRO 用户 $2/月）",
        "note": "聚合 200+ 模型的推理服务，额度很小，适合偶尔试",
        "key_env": "HUGGINGFACE_API_KEY",
        "probe": "https://huggingface.co/api/whoami-v2",
        "api_gives": "minimal",
        "verified": TODAY,
        "configured": False,
    },
}

# ── 已下线 / 不再免费：专门列出来防踩坑 ─────────────────────
OFFLINE_BLACKLIST = [
    {
        "label": "GitHub Models",
        "kind": OFFLINE,
        "what": "2026-07-30 已彻底关停",
        "detail": "模型目录与推理 API 全部失效。网上大量 2025 年的教程仍在推荐它，请忽略。",
        "source": "https://docs.github.com/",
    },
    {
        "label": "SambaNova Cloud",
        "kind": OFFLINE,
        "what": "免费层已取消",
        "detail": "2026 年内已停掉免费额度，需付费。",
        "source": "https://cloud.sambanova.ai/",
    },
    {
        "label": "Cerebras",
        "kind": OFFLINE,
        "what": "现在必须绑卡",
        "detail": "仅提供 $5 试用额度，30 天过期，且限速 5 请求/分。已不再是免绑卡免费档。",
        "source": "https://cloud.cerebras.ai/",
    },
    {
        "label": "Together AI",
        "kind": OFFLINE,
        "what": "$5 起充",
        "detail": "不再提供免费额度，最低充值 $5。",
        "source": "https://api.together.ai/",
    },
    {
        "label": "Vercel AI Gateway",
        "kind": OFFLINE,
        "what": "需要绑卡",
        "detail": "宣传为有赠送额度，但实际要求绑定支付方式。",
        "source": "https://vercel.com/ai-gateway",
    },
]

# ── 接口拿不到能力字段的平台：人工兜底 ─────────────────────
# 只收录值得标注的模型；未收录的一律标为「未公开」，不猜。
# feat: t=工具调用 v=图片输入 r=推理 j=结构化JSON a=语音 vd=视频 ws=联网
MODEL_NOTES = {
    "gemini": {
        "_default": {"caps": {"vision": True}, "source": "doc"},
        "gemini-3.5-flash": {"caps": {"tools": True, "vision": True, "reasoning": True, "json": True}, "source": "doc"},
        "gemini-3.6-flash": {"caps": {"tools": True, "vision": True, "reasoning": True, "json": True}, "source": "doc"},
        "gemini-3.8-flash": {"caps": {"tools": True, "vision": True, "reasoning": True, "json": True}, "source": "doc"},
        "gemini-3.7-flash": {"caps": {"tools": True, "vision": True, "reasoning": True, "json": True}, "source": "doc"},
        "gemma-4": {"caps": {"vision": True}, "source": "doc"},
    },
    "longcat": {
        "LongCat-2.5-Preview": {"caps": {"tools": True, "vision": True, "reasoning": True}, "source": "doc"},
        "LongCat-2.0": {"caps": {"tools": True, "reasoning": True}, "source": "doc"},
    },
    "zhipu": {
        "_default": {"caps": {}, "source": "doc"},
        "glm-5.3-flash": {"caps": {"tools": True, "reasoning": True, "json": True}, "source": "doc"},
        "glm-5.3-flashx": {"caps": {"tools": True, "reasoning": True, "json": True}, "source": "doc"},
        "glm-5.3": {"caps": {"tools": True, "reasoning": True, "json": True}, "source": "doc"},
        "glm-4-flash": {"caps": {}, "source": "doc"},
    },
    "agnes": {
        "_default": {"caps": {}, "source": "doc"},
        "agnes-2.0-flash": {"caps": {"tools": True}, "source": "doc"},
    },
    "nvidia": {
        "_default": {"caps": {}, "source": "doc"},
    },
}
