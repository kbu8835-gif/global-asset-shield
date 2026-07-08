# Global Asset Shield Agent V4

AI Investment Immune System / AI 投资免疫系统

## 项目定位

Global Asset Shield Agent V4 不是 AI Analyst。它不是只告诉用户资产看起来怎么样，而是同时分析：

- 资产风险
- 用户情绪
- 认知偏差
- 行为后果
- 买入信念
- 后续复盘

分析师告诉用户：“可以买。”  
投资免疫系统告诉用户：“这里有毒。”

它的目标不是迎合交易冲动，而是在用户准备追涨、梭哈、听 KOL 喊单、补仓回本时，把风险说清楚，并把每一次决策保存成可复盘的投资日记。

## 为什么叫 AI Investment Immune System

免疫系统不负责让你兴奋，它负责识别有毒信号。  
这个 Agent 的核心工作也是这样：当用户被 FOMO、KOL、朋友推荐、暴富叙事或亏损厌恶驱动时，它会直接指出问题，给出 Don't Buy / Wait / Small Position 的明确决策。

## 和 AI Analyst 的区别

| AI Analyst | AI Investment Immune System |
| --- | --- |
| 重点分析资产 | 同时分析资产和用户行为 |
| 追求更多信息 | 追求阻止错误动作 |
| 常输出中性建议 | 必须给明确决策 |
| 关注收益逻辑 | 关注亏损、冲动和复盘 |
| 一次性报告 | 长期投资日记和复盘 |

## 功能列表

- Authentication：用户注册、登录、JWT、demo user fallback
- User Data Isolation：Journal、Notebook、DNA、KOL Profile、KOL Call 按用户隔离
- AI Risk Scan：Crypto 和股票风险扫描
- AI Emotion Scan：识别 FOMO、仓位冲动、KOL 驱动、沉没成本
- AI Bias Detector：识别 FOMO、Sunk Cost、Confirmation Bias、Authority Bias、Overconfidence、Revenge Trading、Lottery Bias
- AI Devil’s Advocate：强制唱反调，不迎合用户
- AI Regret Simulator：模拟四种后悔路径
- AI Conviction Score：判断用户有没有真正买入逻辑
- AI Investment Decision：输出 Don't Buy / Wait / Small Position
- AI Investment Journal：SQLite 保存每一次报告
- AI Review：对历史决策做复盘
- Investment DNA：统计最近 50 条投资日记，识别投资者行为模式
- AI Investment Notebook：把 Journal 升级为可编辑投资笔记，包含用户笔记、AI 分析、AI Coach、复盘和 Timeline
- KOL Intelligence V1：手动录入 KOL 和喊单，计算 ROI、Trust Score、KOL Dependency，并接入 DNA 和 Immune Report
- DeepSeek AI Coach：在规则版报告上增加 LLM 行为教练总结；API 失败、未配置 Key 或达到每日限额时自动回退到规则版
- KOL Mock 检测：本地 JSON 保存喊单记录

## 目录结构

```text
backend/
  app.py
  config.py
  database.py
  models.py
  schemas.py
  report.py
  scanner/
    crypto.py
    stock.py
    kol.py
  immune/
    risk.py
    emotion.py
    bias.py
    devil.py
    regret.py
    conviction.py
    decision.py
    journal.py
    review.py
    orchestrator.py
    llm.py
    kol_intelligence.py
    notebook.py
    dna.py
    coach.py
  data/
    investment_journal.db
    kol_records.json
  tests/
    test_health.py
    test_crypto.py
    test_stock.py
    test_immune_flow.py
    test_journal.py
    test_kol_intelligence.py
    test_notebook.py
    test_auth_isolation.py
  requirements.txt
  README.md
```

## 安装

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 启动

```bash
cd backend
source .venv/bin/activate
uvicorn app:app --reload --port 8010
```

打开：

- http://127.0.0.1:8010/
- http://127.0.0.1:8010/docs
- http://127.0.0.1:8010/health

## 部署

V1.0 Beta 支持 SQLite 本地开发和 PostgreSQL Docker 部署，通过 `DATABASE_URL` 控制。

本地默认：

```text
DATABASE_URL=sqlite:///./data/investment_journal.db
```

Docker 默认：

```text
DATABASE_URL=postgresql://gas_user:gas_password@db:5432/global_asset_shield
```

部署入口见根目录 [DEPLOYMENT.md](../DEPLOYMENT.md)。

上线前必须修改：

- `JWT_SECRET`
- `POSTGRES_PASSWORD`
- `DEMO_USER_PASSWORD`

可选 LLM 增强：

```text
LLM_ENABLED=true
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_BASE=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
LLM_DAILY_LIMIT=20
LLM_TIMEOUT_SECONDS=12
```

DeepSeek 只增强 `/immune/report` 的 `ai_coach` 字段，不接管最终投资决策。没有 API Key、调用失败或超过每日限额时，系统仍然返回完整规则版报告。

不要提交真实 `.env` 或 `.env.docker` 文件，只提交 `.env.example` 和 `.env.docker.example`。

## 测试

```bash
cd backend
source .venv/bin/activate
pytest
```

## API 示例

### Health

```bash
curl http://127.0.0.1:8010/
```

返回：

```json
{
  "name": "Global Asset Shield Agent",
  "version": "V4",
  "concept": "AI Investment Immune System",
  "status": "running"
}
```

### Crypto Scan

```bash
curl http://127.0.0.1:8010/scan/crypto/PEPE
```

外部数据失败时会自动 fallback 到 mock，不会让接口崩溃。

### Stock Scan

```bash
curl http://127.0.0.1:8010/scan/stock/NVDA
```

外部数据失败时会自动 fallback 到 mock。

### Immune Report

请求：

```bash
curl -X POST http://127.0.0.1:8010/immune/report \
  -H "Content-Type: application/json" \
  -d '{
    "asset": "PEPE",
    "asset_type": "crypto",
    "user_intent": "KOL推荐",
    "user_text": "这个币已经涨了40%，我怕踏空，想梭哈",
    "buy_reason": "看到KOL推荐，感觉马上要起飞",
    "risk_awareness": "不太清楚风险",
    "worst_case_plan": "跌了就再看看",
    "position_size": "50%",
    "horizon": "短线"
  }'
```

### Authentication

启动时会自动创建 demo user，并把旧数据归属给 demo user：

```text
email: demo@globalassetshield.ai
password: demo123456
username: Demo User
```

注册：

```bash
curl -X POST http://127.0.0.1:8010/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "test",
    "password": "12345678"
  }'
```

登录：

```bash
curl -X POST http://127.0.0.1:8010/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "12345678"
  }'
```

使用 JWT：

```bash
curl http://127.0.0.1:8010/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

需要隔离用户数据的 API 会读取 `Authorization: Bearer <token>`。开发兼容模式下，如果没有 token，会自动使用 demo user，不会让旧 Demo 崩溃。

已按用户隔离的数据：

- `/immune/report`
- `/journal`
- `/journal/{id}`
- `/journal/{id}/review`
- `/notebook`
- `/notebook/{id}`
- `/notebook/{id}/review`
- `/dna`
- `/kol/profiles`
- `/kol/calls`
- `/kol/dependency`

响应节选：

```json
{
  "report_id": 1,
  "asset": "PEPE",
  "asset_type": "crypto",
  "risk_scan": {
    "risk_score": 100,
    "risk_level": "极高风险",
    "risk_reasons": ["Crypto 基础风险分：链上资产波动和流动性风险默认存在"]
  },
  "emotion_scan": {
    "emotion_score": 100,
    "emotion_level": "高度冲动",
    "detected_emotions": ["FOMO", "仓位冲动", "KOL 驱动", "风险无知"]
  },
  "bias_detection": {
    "bias_score": 60,
    "biases": [
      {
        "bias_type": "FOMO",
        "severity": "★★★★★",
        "warning": "你现在可能不是在研究机会，而是在逃避错过的焦虑。"
      }
    ]
  },
  "final_decision": "🔴 Don't Buy",
  "position_advice": "不建议买入，至少等待 24 小时后重新评估。",
  "journal_saved": true
}
```

### Journal

```bash
curl http://127.0.0.1:8010/journal
curl http://127.0.0.1:8010/journal/1
```

### Investment DNA

```bash
curl http://127.0.0.1:8010/dna
```

示例：

```json
{
  "investor_type": "FOMO Hunter",
  "discipline": 28,
  "patience": 17,
  "risk_appetite": 86,
  "kol_dependency": 91,
  "conviction": 31,
  "emotion_control": 22,
  "independent_thinking": 18,
  "kol_summary": "过去15次记录中，有15次包含 KOL、喊单或外部观点相关线索。这不等于你一定盲从，但需要确认这些信息有没有替代你的独立买入/做空计划。",
  "top_kol_influences": ["Crypto Rover", "Unknown KOL"],
  "summary": "最近50条投资日记里，AI只根据你写下的内容做行为线索统计：FOMO/追涨相关表达7次..."
}
```

### KOL Intelligence V1

KOL Intelligence V1 是免费可上线版本。它不自动抓 Twitter、Telegram 或 YouTube，也不依赖付费 API。用户手动录入 KOL 和喊单价格，系统计算当前 ROI、Trust Score，并把 KOL Dependency 接入 Investment DNA 和 Immune Report。

V1 的 ROI 刷新使用当前价格近似更新，不做精确历史价格回测。后续版本可以接 CoinGecko historical price 或 GeckoTerminal historical OHLCV。

创建 KOL：

```bash
curl -X POST http://127.0.0.1:8010/kol/profiles \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Crypto Rover",
    "twitter_handle": "@rovercrc",
    "youtube_channel": "Crypto Rover",
    "bio": "Crypto market commentator"
  }'
```

创建喊单：

```bash
curl -X POST http://127.0.0.1:8010/kol/calls \
  -H "Content-Type: application/json" \
  -d '{
    "kol_id": 1,
    "asset": "PEPE",
    "asset_type": "crypto",
    "call_time": "2026-07-01T12:00:00",
    "call_price": 0.00001,
    "current_price": 0.000012,
    "source": "twitter",
    "source_url": "https://x.com/example/status/123",
    "call_text": "PEPE will 10x. Last chance.",
    "call_type": "buy",
    "time_horizon": "short"
  }'
```

刷新 ROI：

```bash
curl -X POST http://127.0.0.1:8010/kol/calls/1/refresh
```

重新计算 Trust Score：

```bash
curl -X POST http://127.0.0.1:8010/kol/profiles/1/recalculate
```

查看 KOL Dependency：

```bash
curl http://127.0.0.1:8010/kol/dependency
```

查看 DNA 中的 KOL Dependency：

```bash
curl http://127.0.0.1:8010/dna
```

### AI Investment Notebook

Notebook 复用 Journal 数据库，但不是只读日志。它允许用户继续编辑投资前思考、买入逻辑、最大风险、亏损计划、最终决定，并在复盘后写入 Lesson、Mistake 和 Next Rule。

```bash
curl http://127.0.0.1:8010/notebook
curl http://127.0.0.1:8010/notebook/1
```

创建：

```bash
curl -X POST http://127.0.0.1:8010/notebook \
  -H "Content-Type: application/json" \
  -d '{"asset":"BTC","asset_type":"crypto","title":"BTC thesis","decision":"Wait"}'
```

保存编辑：

```bash
curl -X PUT http://127.0.0.1:8010/notebook/1 \
  -H "Content-Type: application/json" \
  -d '{"notes":"为什么想投资","buy_reason":"我的买入逻辑","risk_awareness":"最大的风险","worst_case_plan":"如果亏损","decision":"Wait"}'
```

复盘：

```bash
curl -X POST http://127.0.0.1:8010/notebook/1/review \
  -H "Content-Type: application/json" \
  -d '{"user_result_text":"一个月后我发现没有止损，差点情绪化补仓。","current_price":65000}'
```

### Review

```bash
curl -X POST http://127.0.0.1:8010/journal/1/review \
  -H "Content-Type: application/json" \
  -d '{
    "journal_id": 1,
    "current_price": 0.000012,
    "user_result_text": "一个月后亏了28%，我当时太冲动了"
  }'
```

响应：

```json
{
  "journal_id": 1,
  "original_decision": "🔴 Don't Buy",
  "review_result": "一个月后亏了28%，我当时太冲动了。复盘结论：一个月前你追的是上涨带来的安全感，不是经过验证的机会。",
  "mistake_type": "FOMO 追高",
  "lesson": "一个月前你追的是上涨带来的安全感，不是经过验证的机会。",
  "next_time_rule": "下次凡是出现怕踏空，必须等 24 小时，并写出三个不买理由。",
  "review_status": "reviewed"
}
```

### KOL Check

```bash
curl -X POST http://127.0.0.1:8010/kol/check \
  -H "Content-Type: application/json" \
  -d '{
    "kol_name": "example_kol",
    "asset": "PEPE",
    "call_text": "这个币马上翻倍，怕踏空就梭哈"
  }'
```

## 黑客松 Demo 讲解词

“普通 AI 投资助手会分析 PEPE、NVDA 或 TSLA 能不能买。但真实亏损往往不是因为用户没有数据，而是因为用户在 FOMO、KOL 喊单、朋友推荐、梭哈冲动和补仓回本里做了错误动作。

Global Asset Shield Agent V4 是 AI Investment Immune System。它先扫描资产风险，再扫描用户情绪和认知偏差，然后强制生成反方观点、后悔模拟和信念评分。最后它不会说‘自行判断’，而是明确输出 Don't Buy、Wait 或 Small Position。

更重要的是，每一次报告都会写入 SQLite 投资日记。一个月后，用户可以回来复盘：当时是 FOMO、KOL 盲从、仓位过重，还是没有止损。这个 Agent 不是一次性聊天机器人，而是一个长期帮助普通投资者少犯错的投资免疫系统。”

## 当前扩展点

- `scanner/crypto.py`：GoPlus 真实安全检测接口
- `scanner/stock.py`：A 股、港股数据源
- `scanner/kol.py`：从 JSON 迁移到 SQLite 或外部 KOL 数据库
- `immune/decision.py`：接入更细的用户风险偏好
- `immune/review.py`：加入价格回测和持仓周期分析
