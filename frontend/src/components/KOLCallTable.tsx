import type { KOLCall } from "../api";

const inputClass = "w-24 rounded border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-white outline-none focus:border-cyan-300";

export default function KOLCallTable({
  calls,
  onRefresh,
  onDelete,
  onSave,
}: {
  calls: KOLCall[];
  onRefresh: (id: number) => void;
  onDelete: (id: number) => void;
  onSave: (id: number, payload: Partial<KOLCall>) => void;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-950/70">
      <div className="border-b border-slate-800 p-4">
        <h3 className="text-lg font-semibold text-white">Call History</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="bg-slate-900/70 text-xs uppercase text-slate-500">
            <tr>
              {["Asset", "Call Time", "Call Price", "Current Price", "7D ROI", "30D ROI", "Current ROI", "Result", "Source", "Actions"].map((head) => (
                <th key={head} className="px-3 py-3">{head}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {calls.map((call) => (
              <tr key={call.id} className="text-slate-300">
                <td className="px-3 py-3 font-semibold text-white">{call.asset}</td>
                <td className="px-3 py-3">{call.call_time?.slice(0, 10)}</td>
                <td className="px-3 py-3">
                  <input className={inputClass} defaultValue={call.call_price ?? ""} onBlur={(event) => onSave(call.id, { call_price: Number(event.target.value) })} />
                </td>
                <td className="px-3 py-3">
                  <input className={inputClass} defaultValue={call.current_price ?? ""} onBlur={(event) => onSave(call.id, { current_price: Number(event.target.value) })} />
                </td>
                <td className="px-3 py-3">
                  <input className={inputClass} defaultValue={call.roi_7d ?? ""} onBlur={(event) => onSave(call.id, { roi_7d: Number(event.target.value) })} />
                </td>
                <td className="px-3 py-3">
                  <input className={inputClass} defaultValue={call.roi_30d ?? ""} onBlur={(event) => onSave(call.id, { roi_30d: Number(event.target.value) })} />
                </td>
                <td className="px-3 py-3">{call.current_roi ?? "-"}</td>
                <td className="px-3 py-3">{call.result_label ?? "pending"}</td>
                <td className="px-3 py-3">{call.source ?? "manual"}</td>
                <td className="px-3 py-3">
                  <button onClick={() => onRefresh(call.id)} className="mr-2 text-cyan-200">Refresh</button>
                  <button onClick={() => onDelete(call.id)} className="text-rose-200">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
