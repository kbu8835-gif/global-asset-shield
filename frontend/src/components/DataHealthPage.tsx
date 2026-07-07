import { useEffect, useState } from "react";
import { getDataHealth, type DataHealth } from "../api";

type DataHealthPageProps = {
  onError: (message: string) => void;
};

function statusStyle(status: string) {
  if (status === "connected") return "border-emerald-300/40 bg-emerald-400/10 text-emerald-100";
  if (status === "needs_balance") return "border-amber-300/40 bg-amber-400/10 text-amber-100";
  if (status === "fallback") return "border-cyan-300/40 bg-cyan-400/10 text-cyan-100";
  return "border-rose-300/40 bg-rose-400/10 text-rose-100";
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    connected: "Connected",
    degraded: "Degraded",
    fallback: "Fallback",
    needs_balance: "Needs Balance",
    down: "Down",
  };
  return labels[status] || status;
}

export default function DataHealthPage({ onError }: DataHealthPageProps) {
  const [health, setHealth] = useState<DataHealth | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    onError("");
    try {
      setHealth(await getDataHealth());
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to load data health");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <section className="mx-auto max-w-6xl px-5 py-8">
      <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-6 shadow-glow">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <div className="text-sm uppercase tracking-[0.18em] text-cyan-200">Data Source Health</div>
            <h2 className="mt-2 text-3xl font-semibold text-white">系统现在连上了哪些真实数据？</h2>
            <p className="mt-3 max-w-3xl text-slate-300">
              这不是后台状态表。它告诉你：报告里哪些来自真实联网数据，哪些正在用 fallback 保护用户体验。
            </p>
          </div>
          <button
            className="rounded-md bg-cyan-300 px-5 py-3 text-sm font-bold text-slate-950 hover:bg-cyan-200 disabled:opacity-60"
            disabled={loading}
            onClick={load}
          >
            {loading ? "Checking..." : "Refresh Health"}
          </button>
        </div>

        {health ? (
          <div className="mt-6 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
            <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
              <div>
                <div className="text-sm text-slate-400">Overall</div>
                <div className="mt-1 text-2xl font-black text-white">{statusLabel(health.overall_status)}</div>
              </div>
              <p className="max-w-2xl text-slate-300">{health.summary}</p>
            </div>
          </div>
        ) : null}
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        {(health?.sources || []).map((source) => (
          <div key={source.name} className="rounded-lg border border-slate-800 bg-slate-900/70 p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold text-white">{source.name}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-300">{source.detail}</p>
              </div>
              <span className={`shrink-0 rounded-full border px-3 py-1 text-xs font-semibold ${statusStyle(source.status)}`}>
                {statusLabel(source.status)}
              </span>
            </div>
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              <div className="rounded-md border border-slate-800 bg-slate-950/60 px-3 py-2">
                <div className="text-xs text-slate-500">Live Data</div>
                <div className="mt-1 font-semibold text-white">{source.live_data ? "真实联网数据" : "未使用真实数据"}</div>
              </div>
              <div className="rounded-md border border-slate-800 bg-slate-950/60 px-3 py-2">
                <div className="text-xs text-slate-500">Fallback</div>
                <div className="mt-1 font-semibold text-white">{source.fallback_available ? "可自动兜底" : "无兜底"}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
