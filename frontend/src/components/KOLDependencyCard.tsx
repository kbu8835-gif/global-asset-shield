import type { KOLDependency } from "../api";

export default function KOLDependencyCard({ dependency }: { dependency: KOLDependency | null }) {
  if (!dependency) return null;
  return (
    <div className="rounded-lg border border-amber-300/30 bg-amber-400/10 p-4">
      <div className="text-sm uppercase tracking-[0.16em] text-amber-100">KOL Dependency</div>
      <div className="mt-2 text-4xl font-semibold text-white">{dependency.kol_dependency}</div>
      <p className="mt-3 text-sm leading-6 text-slate-300">{dependency.summary}</p>
      {dependency.top_kol_names.length ? (
        <div className="mt-3 text-xs text-slate-400">Top influences: {dependency.top_kol_names.join(", ")}</div>
      ) : null}
    </div>
  );
}

