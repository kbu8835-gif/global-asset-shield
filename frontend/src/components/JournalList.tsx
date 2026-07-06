import type { JournalEntry } from "../api";

type JournalListProps = {
  journal: JournalEntry[];
  loading: boolean;
  onRefresh: () => void;
  onReview: (entry: JournalEntry) => void;
};

export default function JournalList({ journal, loading, onRefresh, onReview }: JournalListProps) {
  return (
    <section className="mx-auto max-w-6xl px-5 py-8">
      <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-5">
        <div className="mb-4 flex flex-col justify-between gap-3 md:flex-row md:items-center">
          <div>
            <h2 className="text-2xl font-semibold text-white">Investment Journal</h2>
            <p className="mt-1 text-sm text-slate-400">每一次扫描都会保存，复盘会让这个 Agent 变成长线工具。</p>
          </div>
          <button onClick={onRefresh} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-100 hover:border-cyan-300">
            {loading ? "Loading..." : "Refresh Journal"}
          </button>
        </div>

        <div className="space-y-3">
          {journal.slice(0, 6).map((entry) => (
            <div key={entry.id} className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
              <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
                <div>
                  <div className="text-xs text-slate-500">#{entry.id} · {new Date(entry.created_at).toLocaleString()}</div>
                  <div className="mt-1 text-lg font-semibold text-white">{entry.asset} · {entry.final_decision}</div>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">{entry.summary}</p>
                </div>
                <button onClick={() => onReview(entry)} className="rounded-lg bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-200">
                  Review
                </button>
              </div>
            </div>
          ))}
          {!journal.length && <div className="rounded-lg border border-slate-800 p-5 text-center text-slate-400">No journal entries yet.</div>}
        </div>
      </div>
    </section>
  );
}

