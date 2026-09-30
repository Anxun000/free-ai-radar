# 免费 AI 模型雷达

一个单文件网页，随时告诉你**此刻哪些 AI 模型能免费用、怎么接进去、以及它现在还是不是真的免费**。

双击 `dist/免费AI模型雷达.html` 就能用 —— 无需联网、无需服务器、无需安装任何东西。

想直接和模型对话？双击 `dist/免费AI模型聊天.html`，填一次密钥就能聊，**不用写任何代码**。

---

## 两个成品

| 文件 | 用途 |
|---|---|
| `dist/免费AI模型雷达.html` | **找模型**。筛选、对比能力、看变更、复制接入代码 |
| `dist/免费AI模型聊天.html` | **用模型**。选一个模型直接对话，支持流式输出、显示思考过程 |

聊天页能成立，是因为 OpenRouter 的接口返回 `Access-Control-Allow-Origin: *`，
**允许浏览器跨域直连**（连 `file://` 的 `Origin: null` 也放行），所以不需要任何后端。
密钥只存在你自己浏览器的 localStorage 里，不会发给任何第三方。

> ⚠️ 只有 OpenRouter 支持浏览器直连。Gemini / Groq / 智谱 / LongCat / 商汤等平台的接口
> 不允许跨域，要在网页里用它们得配一个本地代理。需要的话可以再加。

---

## 为什么需要它

免费 AI 模型这个领域变化极快，网上的清单基本都是过期的：

- **GitHub Models** 已于 2026-07-30 彻底关停，但大量 2025 年的教程仍在推荐
- **Cerebras** 现在必须绑卡，**SambaNova** 免费层已取消
- **Groq** 免费档砍掉了 Llama 聊天模型

所以这个工具的核心不是"列清单"，而是**持续更新 + 可信度标注**。

## 它给你什么

| 能力 | 说明 |
|---|---|
| **9 维筛选** | 平台 / 是否需代理 / 是否需绑卡 / 模态 / 上下文 / 免费类型 / 工具调用 / 图片输入 / 推理 |
| **能力徽章** | 每个模型标注是否支持工具调用、图片输入、推理、结构化 JSON，以及视频/语音/联网搜索 |
| **可信度分级** | 能力数据标明来源：「平台声明」（接口）/「官方文档」（人工核对）/「未公开」 |
| **免费类型分级** | 🟢永久免费 · 🔵每月赠额 · 🟡限时免费 · 🟠注册赠送 · ⚫已下线 |
| **变更雷达** | 每天自动比对，标红「🆕新增 / ⛔消失 / ⚠️能力变化」 |
| **可调用性实测** | 真的发一次请求，标出哪些模型「✅ 可直接调用」，哪些「🔒 仅限 Agent 客户端」 |
| **一键复制** | 直接生成 OpenAI 兼容的接入代码，粘进项目就能跑 |
| **防坑黑名单** | 专门列出已下线/不再免费的平台，避免白折腾 |

## 目录结构

```
free-ai-radar/
├── 密钥填写.txt              ← 在这里填 API Key（已被 .gitignore 忽略）
├── .env.example              ← 空模板（可提交，给协作者看格式）
├── .gitignore                ← 密钥防线
├── collector/
│   ├── registry.py           ← 平台元数据（人工维护：额度/限速/绑卡/入口）
│   ├── collect.py            ← 采集器：抓取 → 归一化 → 存快照 → 算变更
│   └── probe_callable.py     ← 可调用性探针：真的发请求，识别「仅限 Agent 客户端」
├── tools/
│   ├── check_keys.py         ← 密钥连通性自检（只输出状态，不打印密钥）
│   └── verify_model.py       ← 单模型实测：对话 / 工具调用 / 图片输入
├── build.py                  ← 把 data.json 内嵌成两个单文件 HTML
├── templates/
│   └── chat.html             ← 聊天页模板
├── data/
│   ├── data.json             ← 当前数据
│   ├── callable.json         ← 可调用性实测结果
│   └── snapshots/*.json      ← 每日快照（变更雷达的基准）
├── dist/
│   ├── 免费AI模型雷达.html    ← ★ 找模型
│   └── 免费AI模型聊天.html    ← ★ 用模型（双击即聊）
└── .github/workflows/daily.yml  ← 每天自动抓取并提交
```

## 日常使用

```bash
# 1. 验证密钥是否可用（可选，只输出状态）
python tools/check_keys.py

# 2. 抓取最新数据
python collector/collect.py

# 3. 重新生成网页
python build.py

# 4. 打开（Windows）
start dist/免费AI模型雷达.html
```

### 可选：实测某个模型到底能不能用

```bash
python examples/quickstart.py                                  # 默认模型
python examples/quickstart.py stealth/space-bunny-alpha        # 指定模型
python examples/quickstart.py <模型ID> "你想问的问题"
```

### 可选：逐项实测能力（对话 / 工具调用 / 图片输入）

```bash
python tools/verify_model.py stealth/space-bunny-alpha
```

会真的发三次请求，然后把结果写入 `data/verified.json`，
重新 `python build.py` 后，卡片上就会出现「**逐项实测 3/3**」徽章。

这三层可信度是叠加的：

| 徽章 | 含义 | 怎么来的 |
|---|---|---|
| 能力来源：平台声明 | 平台接口自己说的 | 自动抓取 |
| 逐项实测 N/3 | 我真的调通了这几项 | `tools/verify_model.py` |
| ✅ 实测可调用 | 真的能通过 API 调通 | `collector/probe_callable.py` |

### 可选：扫描免费模型的可调用性

```bash
python collector/probe_callable.py
```

⚠️ **这个脚本会消耗 API 额度**（每个免费模型一次请求）。
OpenRouter 免费档是 50 请求/日，扫 20 个模型就占掉一大半，
**不要放进每日自动化**，手动按需跑即可。

## 一个重要发现：声明 ≠ 可用

OpenRouter 上有一类免费模型**被限制为只能在 Agent 客户端内使用**。
它们的 `supported_parameters` 一切正常（工具调用、图片输入、推理全都是 ✅），
但用普通 API 调用会直接返回：

```
403 thinkingmachines/inkling-small:free is only available on agentic harnesses.
    Try plugging it into a coding agent or productivity app listed on ...
```

实测下来，20 个免费模型里有 **2 个**属于这种情况。
所以本工具把「可调用性」单独做成一个维度和徽章——**光看能力声明会踩坑**。

## 安全说明

- **密钥永不落地到成品**。最终 HTML 是纯静态的，已验证零密钥混入。
- 密钥文件 `密钥填写.txt` 已被 `.gitignore` 忽略，忽略规则经过实测验证。
- 密钥只被 `collector/` 与 `tools/` 下的脚本在本地临时使用。
- 也支持从**环境变量**读取密钥（环境变量优先），便于在 CI 中用 Secrets 注入。

## 放到 GitHub 上自动跑

1. 把本目录推到一个仓库
2. 在 `Settings → Secrets and variables → Actions` 里添加各平台的密钥（名字与 `.env.example` 里一致）
3. `.github/workflows/daily.yml` 会在**每天北京时间 09:00** 自动抓取、重建网页并提交

> GitHub Actions 对 **public 仓库完全免费无限量**；private 仓库每月 2000 分钟免费额度，
> 本任务每次仅需几十秒，用量可忽略。

## 维护平台清单

要新增/修改平台的免费额度、限速、入口链接，编辑 `collector/registry.py`。
只维护**接口拿不到的信息**——能自动抓到的（如模型列表、能力字段）不用手写。

修改任何平台的免费政策后，请同步更新该条目的 `verified` 日期。
