import { useEffect, useMemo, useState } from "react";
import {
  createKolCall,
  createKolProfile,
  deleteKolCall,
  deleteKolProfile,
  getKolCalls,
  getKolDependency,
  getKolProfiles,
  recalculateKolProfile,
  refreshKolCall,
  updateKolCall,
  updateKolProfile,
  type KOLCall,
  type KOLDependency,
  type KOLProfile,
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
  const [search, setSearch] = useState("");
  const [newName, setNewName] = useState("Crypto Rover");
  const [newAsset, setNewAsset] = useState("PEPE");
  const [callPrice, setCallPrice] = useState("0.00001");
  const [currentPrice, setCurrentPrice] = useState("0.000012");
  const [callText, setCallText] = useState("PEPE will 10x. Last chance.");

  const selected = profiles.find((profile) => profile.id === selectedId) || profiles[0] || null;

  const loadAll = async (nextId?: number) => {
    const [nextProfiles, nextDependency] = await Promise.all([getKolProfiles(), getKolDependency()]);
    setProfiles(nextProfiles);
    const activeId = nextId || selectedId || nextProfiles[0]?.id || null;
    setSelectedId(activeId);
    setDependency(nextDependency);
    setCalls(activeId ? await getKolCalls(activeId) : []);
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
                  setCalls(await getKolCalls(profile.id));
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
