import { useEffect, useState } from "react";
import {
  createInvestmentJournalEntry,
  getInvestmentJournalDNA,
  getInvestmentJournalEntries,
  getInvestmentJournalHealth,
  submitInvestmentOutcome,
  type InvestmentJournalCreatePayload,
  type InvestmentJournalDNA,
  type InvestmentJournalEntry,
  type InvestmentJournalHealth,
} from "../api";

const userId = "demo_user";

const defaultEntry: InvestmentJournalCreatePayload = {
  user_id: userId,
  asset_symbol: "PEPE",
  asset_type: "crypto",
  action: "consider_buy after pump",
  reason: "KOL 推荐，最近涨很多",
  emotion_tag: "FOMO",
  risk_score: 78,
  ai_advice: "不建议买",
  user_decision: "still_buy",
};

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
      <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</div>
      <div className="mt-3 flex items-end gap-3">
        <div className="h-2 flex-1 rounded-full bg-slate-800">
          <div className="h-2 rounded-full bg-cyan-300" style={{ width: `${Math.max(4, value)}%` }} />
        </div>
        <div className="text-2xl font-black text-white">{value}</div>
      </div>
    </div>
  );
}

export default function InvestmentJournalPage({ onError }: { onError: (message: string) => void }) {
  const [entries, setEntries] = useState<InvestmentJournalEntry[]>([]);
  const [dna, setDna] = useState<InvestmentJournalDNA | null>(null);
  const [health, setHealth] = useState<InvestmentJournalHealth | null>(null);
  const [form, setForm] = useState<InvestmentJournalCreatePayload>(defaultEntry);
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);
  const [outcome7d, setOutcome7d] = useState("-12%");
  const [outcome30d, setOutcome30d] = useState("-38%");
  const [feedback, setFeedback] = useState("当时太冲动了");
  const [aiWasRight, setAiWasRight] = useState(true);
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try {
      const [nextEntries, nextDna, nextHealth] = await Promise.all([
        getInvestmentJournalEntries(userId),
        getInvestmentJournalDNA(userId),
        getInvestmentJournalHealth(userId),
      ]);
      setEntries(nextEntries);
      setDna(nextDna);
      setHealth(nextHealth);
      setSelectedEntryId((current) => current || nextEntries[0]?.id || null);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to load Investment Journal");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const createEntry = async () => {
    setLoading(true);
    onError("");
    try {
      const result = await createInvestmentJournalEntry(form);
      setSummary(result.ai_summary);
      setSelectedEntryId(result.journal_entry_id);
      await load();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to create Investment Journal entry");
    } finally {
      setLoading(false);
    }
  };

  const submitOutcome = async () => {
    if (!selectedEntryId) return;
    setLoading(true);
    onError("");
    try {
      const result = await submitInvestmentOutcome({
        journal_entry_id: selectedEntryId,
        outcome_7d: outcome7d,
        outcome_30d: outcome30d,
        user_feedback: feedback,
        ai_was_right: aiWasRight,
      });
      setSummary(result.behavior_summary);
      await load();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to submit outcome");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="mx-auto max-w-6xl px-5 py-8">
      <div className="mb-6">
        <p className="text-xs uppercase tracking-[0.28em] text-cyan-300">Investment Journal</p>
        <h2 className="mt-2 text-3xl font-black text-white">训练你的投资免疫系统</h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          这不是单纯记录交易，而是在训练你的投资免疫系统。每一次想买、每一次后悔、每一次复盘，都会变成你的长期行为画像。
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-bold text-white">新增投资日记</h3>
            <span className="rounded-full border border-cyan-300/30 px-3 py-1 text-xs text-cyan-200">Behavior Memory</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm text-slate-300">
              Asset
              <input className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-white" value={form.asset_symbol} onChange={(event) => setForm({ ...form, asset_symbol: event.target.value })} />
            </label>
            <label className="text-sm text-slate-300">
              Asset Type
              <select className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-white" value={form.asset_type} onChange={(event) => setForm({ ...form, asset_type: event.target.value })}>
                <option value="crypto">加密货币</option>
                <option value="stock">美股</option>
                <option value="cn_stock">A股</option>
              </select>
            </label>
            <label className="text-sm text-slate-300">
              Action
              <input className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-white" value={form.action} onChange={(event) => setForm({ ...form, action: event.target.value })} />
            </label>
            <label className="text-sm text-slate-300">
              Emotion Tag
              <input className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-white" value={form.emotion_tag || ""} onChange={(event) => setForm({ ...form, emotion_tag: event.target.value })} />
            </label>
            <label className="sm:col-span-2 text-sm text-slate-300">
              Reason
              <textarea className="mt-1 min-h-24 w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-white" value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} />
            </label>
            <label className="text-sm text-slate-300">
              Risk Score
              <input type="number" min={0} max={100} className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-white" value={form.risk_score} onChange={(event) => setForm({ ...form, risk_score: Number(event.target.value) })} />
            </label>
            <label className="text-sm text-slate-300">
              User Decision
              <select className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-white" value={form.user_decision} onChange={(event) => setForm({ ...form, user_decision: event.target.value })}>
                <option value="still_buy">still_buy</option>
                <option value="wait">wait</option>
                <option value="dont_buy">dont_buy</option>
              </select>
            </label>
            <label className="sm:col-span-2 text-sm text-slate-300">
              AI Advice
              <input className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-white" value={form.ai_advice} onChange={(event) => setForm({ ...form, ai_advice: event.target.value })} />
            </label>
          </div>
          <button className="mt-4 rounded-md bg-cyan-300 px-5 py-3 text-sm font-black text-slate-950 hover:bg-cyan-200 disabled:opacity-50" disabled={loading} onClick={createEntry}>
            {loading ? "Saving..." : "Create Journal Entry"}
          </button>
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-5">
            <h3 className="text-lg font-bold text-white">Investment Health</h3>
            <div className="mt-4 text-5xl font-black text-cyan-300">{health?.health_score ?? 50}</div>
            <p className="mt-3 text-sm leading-6 text-slate-300">{health?.summary || "先记录一笔投资决策，AI 才能开始看见你的行为模式。"}</p>
            <div className="mt-4 rounded-md bg-red-500/10 p-3 text-sm text-red-100">Behavior Risk: {health?.behavior_risk_score ?? 0}</div>
          </div>
          {dna ? (
            <div className="grid gap-3">
              <Metric label="FOMO" value={dna.fomo_score} />
              <Metric label="Discipline" value={dna.discipline_score} />
              <Metric label="Patience" value={dna.patience_score} />
              <Metric label="Research" value={dna.research_score} />
              <Metric label="Risk Control" value={dna.risk_control_score} />
              <Metric label="KOL Dependency" value={dna.kol_dependency_score} />
            </div>
          ) : null}
        </div>
      </div>

      {summary ? <div className="mt-5 rounded-lg border border-cyan-300/30 bg-cyan-300/10 p-4 text-sm leading-6 text-cyan-50">{summary}</div> : null}

      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_0.8fr]">
        <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-bold text-white">投资日记列表</h3>
            <button className="text-sm text-cyan-300 hover:text-cyan-100" onClick={load}>Refresh</button>
          </div>
          <div className="space-y-3">
            {entries.length === 0 ? <p className="text-sm text-slate-400">还没有投资日记。</p> : null}
            {entries.map((entry) => (
              <button
                key={entry.id}
                className={`w-full rounded-lg border p-4 text-left ${selectedEntryId === entry.id ? "border-cyan-300 bg-cyan-300/10" : "border-slate-800 bg-slate-900/50 hover:border-slate-600"}`}
                onClick={() => setSelectedEntryId(entry.id)}
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-bold text-white">{entry.asset_symbol}</div>
                    <div className="text-xs text-slate-500">{entry.created_at ? new Date(entry.created_at).toLocaleString() : ""}</div>
                  </div>
                  <div className="rounded-full border border-red-400/30 px-3 py-1 text-sm text-red-100">Risk {entry.behavior_risk_score}</div>
                </div>
                <p className="mt-3 text-sm text-slate-300">{entry.reason}</p>
                <p className="mt-2 text-xs text-slate-500">AI: {entry.ai_advice} · User: {entry.user_decision}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-5">
          <h3 className="text-lg font-bold text-white">Outcome 回流</h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">投资免疫系统不是靠预测变强，而是靠结果回流变清醒。</p>
          <div className="mt-4 grid gap-3">
            <label className="text-sm text-slate-300">
              Journal Entry
              <select className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-white" value={selectedEntryId || ""} onChange={(event) => setSelectedEntryId(Number(event.target.value))}>
                {entries.map((entry) => (
                  <option key={entry.id} value={entry.id}>
                    #{entry.id} {entry.asset_symbol}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm text-slate-300">
              7D Outcome
              <input className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-white" value={outcome7d} onChange={(event) => setOutcome7d(event.target.value)} />
            </label>
            <label className="text-sm text-slate-300">
              30D Outcome
              <input className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-white" value={outcome30d} onChange={(event) => setOutcome30d(event.target.value)} />
            </label>
            <label className="text-sm text-slate-300">
              User Feedback
              <textarea className="mt-1 min-h-24 w-full rounded-md border border-slate-700 bg-slate-900 p-3 text-white" value={feedback} onChange={(event) => setFeedback(event.target.value)} />
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={aiWasRight} onChange={(event) => setAiWasRight(event.target.checked)} />
              AI was right
            </label>
          </div>
          <button className="mt-4 rounded-md border border-cyan-300 px-5 py-3 text-sm font-bold text-cyan-100 hover:bg-cyan-300/10 disabled:opacity-50" disabled={loading || !selectedEntryId} onClick={submitOutcome}>
            Submit Outcome
          </button>
        </div>
      </div>
    </section>
  );
}
