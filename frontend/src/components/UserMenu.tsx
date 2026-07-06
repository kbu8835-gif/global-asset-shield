import type { User } from "../api";

export default function UserMenu({ user, onLogout }: { user: User; onLogout: () => void }) {
  return (
    <div className="fixed right-4 top-4 z-20 flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-950/90 px-3 py-2 text-sm text-slate-200 shadow-xl shadow-slate-950/30 backdrop-blur">
      <div className="text-right">
        <div className="font-semibold text-white">{user.username || "Investor"}</div>
        <div className="text-xs text-slate-400">{user.email}</div>
      </div>
      <button onClick={onLogout} className="rounded-md border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-100 hover:border-cyan-300/60">
        Logout
      </button>
    </div>
  );
}
