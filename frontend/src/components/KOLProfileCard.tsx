import { useEffect, useState } from "react";
import type { KOLProfile } from "../api";

const inputClass = "rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300";

export default function KOLProfileCard({
  profile,
  onRecalculate,
  onSave,
}: {
  profile: KOLProfile | null;
  onRecalculate: () => void;
  onSave: (payload: Partial<KOLProfile>) => void;
}) {
  const [draft, setDraft] = useState({ name: "", twitter_handle: "", youtube_channel: "", bio: "" });

  useEffect(() => {
    if (!profile) return;
    setDraft({
      name: profile.name,
      twitter_handle: profile.twitter_handle || "",
      youtube_channel: profile.youtube_channel || "",
      bio: profile.bio || "",
    });
  }, [profile]);

  if (!profile) {
    return <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-5 text-slate-400">Select or add a KOL.</div>;
  }
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-5">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
        <div>
          <h3 className="text-3xl font-semibold text-white">{profile.name}</h3>
          <p className="mt-2 text-sm text-slate-400">{profile.twitter_handle || "No Twitter"} · {profile.youtube_channel || "No YouTube"}</p>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">{profile.bio || "别人的观点可以参考，但不能替你承担亏损。"}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => onSave(draft)} className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-950">
            Save Profile
          </button>
          <button onClick={onRecalculate} className="rounded-lg bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950">
            Recalculate Trust
          </button>
        </div>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <input className={inputClass} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} placeholder="Name" />
        <input className={inputClass} value={draft.twitter_handle} onChange={(event) => setDraft({ ...draft, twitter_handle: event.target.value })} placeholder="Twitter / X" />
        <input className={inputClass} value={draft.youtube_channel} onChange={(event) => setDraft({ ...draft, youtube_channel: event.target.value })} placeholder="YouTube" />
        <input className={inputClass} value={draft.bio} onChange={(event) => setDraft({ ...draft, bio: event.target.value })} placeholder="Bio" />
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-4">
        {[
          ["Trust Score：他的历史喊单值得信任吗？", profile.trust_score],
          ["Risk Level", profile.risk_level],
          ["Total Calls", profile.total_calls],
          ["7D Win Rate", `${profile.win_rate_7d}%`],
          ["30D Win Rate", `${profile.win_rate_30d}%`],
          ["Avg 7D ROI", `${profile.average_roi_7d}%`],
          ["Avg 30D ROI", `${profile.average_roi_30d}%`],
          ["Avg Drawdown", `${profile.average_max_drawdown}%`],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
            <div className="text-xs text-slate-500">{label}</div>
            <div className="mt-2 text-xl font-semibold text-white">{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
