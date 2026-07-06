import { useEffect, useMemo, useState } from "react";
import {
  createNotebook,
  getNotebook,
  getNotebooks,
  reviewNotebook,
  updateNotebook,
  type NotebookDetail,
  type NotebookListItem,
} from "../api";

type NotebookWorkspaceProps = {
  onError: (message: string) => void;
};

const inputClass =
  "w-full rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300";
const areaClass =
  "min-h-28 w-full rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-3 text-sm leading-6 text-white outline-none focus:border-cyan-300";

function formatDate(value?: string | null) {
  if (!value) return "";
  return new Date(value).toISOString().slice(0, 10);
}

function decisionIcon(decision: string) {
  if (decision.includes("Don't")) return "🔴";
  if (decision.includes("Buy") || decision.includes("Small")) return "🟢";
  return "🟡";
}

function scoreBlock(label: string, value?: number) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <div className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value ?? 0}</div>
    </div>
  );
}

export default function NotebookWorkspace({ onError }: NotebookWorkspaceProps) {
  const [items, setItems] = useState<NotebookListItem[]>([]);
  const [selected, setSelected] = useState<NotebookDetail | null>(null);
  const [draft, setDraft] = useState<NotebookDetail | null>(null);
  const [search, setSearch] = useState("");
  const [assetFilter, setAssetFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [sort, setSort] = useState("updated");
  const [saving, setSaving] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewText, setReviewText] = useState("");

  const loadList = async () => {
    const nextItems = await getNotebooks();
    setItems(nextItems);
    if (!selected && nextItems[0]) {
      await openNotebook(nextItems[0].id);
    }
  };

  const openNotebook = async (id: number) => {
    const detail = await getNotebook(id);
    setSelected(detail);
    setDraft(detail);
    setReviewOpen(false);
    setReviewText("");
  };

  useEffect(() => {
    loadList().catch((err) => onError(err instanceof Error ? err.message : "Failed to load notebook"));
  }, []);

  useEffect(() => {
    if (!draft || !selected || draft.id !== selected.id) return;
    const timer = window.setTimeout(() => {
      saveDraft(false).catch((err) => onError(err instanceof Error ? err.message : "Auto save failed"));
    }, 1200);
    return () => window.clearTimeout(timer);
  }, [
    draft?.title,
    draft?.notes,
    draft?.buy_reason,
    draft?.risk_awareness,
    draft?.worst_case_plan,
    draft?.decision,
    draft?.status,
  ]);

  const assets = useMemo(() => ["All", ...Array.from(new Set(items.map((item) => item.asset)))], [items]);
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return items
      .filter((item) => (assetFilter === "All" ? true : item.asset === assetFilter))
      .filter((item) => (statusFilter === "All" ? true : item.status === statusFilter))
      .filter((item) => (!query ? true : `${item.title} ${item.asset} ${item.decision}`.toLowerCase().includes(query)))
      .sort((a, b) => {
        const left = sort === "created" ? a.created_at : a.updated_at;
        const right = sort === "created" ? b.created_at : b.updated_at;
        return right.localeCompare(left);
      });
  }, [items, search, assetFilter, statusFilter, sort]);

  const patchDraft = (patch: Partial<NotebookDetail>) => {
    if (!draft) return;
    setDraft({ ...draft, ...patch });
  };

  const saveDraft = async (showState = true) => {
    if (!draft) return;
    if (showState) setSaving(true);
    const updated = await updateNotebook(draft.id, {
      title: draft.title,
      notes: draft.notes || "",
      buy_reason: draft.buy_reason || "",
      risk_awareness: draft.risk_awareness || "",
      worst_case_plan: draft.worst_case_plan || "",
      decision: draft.decision,
      status: draft.status,
    });
    setSelected(updated);
    setDraft(updated);
    await loadList();
    if (showState) setSaving(false);
  };

  const createBlank = async () => {
    const created = await createNotebook({
      asset: "NEW",
      asset_type: "crypto",
      title: "New investment note",
      decision: "Wait",
      notes: "",
    });
    await loadList();
    await openNotebook(created.id);
  };

  const submitReview = async () => {
    if (!draft || !reviewText.trim()) return;
    const reviewed = await reviewNotebook(draft.id, { user_result_text: reviewText, current_price: 0 });
    setSelected(reviewed);
    setDraft(reviewed);
    await loadList();
  };

  return (
    <section className="mx-auto max-w-7xl px-5 py-8">
      <div className="grid min-h-[760px] gap-5 lg:grid-cols-[360px_1fr]">
        <aside className="rounded-lg border border-slate-800 bg-slate-950/80 p-4">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-sm uppercase tracking-[0.18em] text-cyan-200">Notebook</div>
              <h2 className="mt-1 text-xl font-semibold text-white">AI Investment Notebook</h2>
            </div>
            <button onClick={createBlank} className="rounded-lg bg-cyan-300 px-3 py-2 text-sm font-semibold text-slate-950">
              New
            </button>
          </div>
          <input className={inputClass} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search notes..." />
          <div className="mt-3 grid grid-cols-3 gap-2">
            <select className={inputClass} value={sort} onChange={(event) => setSort(event.target.value)}>
              <option value="updated">最近修改</option>
              <option value="created">创建时间</option>
            </select>
            <select className={inputClass} value={assetFilter} onChange={(event) => setAssetFilter(event.target.value)}>
              {assets.map((asset) => (
                <option key={asset}>{asset}</option>
              ))}
            </select>
            <select className={inputClass} value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option>All</option>
              <option>Open</option>
              <option>Reviewed</option>
              <option>Archived</option>
            </select>
          </div>
          <div className="mt-4 space-y-2">
            {filtered.map((item) => (
              <button
                key={item.id}
                onClick={() => openNotebook(item.id)}
                className={`w-full rounded-lg border p-3 text-left transition ${
                  draft?.id === item.id ? "border-cyan-300/50 bg-cyan-300/10" : "border-slate-800 bg-slate-900/50 hover:border-slate-600"
                }`}
              >
                <div className="flex items-center gap-2 text-white">
                  <span>📄</span>
                  <span className="font-semibold">{item.title}</span>
                </div>
                <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                  <span>{formatDate(item.updated_at)}</span>
                  <span>{item.decision}</span>
                </div>
              </button>
            ))}
          </div>
        </aside>

        <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-6">
          {draft ? (
            <div className="mx-auto max-w-3xl">
              <div className="mb-6">
                <input
                  className="w-full bg-transparent text-4xl font-semibold text-white outline-none"
                  value={draft.title}
                  onChange={(event) => patchDraft({ title: event.target.value })}
                />
                <div className="mt-2 text-sm text-slate-400">
                  {draft.asset} · {draft.asset_type} · {formatDate(draft.created_at)}
                </div>
              </div>

              <div className="mb-6 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                <div className="text-sm text-slate-400">Timeline</div>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-300">
                  {draft.timeline.map((item, index) => (
                    <span key={`${item.event}-${index}`} className="inline-flex items-center gap-2">
                      <span className="rounded-full border border-slate-700 px-3 py-1">{formatDate(item.date)} {item.event}</span>
                      {index < draft.timeline.length - 1 ? <span className="text-slate-600">↓</span> : null}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mb-6 grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                  <div className="text-sm text-slate-400">Asset</div>
                  <div className="mt-2 text-2xl font-semibold text-white">{draft.asset}</div>
                  <div className="mt-1 text-slate-400">{draft.asset_type}</div>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                  <div className="text-sm text-slate-400">AI Decision</div>
                  <div className="mt-2 text-3xl font-semibold text-white">{decisionIcon(draft.decision)} {draft.decision}</div>
                </div>
              </div>

              <div className="space-y-5">
                <label className="block">
                  <div className="mb-2 text-sm font-semibold text-white">为什么想投资？</div>
                  <textarea className={areaClass} value={draft.notes || ""} onChange={(event) => patchDraft({ notes: event.target.value })} />
                </label>
                <label className="block">
                  <div className="mb-2 text-sm font-semibold text-white">我的买入逻辑</div>
                  <textarea className={areaClass} value={draft.buy_reason || ""} onChange={(event) => patchDraft({ buy_reason: event.target.value })} />
                </label>
                <label className="block">
                  <div className="mb-2 text-sm font-semibold text-white">最大的风险</div>
                  <textarea className={areaClass} value={draft.risk_awareness || ""} onChange={(event) => patchDraft({ risk_awareness: event.target.value })} />
                </label>
                <label className="block">
                  <div className="mb-2 text-sm font-semibold text-white">如果亏损</div>
                  <textarea className={areaClass} value={draft.worst_case_plan || ""} onChange={(event) => patchDraft({ worst_case_plan: event.target.value })} />
                </label>
              </div>

              <div className="mt-6 rounded-lg border border-slate-800 bg-slate-900/60 p-5">
                <h3 className="text-lg font-semibold text-white">AI Analysis</h3>
                <div className="mt-4 grid gap-3 md:grid-cols-4">
                  {scoreBlock("Risk", draft.ai_analysis.risk?.score)}
                  {scoreBlock("Emotion", draft.ai_analysis.emotion?.score)}
                  {scoreBlock("Bias", draft.ai_analysis.bias?.score)}
                  {scoreBlock("Conviction", draft.ai_analysis.conviction?.score)}
                </div>
              </div>

              <div className="mt-6 rounded-lg border border-cyan-300/20 bg-cyan-300/10 p-5">
                <h3 className="text-lg font-semibold text-white">AI Coach</h3>
                <p className="mt-3 whitespace-pre-line leading-7 text-cyan-50">{draft.ai_coach}</p>
              </div>

              <div className="mt-6 rounded-lg border border-slate-800 bg-slate-900/60 p-5">
                <h3 className="text-lg font-semibold text-white">我的最终决定</h3>
                <div className="mt-3 flex flex-wrap gap-3">
                  {["Buy", "Wait", "Don't Buy"].map((decision) => (
                    <label key={decision} className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-slate-200">
                      <input
                        type="radio"
                        checked={draft.decision === decision}
                        onChange={() => patchDraft({ decision })}
                      />
                      {decision}
                    </label>
                  ))}
                </div>
              </div>

              <details className="mt-6 rounded-lg border border-slate-800 bg-slate-900/60 p-5" open={reviewOpen} onToggle={(event) => setReviewOpen(event.currentTarget.open)}>
                <summary className="cursor-pointer text-lg font-semibold text-white">Review</summary>
                <textarea
                  className={`${areaClass} mt-4`}
                  value={reviewText}
                  onChange={(event) => setReviewText(event.target.value)}
                  placeholder="今天结果如何？"
                />
                <button onClick={submitReview} className="mt-3 rounded-lg bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950">
                  Generate Review
                </button>
                {(draft.mistakes || draft.lesson || draft.next_action) && (
                  <div className="mt-4 space-y-3 text-sm leading-6 text-slate-300">
                    <p><span className="text-white">Mistake:</span> {draft.mistakes}</p>
                    <p><span className="text-white">Lesson:</span> {draft.lesson}</p>
                    <p><span className="text-white">Next Rule:</span> {draft.next_action}</p>
                  </div>
                )}
              </details>

              <div className="sticky bottom-4 mt-8 flex justify-end">
                <button onClick={() => saveDraft(true)} className="rounded-lg bg-white px-5 py-3 text-sm font-semibold text-slate-950 shadow-glow">
                  {saving ? "Saving..." : "Save Notebook"}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center text-slate-400">Select or create a notebook.</div>
          )}
        </div>
      </div>
    </section>
  );
}

