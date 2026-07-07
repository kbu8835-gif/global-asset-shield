import { useEffect, useMemo, useState } from "react";
import {
  createNotebook,
  deleteNotebook,
  getNotebook,
  getNotebooks,
  reviewNotebook,
  updateNotebook,
  type NotebookDetail,
  type NotebookListItem,
} from "../api";

type NotebookWorkspaceProps = {
  onError: (message: string) => void;
  focusNotebookId?: number | null;
};

const inputClass =
  "w-full rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300";
const areaClass =
  "min-h-28 w-full rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-3 text-sm leading-6 text-white outline-none focus:border-cyan-300";
const pillClass = "rounded-full border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-300";

function formatDate(value?: string | null) {
  if (!value) return "";
  return new Date(value).toISOString().slice(0, 10);
}

function decisionIcon(decision: string) {
  if (decision.includes("Don't")) return "🔴";
  if (decision.includes("Buy") || decision.includes("Small") || decision.includes("Short")) return "🟢";
  return "🟡";
}

function statusTone(status: string) {
  if (status === "Reviewed") return "border-emerald-300/40 bg-emerald-400/10 text-emerald-100";
  if (status === "Archived") return "border-slate-600 bg-slate-800 text-slate-300";
  return "border-cyan-300/40 bg-cyan-400/10 text-cyan-100";
}

function directionLabel(direction?: string | null) {
  if (direction === "short") return "做空";
  if (direction === "watch") return "观望";
  return "做多";
}

function decisionOptions(direction?: string | null) {
  if (direction === "short") return ["Short", "Wait", "Don't Short"];
  return ["Buy", "Wait", "Don't Buy"];
}

function scoreBlock(label: string, value?: number) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <div className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value ?? 0}</div>
    </div>
  );
}

function formatSaveState(saving: boolean, savedAt: string) {
  if (saving) return "正在保存...";
  if (!savedAt) return "已开启自动保存";
  return `已保存 ${savedAt}`;
}

export default function NotebookWorkspace({ onError, focusNotebookId }: NotebookWorkspaceProps) {
  const [items, setItems] = useState<NotebookListItem[]>([]);
  const [selected, setSelected] = useState<NotebookDetail | null>(null);
  const [draft, setDraft] = useState<NotebookDetail | null>(null);
  const [search, setSearch] = useState("");
  const [assetFilter, setAssetFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [sort, setSort] = useState("updated");
  const [saving, setSaving] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState("");
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
    if (!focusNotebookId) return;
    openNotebook(focusNotebookId).catch((err) => onError(err instanceof Error ? err.message : "Failed to open notebook"));
  }, [focusNotebookId]);

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
    draft?.trade_direction,
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
      asset: draft.asset,
      asset_type: draft.asset_type,
      title: draft.title,
      notes: draft.notes || "",
      buy_reason: draft.buy_reason || "",
      risk_awareness: draft.risk_awareness || "",
      worst_case_plan: draft.worst_case_plan || "",
      decision: draft.decision,
      status: draft.status,
      trade_direction: draft.trade_direction || "long",
    });
    setSelected(updated);
    setDraft(updated);
    setLastSavedAt(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
    await loadList();
    if (showState) setSaving(false);
  };

  const createBlank = async () => {
    const created = await createNotebook({
      asset: "NEW",
      asset_type: "crypto",
      trade_direction: "long",
      title: `投资笔记 ${new Date().toISOString().slice(0, 10)}`,
      decision: "Wait",
      notes: "我正在考虑这笔交易，还没有下结论。",
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

  const removeNotebook = async (item: NotebookListItem) => {
    const confirmed = window.confirm(`确定删除「${item.title}」吗？这会真正删除这条笔记，不能撤销。`);
    if (!confirmed) return;
    await deleteNotebook(item.id);
    if (draft?.id === item.id) {
      setSelected(null);
      setDraft(null);
    }
    const nextItems = await getNotebooks();
    setItems(nextItems);
    if (draft?.id === item.id && nextItems[0]) {
      await openNotebook(nextItems[0].id);
    }
  };

  const stats = useMemo(() => {
    const open = items.filter((item) => item.status === "Open").length;
    const reviewed = items.filter((item) => item.status === "Reviewed").length;
    const archived = items.filter((item) => item.status === "Archived").length;
    return { total: items.length, open, reviewed, archived };
  }, [items]);

  return (
    <section className="mx-auto max-w-7xl px-5 py-8">
      <div className="grid min-h-[760px] gap-5 lg:grid-cols-[360px_1fr]">
        <aside className="rounded-lg border border-slate-800 bg-slate-950/80 p-4">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-sm uppercase tracking-[0.18em] text-cyan-200">Notebook</div>
              <h2 className="mt-1 text-xl font-semibold text-white">AI Investment Notebook</h2>
              <p className="mt-1 text-xs leading-5 text-slate-500">这不是交易流水。这里记录你为什么动手、何时停手、事后学到了什么。</p>
            </div>
            <button onClick={createBlank} className="rounded-lg bg-cyan-300 px-3 py-2 text-sm font-semibold text-slate-950">
              New
            </button>
          </div>
          <div className="mb-4 grid grid-cols-4 gap-2">
            {[
              ["全部", stats.total],
              ["Open", stats.open],
              ["复盘", stats.reviewed],
              ["归档", stats.archived],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-800 bg-slate-900/60 p-2 text-center">
                <div className="text-xs text-slate-500">{label}</div>
                <div className="mt-1 text-lg font-semibold text-white">{value}</div>
              </div>
            ))}
          </div>
          <input className={inputClass} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索资产、理由或决定..." />
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
            {filtered.length ? filtered.map((item) => (
              <div
                key={item.id}
                className={`w-full rounded-lg border p-3 text-left transition ${
                  draft?.id === item.id ? "border-cyan-300/50 bg-cyan-300/10" : "border-slate-800 bg-slate-900/50 hover:border-slate-600"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <button className="min-w-0 flex-1 text-left" onClick={() => openNotebook(item.id)}>
                    <div className="flex items-center gap-2 text-white">
                      <span>📄</span>
                      <span className="truncate font-semibold">{item.title}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                      <span>{item.asset}</span>
                      <span>{directionLabel(item.trade_direction)}</span>
                      <span className={`rounded-full border px-2 py-0.5 ${statusTone(item.status)}`}>{item.status}</span>
                    </div>
                    <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                      <span>{formatDate(item.updated_at)}</span>
                      <span>{decisionIcon(item.decision)} {item.decision}</span>
                    </div>
                  </button>
                  <button
                    className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-400 hover:border-red-300/60 hover:text-red-100"
                    onClick={() => removeNotebook(item).catch((err) => onError(err instanceof Error ? err.message : "Failed to delete notebook"))}
                    title="Delete notebook"
                  >
                    Delete
                  </button>
                </div>
              </div>
            )) : (
              <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/40 p-5 text-sm leading-6 text-slate-400">
                还没有笔记。你可以先跑一次免疫扫描，或新建一条投资想法。真正有用的投资记录，应该写在下单之前。
              </div>
            )}
          </div>
        </aside>

        <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-6">
          {draft ? (
            <div className="mx-auto max-w-3xl">
              <div className="mb-6">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                  <div className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusTone(draft.status)}`}>{draft.status}</div>
                  <div className="text-xs text-slate-500">{formatSaveState(saving, lastSavedAt)}</div>
                </div>
                <input
                  className="w-full bg-transparent text-4xl font-semibold text-white outline-none"
                  value={draft.title}
                  onChange={(event) => patchDraft({ title: event.target.value })}
                />
                <div className="mt-2 text-sm text-slate-400">
                  {draft.asset} · {draft.asset_type} · {directionLabel(draft.trade_direction)} · {formatDate(draft.created_at)}
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
                  <div className="text-sm text-slate-400">资产与方向</div>
                  <div className="mt-3 grid gap-3 md:grid-cols-[1fr_130px_130px]">
                    <input className={inputClass} value={draft.asset} onChange={(event) => patchDraft({ asset: event.target.value.toUpperCase() })} />
                    <select
                      className={inputClass}
                      value={draft.asset_type}
                      onChange={(event) => {
                        const assetType = event.target.value;
                        patchDraft({ asset_type: assetType, trade_direction: assetType === "cn_stock" ? "long" : draft.trade_direction });
                      }}
                    >
                      <option value="crypto">Crypto</option>
                      <option value="stock">美股</option>
                      <option value="cn_stock">A股</option>
                    </select>
                    {draft.asset_type !== "cn_stock" ? (
                      <select className={inputClass} value={draft.trade_direction || "long"} onChange={(event) => patchDraft({ trade_direction: event.target.value })}>
                        <option value="long">做多</option>
                        <option value="short">做空</option>
                      </select>
                    ) : (
                      <span className={`${pillClass} flex items-center justify-center`}>A股默认做多</span>
                    )}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                  <div className="text-sm text-slate-400">AI 给出的风险建议</div>
                  <div className="mt-2 text-3xl font-semibold text-white">{decisionIcon(draft.decision)} {draft.decision}</div>
                </div>
              </div>

              <div className="space-y-5">
                <label className="block">
                  <div className="mb-2 text-sm font-semibold text-white">1. 今天为什么想到它？</div>
                  <textarea className={areaClass} value={draft.notes || ""} onChange={(event) => patchDraft({ notes: event.target.value })} placeholder="例如：看到 KOL 提到、朋友推荐、自己研究、价格突然上涨..." />
                </label>
                <label className="block">
                  <div className="mb-2 text-sm font-semibold text-white">2. 我的交易逻辑</div>
                  <textarea className={areaClass} value={draft.buy_reason || ""} onChange={(event) => patchDraft({ buy_reason: event.target.value })} placeholder="如果做多，为什么会上涨？如果做空，为什么会下跌？" />
                </label>
                <label className="block">
                  <div className="mb-2 text-sm font-semibold text-white">3. 什么情况说明我错了？</div>
                  <textarea className={areaClass} value={draft.risk_awareness || ""} onChange={(event) => patchDraft({ risk_awareness: event.target.value })} placeholder="写不出这一条，就不要急着下单。" />
                </label>
                <label className="block">
                  <div className="mb-2 text-sm font-semibold text-white">4. 如果亏损，我怎么退出？</div>
                  <textarea className={areaClass} value={draft.worst_case_plan || ""} onChange={(event) => patchDraft({ worst_case_plan: event.target.value })} placeholder="例如：下跌/上涨到某个比例、跌破某个条件、情绪上头时先停止交易。" />
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
                {(draft.ai_analysis.risk?.score ?? 0) === 0 ? (
                  <p className="mt-4 text-sm leading-6 text-slate-400">这是一条手动笔记，还没有完整免疫扫描。建议在 Conversation 里跑一次扫描，再回到这里复盘。</p>
                ) : null}
              </div>

              <div className="mt-6 rounded-lg border border-cyan-300/20 bg-cyan-300/10 p-5">
                <h3 className="text-lg font-semibold text-white">AI Coach</h3>
                <p className="mt-3 whitespace-pre-line leading-7 text-cyan-50">{draft.ai_coach}</p>
              </div>

              <div className="mt-6 rounded-lg border border-slate-800 bg-slate-900/60 p-5">
                <h3 className="text-lg font-semibold text-white">我的最终决定</h3>
                <p className="mt-2 text-sm text-slate-400">AI 可以提醒风险，但最终决定属于你。写下来，之后才有东西可以复盘。</p>
                <div className="mt-3 flex flex-wrap gap-3">
                  {decisionOptions(draft.trade_direction).map((decision) => (
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
                <summary className="cursor-pointer text-lg font-semibold text-white">复盘：结果发生后再打开</summary>
                <textarea
                  className={`${areaClass} mt-4`}
                  value={reviewText}
                  onChange={(event) => setReviewText(event.target.value)}
                  placeholder="结果如何？我当时哪里想错了？有没有违反自己的规则？"
                />
                <button onClick={submitReview} className="mt-3 rounded-lg bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950">
                  AI 复盘
                </button>
                {(draft.mistakes || draft.lesson || draft.next_action) && (
                  <div className="mt-4 space-y-3 text-sm leading-6 text-slate-300">
                    <p><span className="text-white">错误类型：</span>{draft.mistakes}</p>
                    <p><span className="text-white">教训：</span>{draft.lesson}</p>
                    <p><span className="text-white">下一条规则：</span>{draft.next_action}</p>
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
