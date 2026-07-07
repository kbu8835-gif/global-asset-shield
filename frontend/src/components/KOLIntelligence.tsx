import { useEffect, useMemo, useState } from "react";
import {
  captureKolCall,
  captureKolCallsBatch,
  createKolCall,
  createKolProfile,
  deleteKolCall,
  deleteKolProfile,
  getKolCalls,
  getKolDependency,
  getKolProfiles,
  getKolRiskProfile,
  recalculateKolProfile,
  refreshKolCall,
  updateKolCall,
  updateKolProfile,
  type KOLCall,
  type KOLDependency,
  type KOLProfile,
  type KOLRiskProfile,
} from "../api";
import KOLCallTable from "./KOLCallTable";
import KOLDependencyCard from "./KOLDependencyCard";
import KOLProfileCard from "./KOLProfileCard";

const inputClass = "rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300";

export default function KOLIntelligence({ onError }: { onError: (message: string) => void }) {
  const [profiles, setProfiles] = useState<KOLProfile[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [calls, setCalls] = useState<KOLCall[]>([]);
  const [dependency, setDependency] = useState<KOLDependency | null>(null);
  const [riskProfile, setRiskProfile] = useState<KOLRiskProfile | null>(null);
  const [search, setSearch] = useState("");
  const [newName, setNewName] = useState("Crypto Rover");
  const [newAsset, setNewAsset] = useState("PEPE");
  const [callPrice, setCallPrice] = useState("0.00001");
  const [currentPrice, setCurrentPrice] = useState("0.000012");
  const [callText, setCallText] = useState("PEPE will 10x. Last chance.");
  const [captureText, setCaptureText] = useState("$PEPE will 10x. Last chance before moon. 梭哈起飞");
  const [capturePrice, setCapturePrice] = useState("");
  const [captureResult, setCaptureResult] = useState<KOLCall | null>(null);
  const [batchText, setBatchText] = useState("2026-06-30 PEPE 0.00001 PEPE will 10x last chance\n2026-07-03 DOGE 0.12 DOGE moon soon 起飞\n2026-07-06 WIF 1.8 WIF 梭哈 财富自由");
  const [batchResult, setBatchResult] = useState("");

  const selected = profiles.find((profile) => profile.id === selectedId) || profiles[0] || null;

  const loadAll = async (nextId?: number) => {
    const [nextProfiles, nextDependency] = await Promise.all([getKolProfiles(), getKolDependency()]);
    setProfiles(nextProfiles);
    const activeId = nextId || selectedId || nextProfiles[0]?.id || null;
    setSelectedId(activeId);
    setDependency(nextDependency);
    if (activeId) {
      const [nextCalls, nextRiskProfile] = await Promise.all([getKolCalls(activeId), getKolRiskProfile(activeId)]);
      setCalls(nextCalls);
      setRiskProfile(nextRiskProfile);
    } else {
      setCalls([]);
      setRiskProfile(null);
    }
  };

  useEffect(() => {
    loadAll().catch((err) => onError(err instanceof Error ? err.message : "Failed to load KOL Intelligence"));
  }, []);

  const filteredProfiles = useMemo(() => {
    const query = search.toLowerCase();
    return profiles.filter((profile) => profile.name.toLowerCase().includes(query));
  }, [profiles, search]);

  const addProfile = async () => {
    const created = await createKolProfile({ name: newName, twitter_handle: "@example", bio: "Manual KOL profile" });
    await loadAll(created.id);
  };

  const addCall = async () => {
    if (!selected) return;
    await createKolCall({
      kol_id: selected.id,
      asset: newAsset,
      asset_type: "crypto",
      call_price: Number(callPrice),
      current_price: Number(currentPrice),
      source: "manual",
      call_type: "buy",
      call_text: callText,
      call_time: new Date().toISOString(),
    });
    const recalculated = await recalculateKolProfile(selected.id);
    await loadAll(recalculated.id);
  };

  const captureCall = async () => {
    const captured = await captureKolCall({
      kol_id: selected?.id,
      kol_name: selected?.name,
      call_text: captureText,
      asset_type: "crypto",
      call_price: capturePrice ? Number(capturePrice) : null,
    });
    setCaptureResult(captured);
    if (captured.kol_id) {
      const recalculated = await recalculateKolProfile(captured.kol_id);
      await loadAll(recalculated.id);
    } else {
      await loadAll(selected?.id);
    }
  };

  const captureBatch = async () => {
    if (!selected) return;
    const result = await captureKolCallsBatch({
      kol_id: selected.id,
      kol_name: selected.name,
      text: batchText,
      asset_type: "crypto",
    });
    setBatchResult(result.summary);
    await loadAll(selected.id);
  };

  return (
    <section className="mx-auto max-w-7xl px-5 py-8">
      <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
        <aside className="rounded-lg border border-slate-800 bg-slate-950/80 p-4">
          <div className="text-sm uppercase tracking-[0.18em] text-cyan-200">KOL Intelligence</div>
          <h2 className="mt-1 text-xl font-semibold text-white">你正在相信谁？</h2>
          <p className="mt-2 text-sm leading-6 text-slate-400">真正的风险不是这个 KOL 是否看对，而是你是否已经停止独立判断。</p>
          <input className={`${inputClass} mt-4 w-full`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search KOL..." />
          <div className="mt-4 flex gap-2">
            <input className={`${inputClass} min-w-0 flex-1`} value={newName} onChange={(event) => setNewName(event.target.value)} />
            <button onClick={addProfile} className="rounded-lg bg-cyan-300 px-3 py-2 text-sm font-semibold text-slate-950">Add KOL</button>
          </div>
          <div className="mt-4 space-y-2">
            {filteredProfiles.map((profile) => (
              <button
                key={profile.id}
                onClick={async () => {
                  setSelectedId(profile.id);
                  const [nextCalls, nextRiskProfile] = await Promise.all([getKolCalls(profile.id), getKolRiskProfile(profile.id)]);
                  setCalls(nextCalls);
                  setRiskProfile(nextRiskProfile);
                }}
                className={`w-full rounded-lg border p-3 text-left ${selected?.id === profile.id ? "border-cyan-300/50 bg-cyan-300/10" : "border-slate-800 bg-slate-900/60"}`}
              >
                <div className="font-semibold text-white">{profile.name}</div>
                <div className="mt-1 text-xs text-slate-400">Trust {profile.trust_score} · {profile.risk_level} · {profile.total_calls} calls</div>
              </button>
            ))}
          </div>
          {selected ? (
            <button onClick={async () => { await deleteKolProfile(selected.id); await loadAll(); }} className="mt-4 text-sm text-rose-200">
              Delete selected KOL
            </button>
          ) : null}
        </aside>

        <div className="space-y-5">
          <KOLDependencyCard dependency={dependency} />
          <KOLProfileCard
            profile={selected}
            onSave={async (payload) => {
              if (!selected) return;
              await updateKolProfile(selected.id, payload);
              await loadAll(selected.id);
            }}
            onRecalculate={async () => {
              if (!selected) return;
              const next = await recalculateKolProfile(selected.id);
              await loadAll(next.id);
            }}
          />
          {riskProfile ? (
            <div className="rounded-lg border border-rose-300/20 bg-rose-400/10 p-5">
              <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
                <div>
                  <div className="text-xs uppercase tracking-[0.18em] text-rose-200">KOL Risk Profile</div>
                  <h3 className="mt-1 text-2xl font-black text-white">{riskProfile.profile_type}</h3>
                </div>
                <div className="rounded-lg border border-rose-200/30 px-4 py-3 text-center">
                  <div className="text-xs text-rose-100">割韭菜风险</div>
                  <div className="text-3xl font-black text-white">{riskProfile.leek_risk_score}</div>
                </div>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-md bg-slate-950/60 p-3 text-sm text-slate-200">高情绪喊单 {riskProfile.high_emotion_ratio}%</div>
                <div className="rounded-md bg-slate-950/60 p-3 text-sm text-slate-200">历史胜率 {riskProfile.win_rate}%</div>
                <div className="rounded-md bg-slate-950/60 p-3 text-sm text-slate-200">平均 ROI {riskProfile.average_roi}%</div>
              </div>
              {riskProfile.red_flags.length ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {riskProfile.red_flags.map((flag) => (
                    <span key={flag} className="rounded-full border border-rose-200/30 px-3 py-1 text-xs text-rose-100">{flag}</span>
                  ))}
                </div>
              ) : null}
              <p className="mt-4 text-sm leading-6 text-rose-50">{riskProfile.summary}</p>
            </div>
          ) : null}
          <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
            <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
              <div>
                <h3 className="text-lg font-semibold text-white">KOL Capture</h3>
                <p className="mt-1 text-sm leading-6 text-slate-400">粘贴喊单内容，系统自动识别资产、喊单类型、FOMO 和偏差标签。无需 X API。</p>
              </div>
              <span className="rounded-full border border-cyan-300/30 px-3 py-1 text-xs text-cyan-100">Free V1</span>
            </div>
            <textarea
              className={`${inputClass} mt-3 min-h-28 w-full`}
              value={captureText}
              onChange={(event) => setCaptureText(event.target.value)}
              placeholder="$PEPE will 10x. Last chance before moon."
            />
            <div className="mt-3 grid gap-3 md:grid-cols-[180px_auto]">
              <input className={inputClass} value={capturePrice} onChange={(event) => setCapturePrice(event.target.value)} placeholder="Call price 可选" />
              <button onClick={captureCall} className="rounded-lg bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50" disabled={!captureText.trim()}>
                Capture KOL Call
              </button>
            </div>
            {captureResult ? (
              <div className="mt-4 rounded-lg border border-cyan-300/20 bg-cyan-300/10 p-3 text-sm leading-6 text-cyan-50">
                已生成喊单记录：{captureResult.asset} · {captureResult.call_type} · 情绪 {captureResult.emotion_tags || "[]"} · 偏差 {captureResult.bias_tags || "[]"}
              </div>
            ) : null}
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
            <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
              <div>
                <h3 className="text-lg font-semibold text-white">Batch Historical Calls</h3>
                <p className="mt-1 text-sm leading-6 text-slate-400">批量粘贴历史喊单，一行一条：日期 资产 入场价 喊单内容。系统会自动形成这个 KOL 的历史记录。</p>
              </div>
              <button onClick={captureBatch} className="rounded-lg bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50" disabled={!selected || !batchText.trim()}>
                Import History
              </button>
            </div>
            <textarea
              className={`${inputClass} mt-3 min-h-32 w-full font-mono`}
              value={batchText}
              onChange={(event) => setBatchText(event.target.value)}
            />
            {batchResult ? <div className="mt-3 rounded-lg border border-cyan-300/20 bg-cyan-300/10 p-3 text-sm leading-6 text-cyan-50">{batchResult}</div> : null}
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
            <h3 className="text-lg font-semibold text-white">Add Call</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-5">
              <input className={inputClass} value={newAsset} onChange={(event) => setNewAsset(event.target.value)} placeholder="Asset" />
              <input className={inputClass} value={callPrice} onChange={(event) => setCallPrice(event.target.value)} placeholder="Call price" />
              <input className={inputClass} value={currentPrice} onChange={(event) => setCurrentPrice(event.target.value)} placeholder="Current price" />
              <input className={`${inputClass} md:col-span-2`} value={callText} onChange={(event) => setCallText(event.target.value)} placeholder="Call text" />
            </div>
            <button onClick={addCall} className="mt-3 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-950">
              Add Call and Calculate ROI
            </button>
          </div>
          <KOLCallTable
            calls={calls}
            onRefresh={async (id) => {
              await refreshKolCall(id);
              await loadAll(selected?.id);
            }}
            onDelete={async (id) => {
              await deleteKolCall(id);
              await loadAll(selected?.id);
            }}
            onSave={async (id, payload) => {
              await updateKolCall(id, payload);
              if (selected) await recalculateKolProfile(selected.id);
              await loadAll(selected?.id);
            }}
          />
          <div className="rounded-lg border border-cyan-300/20 bg-cyan-300/10 p-5 text-sm leading-6 text-cyan-50">
            别人的观点可以参考，但不能替你承担亏损。如果你说不出自己的失效条件，KOL 的胜率再高也救不了你。
          </div>
        </div>
      </div>
    </section>
  );
}
