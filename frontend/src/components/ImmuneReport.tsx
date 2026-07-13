import ScoreCard from "./ScoreCard";

type ImmuneReportProps = {
  report: any | null;
  onOpenNotebook?: (id: number) => void;
};

function listItems(items: unknown): string[] {
  return Array.isArray(items) ? items.map((item) => String(item)) : [];
}

function normalizeBiases(raw: unknown): Array<Record<string, string>> {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    if (typeof item === "string") {
      return { bias_type: item, severity: "", warning: item, better_question: "" };
    }
    return item as Record<string, string>;
  });
}

function toneForDecision(decision: string): "red" | "yellow" | "green" {
  if (decision.includes("Don't")) return "red";
  if (decision.includes("Small")) return "green";
  return "yellow";
}

function decisionTitle(decision: string) {
  if (decision.includes("Don't Short")) return "先不要做空";
  if (decision.includes("Don't")) return "先不要买";
  if (decision.includes("Small Short")) return "只允许小仓位做空";
  if (decision.includes("Small")) return "只允许小仓位";
  return "先观察";
}

function nextActionsForDecision(decision: string): string[] {
  if (decision.includes("Don't Short")) {
    return ["至少等 24 小时再重新扫描一次", "写清楚做空失效条件：上涨到哪里立刻退出", "不要用加空来证明自己看对"];
  }
  if (decision.includes("Don't")) {
    return ["至少等 24 小时再重新扫描一次", "先写清楚失效条件：什么情况证明你错了", "不要用加仓来证明自己没错"];
  }
  if (decision.includes("Small Short")) {
    return ["风险敞口控制在 3%-5%", "下单前写好止损、止盈和最长持有时间", "确认自己不是因为讨厌它才做空"];
  }
  if (decision.includes("Small")) {
    return ["仓位控制在 5%-10%", "下单前写好止损和复盘日期", "把这次理由保存到 Notebook，之后对照结果"];
  }
  return ["先加入观察清单，不急着下单", "如果一定要试错，仓位不要超过 5%", "等情绪退下来后，再用同样输入重新扫描"];
}

function confidenceTone(level?: string) {
  if ((level || "").includes("High")) return "border-emerald-300/40 bg-emerald-400/10 text-emerald-50";
  if ((level || "").includes("Medium")) return "border-cyan-300/40 bg-cyan-400/10 text-cyan-50";
  if ((level || "").includes("Low")) return "border-amber-300/40 bg-amber-400/10 text-amber-50";
  return "border-rose-300/40 bg-rose-400/10 text-rose-50";
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-5">
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <div className="mt-4 text-sm leading-6 text-slate-300">{children}</div>
    </div>
  );
}

function formatNumber(value: unknown) {
  const number = Number(value);
  if (value === null || value === undefined || Number.isNaN(number)) return "未知";
  return number.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function directionLabel(direction?: string) {
  if (direction === "short") return "做空 / 看跌";
  if (direction === "watch") return "观望 / 不开仓";
  return "做多 / 买入";
}

function JourneyStep({ index, title, detail, active }: { index: number; title: string; detail: string; active?: boolean }) {
  return (
    <div className={`rounded-lg border p-3 ${active ? "border-cyan-300/50 bg-cyan-300/10" : "border-slate-800 bg-slate-950/60"}`}>
      <div className="flex items-center gap-2">
        <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${active ? "bg-cyan-300 text-slate-950" : "bg-slate-800 text-slate-300"}`}>
          {index}
        </span>
        <span className="text-sm font-semibold text-white">{title}</span>
      </div>
      <p className="mt-2 text-xs leading-5 text-slate-400">{detail}</p>
    </div>
  );
}

function MarketData({ rawData, assetType }: { rawData: Record<string, any>; assetType: string }) {
  if (!rawData) return null;
  const isCrypto = assetType === "crypto";
  const isCnStock = assetType === "cn_stock";
  const rows = isCrypto
    ? [
        ["名称", rawData.name || rawData.symbol],
        ["链 / DEX", [rawData.chain, rawData.dex].filter(Boolean).join(" / ") || "未知"],
        ["价格 USD", rawData.price_usd ? `$${rawData.price_usd}` : "未知"],
        ["流动性 USD", `$${formatNumber(rawData.liquidity)}`],
        ["FDV", `$${formatNumber(rawData.fdv)}`],
        ["24h 成交量", `$${formatNumber(rawData.volume24h)}`],
      ]
    : isCnStock
      ? [
          ["名称", rawData.name || rawData.symbol],
          ["价格", rawData.price ? `¥${formatNumber(rawData.price)}` : "未知"],
          ["总市值", rawData.market_cap ? `¥${formatNumber(rawData.market_cap)}` : "未知"],
          ["涨跌幅", rawData.day_change_percent !== null && rawData.day_change_percent !== undefined ? `${formatNumber(rawData.day_change_percent)}%` : "未知"],
          ["换手率", rawData.turnover_rate !== null && rawData.turnover_rate !== undefined ? `${formatNumber(rawData.turnover_rate)}%` : "未知"],
          ["PE", formatNumber(rawData.pe)],
        ]
      : [
          ["名称", rawData.short_name || rawData.symbol],
          ["价格", rawData.price ? `$${formatNumber(rawData.price)}` : "未知"],
          ["市值", rawData.market_cap ? `$${formatNumber(rawData.market_cap)}` : "未知"],
          ["单日涨跌幅", rawData.day_change_percent !== null && rawData.day_change_percent !== undefined ? `${formatNumber(rawData.day_change_percent)}%` : "未知"],
          ["成交量", formatNumber(rawData.volume)],
          ["PE", formatNumber(rawData.pe)],
          ["营收增长", rawData.revenue_growth !== null && rawData.revenue_growth !== undefined ? `${formatNumber(Number(rawData.revenue_growth) * 100)}%` : "未知"],
          ["利润率", rawData.profit_margin !== null && rawData.profit_margin !== undefined ? `${formatNumber(Number(rawData.profit_margin) * 100)}%` : "未知"],
          ["Debt/Equity", formatNumber(rawData.debt_to_equity)],
          ["自由现金流", rawData.free_cash_flow ? `$${formatNumber(rawData.free_cash_flow)}` : "未知"],
          ["分析师共识", rawData.recommendation_key || "未知"],
          ["新闻风险", Array.isArray(rawData.news_risk_keywords) && rawData.news_risk_keywords.length ? rawData.news_risk_keywords.join(", ") : "未发现"],
        ];

  return (
    <div className="mt-4 rounded-lg border border-slate-700 bg-slate-950/60 p-4">
      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
        <div className="font-semibold text-white">行情资料</div>
        {rawData.fallback_mock ? (
          <span className="rounded-full border border-amber-300/40 px-3 py-1 text-xs text-amber-100">Fallback mock，未取得实时数据</span>
        ) : (
          <span className="rounded-full border border-emerald-300/40 px-3 py-1 text-xs text-emerald-100">已读取外部行情</span>
        )}
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-md border border-slate-800 bg-slate-900/70 px-3 py-2">
            <div className="text-xs text-slate-500">{label}</div>
            <div className="mt-1 break-words font-semibold text-slate-100">{value || "未知"}</div>
          </div>
        ))}
      </div>
      {rawData.pair_url ? (
        <a className="mt-3 inline-flex text-sm font-semibold text-cyan-300 hover:text-cyan-100" href={rawData.pair_url} target="_blank" rel="noreferrer">
          打开 DexScreener 交易对
        </a>
      ) : null}
      {rawData.security_summary ? (
        <div className="mt-4 rounded-lg border border-rose-300/20 bg-rose-400/10 p-3">
          <div className="font-semibold text-rose-50">GoPlus 合约安全</div>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {[
              ["蜜罐", rawData.security_summary.is_honeypot ? "是" : "否"],
              ["黑名单", rawData.security_summary.is_blacklisted ? "是" : "否"],
              ["可增发", rawData.security_summary.is_mintable ? "是" : "否"],
              ["代理合约", rawData.security_summary.is_proxy ? "是" : "否"],
              ["买入税", `${rawData.security_summary.buy_tax_percent}%`],
              ["卖出税", `${rawData.security_summary.sell_tax_percent}%`],
            ].map(([label, value]) => (
              <div key={label} className="rounded-md bg-slate-950/50 px-3 py-2">
                <span className="text-slate-400">{label}: </span>
                <span className="font-semibold text-white">{value}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function MungerLens({ lens }: { lens: any }) {
  if (!lens) return null;
  return (
    <Section title="Munger Lens">
      <div className="rounded-lg border border-amber-300/20 bg-amber-300/10 p-4">
        <div className="text-xs uppercase tracking-[0.18em] text-amber-200">反愚蠢检查器</div>
        <div className="mt-2 text-2xl font-black text-white">{lens.munger_verdict}</div>
        <p className="mt-3 text-amber-50">{lens.one_sentence}</p>
      </div>
      <div className="mt-4 space-y-4">
        <div>
          <div className="font-semibold text-white">逆向思考</div>
          <p className="mt-1 text-slate-400">{lens.inversion?.question}</p>
          <ul className="mt-2 space-y-2">
            {listItems(lens.inversion?.failure_paths).map((item, index) => <li key={index}>- {item}</li>)}
          </ul>
        </div>
        <div>
          <div className="font-semibold text-white">能力圈</div>
          <p className="mt-1">{lens.circle_of_competence}</p>
        </div>
        <div>
          <div className="font-semibold text-white">激励机制</div>
          <p className="mt-1">{lens.incentive_check}</p>
        </div>
        <div>
          <div className="font-semibold text-white">Lollapalooza 效应</div>
          <ul className="mt-2 space-y-2">
            {listItems(lens.lollapalooza_effect).map((item, index) => <li key={index}>- {item}</li>)}
          </ul>
        </div>
        <div className="rounded-lg border border-slate-700 bg-slate-950/60 p-3">
          <div className="font-semibold text-white">安全边际</div>
          <p className="mt-1 text-slate-300">{lens.margin_of_safety}</p>
          {lens.too_hard_pile ? <p className="mt-2 text-amber-100">这笔交易应该先进入 Too Hard 篮子。</p> : null}
        </div>
      </div>
    </Section>
  );
}

function AiCoach({ coach }: { coach: any }) {
  if (!coach) return null;
  const sourceLabel = coach.source === "deepseek" ? "DeepSeek AI" : coach.source === "limit_exceeded" ? "规则版 / 今日额度已用完" : "规则版 fallback";
  return (
    <Section title="AI Coach">
      <div className="rounded-lg border border-cyan-300/20 bg-cyan-300/10 p-4">
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
          <div className="text-xs uppercase tracking-[0.18em] text-cyan-200">对话式投资免疫教练</div>
          <span className="rounded-full border border-cyan-200/30 px-3 py-1 text-xs text-cyan-100">{sourceLabel}</span>
        </div>
        <p className="mt-3 text-lg font-semibold leading-8 text-white">{coach.coach_message}</p>
      </div>
      <div className="mt-4 space-y-4">
        <div>
          <div className="font-semibold text-white">行为模式</div>
          <p className="mt-1 text-slate-300">{coach.behavior_pattern}</p>
        </div>
        {coach.data_confidence_note ? (
          <div>
            <div className="font-semibold text-white">数据置信度解释</div>
            <p className="mt-1 text-slate-300">{coach.data_confidence_note}</p>
          </div>
        ) : null}
        <div>
          <div className="font-semibold text-white">下一步动作</div>
          <p className="mt-1 text-amber-100">{coach.next_action}</p>
        </div>
        <div className="rounded-lg border border-slate-700 bg-slate-950/60 p-3 text-xs text-slate-400">
          {coach.cost_control}
          {typeof coach.remaining === "number" ? <span> 今日剩余额度：{coach.remaining}/{coach.daily_limit}</span> : null}
        </div>
      </div>
    </Section>
  );
}

function DataConfidence({ confidence }: { confidence: any }) {
  if (!confidence) return null;
  return (
    <Section title="Data Confidence">
      <div className={`rounded-lg border p-4 ${confidenceTone(confidence.level)}`}>
        <div className="text-xs uppercase tracking-[0.18em] opacity-80">数据置信度</div>
        <div className="mt-2 flex items-end gap-3">
          <div className="text-4xl font-black text-white">{confidence.score}</div>
          <div className="pb-1 text-lg font-semibold">{confidence.level}</div>
        </div>
        <p className="mt-3 text-sm leading-6">{confidence.summary}</p>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-emerald-300/20 bg-slate-950/60 p-3">
          <div className="font-semibold text-emerald-100">已获取</div>
          <ul className="mt-2 space-y-1 text-slate-300">
            {listItems(confidence.available).map((item, index) => <li key={index}>- {item}</li>)}
          </ul>
        </div>
        <div className="rounded-lg border border-amber-300/20 bg-slate-950/60 p-3">
          <div className="font-semibold text-amber-100">缺失</div>
          <ul className="mt-2 space-y-1 text-slate-300">
            {listItems(confidence.missing).map((item, index) => <li key={index}>- {item}</li>)}
          </ul>
        </div>
      </div>
      {listItems(confidence.warnings).length ? (
        <div className="mt-4 rounded-lg border border-rose-300/20 bg-rose-400/10 p-3 text-rose-50">
          {listItems(confidence.warnings).map((item, index) => <p key={index}>- {item}</p>)}
        </div>
      ) : null}
      <p className="mt-4 text-cyan-100">{confidence.decision_gate}</p>
    </Section>
  );
}

function ObservationPlan({ plan }: { plan: any }) {
  if (!plan) return null;
  return (
    <Section title="Observation Plan">
      <div className="rounded-lg border border-cyan-300/30 bg-cyan-300/10 p-4">
        <div className="text-xs uppercase tracking-[0.18em] text-cyan-200">观望不是空等</div>
        <p className="mt-2 text-lg font-semibold leading-7 text-white">{plan.summary}</p>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-lg border border-slate-700 bg-slate-950/60 p-3">
          <div className="text-xs text-slate-500">观察信号</div>
          <div className="mt-2 font-semibold text-white">{plan.signal_to_watch}</div>
        </div>
        <div className="rounded-lg border border-slate-700 bg-slate-950/60 p-3">
          <div className="text-xs text-slate-500">突然上涨时</div>
          <div className="mt-2 font-semibold text-white">{plan.fomo_plan}</div>
        </div>
        <div className="rounded-lg border border-slate-700 bg-slate-950/60 p-3">
          <div className="text-xs text-slate-500">复查时间</div>
          <div className="mt-2 font-semibold text-white">{plan.review_timing}</div>
        </div>
      </div>
      <p className="mt-4 text-amber-100">{plan.no_position_rule}</p>
      <ul className="mt-3 space-y-2">
        {listItems(plan.checklist).map((item, index) => <li key={index}>- {item}</li>)}
      </ul>
    </Section>
  );
}

function HistoricalDNAScan({ scan }: { scan: any }) {
  if (!scan) return null;
  const patterns = listItems(scan.triggered_patterns);
  const warnings = listItems(scan.warnings);
  const evidence = Array.isArray(scan.evidence) ? scan.evidence : [];
  return (
    <Section title="Historical DNA Scan">
      <div className="rounded-lg border border-cyan-300/20 bg-cyan-300/10 p-4">
        <div className="text-xs uppercase tracking-[0.16em] text-cyan-200">This scan remembers you</div>
        <div className="mt-2 text-2xl font-semibold text-white">{scan.investor_type || "Unknown Investor"}</div>
        <p className="mt-3 text-slate-300">{scan.summary}</p>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        {[
          ["纪律", scan.discipline],
          ["耐心", scan.patience],
          ["情绪控制", scan.emotion_control],
          ["独立思考", scan.independent_thinking],
        ].map(([label, value]) => (
          <div key={String(label)} className="rounded-lg border border-slate-700 bg-slate-950/60 p-3">
            <div className="text-xs text-slate-500">{label}</div>
            <div className="mt-1 text-2xl font-semibold text-white">{String(value ?? 0)}</div>
          </div>
        ))}
      </div>
      <div className="mt-4">
        <div className="font-semibold text-white">本次重复模式</div>
        {patterns.length ? (
          <ul className="mt-2 space-y-2">{patterns.map((item, index) => <li key={index}>- {item}</li>)}</ul>
        ) : (
          <p className="mt-2 text-slate-400">这次没有明显重复历史高危模式。</p>
        )}
      </div>
      <div className="mt-4">
        <div className="font-semibold text-amber-100">历史提醒</div>
        <ul className="mt-2 space-y-2">{warnings.map((item, index) => <li key={index}>- {item}</li>)}</ul>
      </div>
      {evidence.length ? (
        <div className="mt-4">
          <div className="font-semibold text-cyan-100">证据来源</div>
          <div className="mt-2 space-y-2">
            {evidence.map((item: any, index: number) => (
              <div key={index} className="rounded-lg border border-slate-700 bg-slate-950/60 p-3">
                <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                  <span>#{item.record_id}</span>
                  <span>{item.asset}</span>
                  <span>{item.signal}</span>
                  <span>{item.field}</span>
                </div>
                <p className="mt-2 text-slate-300">{item.excerpt}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </Section>
  );
}

export default function ImmuneReport({ report, onOpenNotebook }: ImmuneReportProps) {
  if (!report) {
    return (
      <section className="mx-auto max-w-6xl px-5 py-8">
        <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-8 text-center text-slate-400">
          先完成一次免疫扫描。系统会把资产风险、情绪冲动、认知偏差和行动建议放在同一份报告里。
        </div>
      </section>
    );
  }

  const biases = normalizeBiases(report.bias_detection?.biases);

  return (
    <section className="mx-auto max-w-6xl px-5 py-8">
      <div className="mb-5 rounded-lg border border-slate-800 bg-slate-950/80 p-6 shadow-glow">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
          <div>
            <div className="text-sm uppercase tracking-[0.18em] text-slate-500">Immune Report #{report.report_id}</div>
            <h2 className="mt-2 text-3xl font-semibold text-white">
              {report.asset} <span className="text-base font-medium text-slate-400">/ {report.asset_type}</span>
            </h2>
            <div className="mt-3 inline-flex rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 text-xs font-semibold text-cyan-100">
              扫描方向：{directionLabel(report.trade_direction)}
            </div>
            <p className="mt-3 max-w-3xl text-slate-300">{report.summary}</p>
          </div>
          <div className={`rounded-lg border p-5 text-center ${toneForDecision(report.final_decision) === "red" ? "border-red-400/40 bg-red-500/15" : toneForDecision(report.final_decision) === "green" ? "border-emerald-300/40 bg-emerald-500/15" : "border-amber-300/40 bg-amber-400/15"}`}>
            <div className="text-sm text-slate-400">Final Decision</div>
            <div className="mt-2 text-4xl font-bold text-white">{report.final_decision}</div>
          </div>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <ScoreCard label="Risk" value={report.risk_scan?.risk_score} detail={report.risk_scan?.risk_level} tone="red" />
          <ScoreCard label="Emotion" value={report.emotion_scan?.emotion_score} detail={report.emotion_scan?.emotion_level} tone="yellow" />
          <ScoreCard label="Bias" value={report.bias_detection?.bias_score} detail={`${biases.length} detected`} tone="cyan" />
          <ScoreCard label="Conviction" value={report.conviction_score?.score} detail={report.conviction_score?.level} tone="green" />
        </div>
        <div className="mt-5 rounded-lg border border-slate-800 bg-slate-900/70 p-4">
          <div className="text-sm font-semibold text-white">Position Advice</div>
          <p className="mt-2 text-slate-300">{report.position_advice}</p>
          <p className="mt-2 text-slate-400">{report.decision_reason}</p>
        </div>
        <div className="mt-5 rounded-lg border border-cyan-300/20 bg-cyan-300/10 p-4">
          <div className="text-sm uppercase tracking-[0.18em] text-cyan-200">What to do next</div>
          <div className="mt-2 text-2xl font-black text-white">{decisionTitle(report.final_decision)}</div>
          {report.journal_saved && report.report_id ? (
            <div className="mt-3 rounded-lg border border-emerald-300/30 bg-emerald-400/10 p-3 text-sm leading-6 text-emerald-50">
              已保存为 Notebook #{report.report_id}。这次扫描不是一次性报告，下一步要进入笔记本写下你的最终决定，之后用复盘更新 DNA。
            </div>
          ) : null}
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <JourneyStep index={1} title="Scan" detail="资产风险、情绪、偏差和信念已完成扫描。" active />
            <JourneyStep index={2} title="Notebook" detail="把最终决定和交易计划写进同一条记录。" active={Boolean(report.journal_saved)} />
            <JourneyStep index={3} title="Review" detail="结果发生后复盘：卖飞、补仓、扛单、爆仓都要记录。" />
            <JourneyStep index={4} title="DNA" detail="复盘会沉淀为长期行为画像，影响下一次扫描。" />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {nextActionsForDecision(report.final_decision).map((action, index) => (
              <div key={action} className="rounded-lg border border-slate-700 bg-slate-950/70 p-3">
                <div className="text-xs font-semibold text-cyan-200">Step {index + 1}</div>
                <p className="mt-2 text-sm leading-6 text-slate-200">{action}</p>
              </div>
            ))}
          </div>
          {report.journal_saved && report.report_id ? (
            <button
              className="mt-4 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-100"
              onClick={() => onOpenNotebook?.(report.report_id)}
            >
              继续到 Notebook 写最终决定
            </button>
          ) : null}
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <DataConfidence confidence={report.data_confidence} />
        <ObservationPlan plan={report.observation_plan} />
        <HistoricalDNAScan scan={report.historical_dna_scan} />
        <Section title="A. Risk Scan">
          <p className="font-semibold text-white">{report.risk_scan?.risk_score} / {report.risk_scan?.risk_level}</p>
          <MarketData rawData={report.risk_scan?.raw_data} assetType={report.asset_type} />
          <ul className="mt-3 space-y-2">
            {listItems(report.risk_scan?.risk_reasons).map((item, index) => <li key={index}>- {item}</li>)}
          </ul>
        </Section>
        <Section title="B. Emotion Scan">
          <p className="font-semibold text-white">{report.emotion_scan?.emotion_score} / {report.emotion_scan?.emotion_level}</p>
          <p className="mt-3">Detected: {listItems(report.emotion_scan?.detected_emotions).join(", ")}</p>
          <p className="mt-3 text-cyan-100">{report.emotion_scan?.intervention_advice}</p>
        </Section>
        <Section title="C. Bias Detector">
          <p className="font-semibold text-white">Bias Score: {report.bias_detection?.bias_score}</p>
          <div className="mt-3 space-y-3">
            {biases.map((bias, index) => (
              <div key={index} className="rounded-lg border border-slate-700 bg-slate-950/60 p-3">
                <div className="font-semibold text-white">{bias.bias_type} {bias.severity}</div>
                <p className="mt-1 text-rose-100">{bias.warning}</p>
                {bias.better_question ? <p className="mt-1 text-slate-400">Better question: {bias.better_question}</p> : null}
              </div>
            ))}
          </div>
        </Section>
        <Section title="D. Devil's Advocate">
          <p className="font-semibold text-rose-100">{report.trade_direction === "short" ? "Against Shorting" : report.trade_direction === "watch" ? "Against Opening a Position" : "Against Buying"}</p>
          <ul className="mt-2 space-y-2">{listItems(report.devil_advocate?.against_buying).map((item, index) => <li key={index}>- {item}</li>)}</ul>
          <p className="mt-4 font-semibold text-emerald-100">Supporting Case</p>
          <ul className="mt-2 space-y-2">{listItems(report.devil_advocate?.supporting_case).map((item, index) => <li key={index}>- {item}</li>)}</ul>
          <p className="mt-4 font-semibold text-cyan-100">Killer Questions</p>
          <ul className="mt-2 space-y-2">{listItems(report.devil_advocate?.killer_questions).map((item, index) => <li key={index}>- {item}</li>)}</ul>
        </Section>
        <Section title="Regret Simulator">
          <div className="space-y-3">
            <p><span className="text-white">{report.trade_direction === "short" ? "Short and up" : "Buy and up"}:</span> {report.regret_simulation?.buy_and_up}</p>
            <p><span className="text-white">{report.trade_direction === "short" ? "Short and down" : "Buy and down"}:</span> {report.regret_simulation?.buy_and_down}</p>
            <p><span className="text-white">{report.trade_direction === "short" ? "Not short and up" : "Not buy and up"}:</span> {report.regret_simulation?.not_buy_and_up}</p>
            <p><span className="text-white">{report.trade_direction === "short" ? "Not short and down" : "Not buy and down"}:</span> {report.regret_simulation?.not_buy_and_down}</p>
            <p className="text-amber-100">{report.regret_simulation?.likely_regret_pattern}</p>
            <p className="text-rose-100">{report.regret_simulation?.behavior_warning}</p>
          </div>
        </Section>
        <Section title="Conviction Score">
          <p className="font-semibold text-white">{report.conviction_score?.score} / {report.conviction_score?.level}</p>
          <p className="mt-3 font-semibold text-rose-100">Problems</p>
          <ul className="mt-2 space-y-2">{listItems(report.conviction_score?.problems).map((item, index) => <li key={index}>- {item}</li>)}</ul>
          <p className="mt-4 font-semibold text-cyan-100">Improvement Questions</p>
          <ul className="mt-2 space-y-2">{listItems(report.conviction_score?.improvement_questions).map((item, index) => <li key={index}>- {item}</li>)}</ul>
        </Section>
        <AiCoach coach={report.ai_coach} />
        <MungerLens lens={report.munger_lens} />
      </div>
    </section>
  );
}
