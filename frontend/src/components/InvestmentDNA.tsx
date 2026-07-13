import type { InvestmentDNA as InvestmentDNAType, InvestmentJournalHealth } from "../api";

type InvestmentDNAProps = {
  dna: InvestmentDNAType | null;
  health: InvestmentJournalHealth | null;
  loading: boolean;
  onRefresh: () => void;
};

function barWidth(value: number) {
  return `${Math.max(4, Math.min(100, value))}%`;
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="text-sm font-medium text-slate-300">{label}</div>
        <div className="text-2xl font-semibold text-white">{value}</div>
      </div>
      <div className="mt-3 h-2 rounded-full bg-slate-800">
        <div className="h-2 rounded-full bg-cyan-300" style={{ width: barWidth(value) }} />
      </div>
    </div>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return date.toISOString().slice(0, 10);
}

export default function InvestmentDNA({ dna, health, loading, onRefresh }: InvestmentDNAProps) {
  const evidenceSources = dna?.evidence_sources || [];

  return (
    <section className="mx-auto max-w-6xl px-5 pb-16 pt-4">
      <div className="rounded-lg border border-cyan-300/20 bg-slate-950/80 p-6 shadow-glow">
        <div className="mb-6 flex flex-col justify-between gap-3 md:flex-row md:items-start">
          <div>
            <div className="text-sm uppercase tracking-[0.2em] text-cyan-200">Investment DNA</div>
            <h2 className="mt-2 text-3xl font-semibold text-white">The market changes. Your behavior repeats.</h2>
            <p className="mt-2 text-slate-400">AI 不预测市场。AI 预测你下一次会犯什么错。</p>
          </div>
          <button onClick={onRefresh} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-100 hover:border-cyan-300">
            {loading ? "Reading DNA..." : "Refresh DNA"}
          </button>
        </div>

        {dna ? (
          <>
            <div className="mb-5 rounded-lg border border-red-400/30 bg-red-500/10 p-5">
              <div className="text-sm text-slate-400">Investor Type</div>
              <div className="mt-2 text-4xl font-bold text-white">🔥 {dna.investor_type}</div>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <Metric label="Discipline" value={dna.discipline} />
              <Metric label="Patience" value={dna.patience} />
              <Metric label="Risk Appetite" value={dna.risk_appetite} />
              <Metric label="Emotion Control" value={dna.emotion_control} />
              <Metric label="Independent Thinking" value={dna.independent_thinking} />
              <Metric label="Conviction" value={dna.conviction} />
            </div>
            {health ? (
              <div className="mt-5 grid gap-4 md:grid-cols-[260px_1fr]">
                <div className="rounded-lg border border-emerald-300/30 bg-emerald-400/10 p-5">
                  <div className="text-sm text-emerald-100">Investment Health</div>
                  <div className="mt-2 text-5xl font-black text-white">{health.health_score}</div>
                  <div className="mt-2 text-sm text-emerald-100">Behavior Risk: {health.behavior_risk_score}</div>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-5">
                  <div className="text-sm font-semibold text-white">Health Summary</div>
                  <p className="mt-2 leading-7 text-slate-300">{health.summary}</p>
                </div>
              </div>
            ) : null}
            <div className="mt-5 rounded-lg border border-slate-800 bg-slate-900/70 p-5">
              <div className="text-sm font-semibold text-white">Summary</div>
              <p className="mt-2 leading-7 text-slate-300">{dna.summary}</p>
            </div>
            <div className="mt-5 rounded-lg border border-cyan-300/20 bg-slate-900/70 p-5">
              <div className="flex flex-col justify-between gap-2 md:flex-row md:items-end">
                <div>
                  <div className="text-sm font-semibold text-white">Evidence Sources</div>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    DNA 不是凭空判断。下面是系统用于判断你的行为模式的原始记录来源。
                  </p>
                </div>
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200">{dna.evidence_window || "最近记录"}</div>
              </div>
              <div className="mt-5 grid gap-4">
                {evidenceSources.length ? evidenceSources.map((group) => (
                  <div key={group.signal} className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
                    <div className="flex flex-col justify-between gap-2 md:flex-row md:items-start">
                      <div>
                        <div className="text-base font-semibold text-white">{group.signal}</div>
                        <p className="mt-1 text-sm leading-6 text-slate-400">{group.explanation}</p>
                      </div>
                      <div className="rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 text-sm font-semibold text-cyan-50">
                        命中 {group.count}
                      </div>
                    </div>
                    {group.records.length ? (
                      <div className="mt-4 space-y-3">
                        {group.records.map((record) => (
                          <div key={`${group.signal}-${record.source}-${record.record_id}-${record.field}`} className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                              <span className="rounded-full border border-slate-700 px-2 py-0.5">#{record.record_id}</span>
                              <span>{record.source}</span>
                              <span>{record.asset}</span>
                              <span>{record.asset_type}</span>
                              {record.trade_direction ? <span>{record.trade_direction}</span> : null}
                              <span>{formatDate(record.created_at)}</span>
                            </div>
                            <div className="mt-2 text-sm text-slate-300">
                              <span className="text-cyan-200">{record.field}</span>
                              <span className="text-slate-500"> · 命中 </span>
                              <span className="text-amber-100">{record.keyword}</span>
                            </div>
                            <p className="mt-2 text-sm leading-6 text-slate-200">{record.excerpt || "这条记录只有评分，没有文字片段。"}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="mt-4 rounded-lg border border-dashed border-slate-700 p-3 text-sm leading-6 text-slate-500">
                        没有找到用户原文证据。这个信号不会强行推断。
                      </div>
                    )}
                  </div>
                )) : (
                  <div className="rounded-lg border border-dashed border-slate-700 p-4 text-sm leading-6 text-slate-400">
                    还没有足够证据。先完成一次免疫扫描，并在 Notebook 写下你的真实理由。
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="rounded-lg border border-slate-800 p-5 text-slate-400">Run an immune scan to build your Investment DNA.</div>
        )}
      </div>
    </section>
  );
}
