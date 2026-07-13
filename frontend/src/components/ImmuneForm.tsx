import type { ImmuneReportPayload } from "../api";

type ImmuneFormProps = {
  form: ImmuneReportPayload;
  loading: boolean;
  onChange: (form: ImmuneReportPayload) => void;
  onSubmit: () => void;
};

const fieldClass =
  "w-full rounded-lg border border-slate-700 bg-slate-950/80 px-3 py-2.5 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-300";

export default function ImmuneForm({ form, loading, onChange, onSubmit }: ImmuneFormProps) {
  const update = (key: keyof ImmuneReportPayload, value: string) => {
    if (key === "asset_type" && value === "cn_stock") {
      onChange({ ...form, asset_type: value as "cn_stock", trade_direction: "long" });
      return;
    }
    onChange({ ...form, [key]: value });
  };

  return (
    <section id="scan" className="mx-auto max-w-6xl px-5 py-8">
      <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-5 shadow-glow">
        <div className="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-end">
          <div>
            <h2 className="text-2xl font-semibold text-white">Run Immune Scan</h2>
            <p className="mt-1 text-sm text-slate-400">资产风险 + 情绪 + 偏差 + 后悔 + 信念，一次跑完整闭环。</p>
          </div>
          <button
            onClick={onSubmit}
            disabled={loading}
            className="rounded-lg bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Scanning..." : "Run Immune Scan"}
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <label className="block">
            <span className="mb-2 block text-xs font-medium uppercase text-slate-400">Asset</span>
            <input className={fieldClass} value={form.asset} onChange={(event) => update("asset", event.target.value)} />
          </label>
          <label className="block">
            <span className="mb-2 block text-xs font-medium uppercase text-slate-400">Asset Type</span>
            <select className={fieldClass} value={form.asset_type} onChange={(event) => update("asset_type", event.target.value)}>
              <option value="crypto">加密货币</option>
              <option value="stock">美股</option>
              <option value="cn_stock">A股</option>
            </select>
          </label>
          {form.asset_type !== "cn_stock" ? (
            <label className="block">
              <span className="mb-2 block text-xs font-medium uppercase text-slate-400">Direction</span>
              <select className={fieldClass} value={form.trade_direction || "long"} onChange={(event) => update("trade_direction", event.target.value)}>
                <option value="long">做多 / 买入</option>
                <option value="short">做空 / 看跌</option>
              </select>
            </label>
          ) : null}
          <label className="block">
            <span className="mb-2 block text-xs font-medium uppercase text-slate-400">User Intent</span>
            <select className={fieldClass} value={form.user_intent} onChange={(event) => update("user_intent", event.target.value)}>
              <option>KOL推荐</option>
              <option>朋友推荐</option>
              <option>涨很多了怕错过</option>
              <option>自己研究</option>
              <option>抄底补仓</option>
            </select>
          </label>
          <label className="block">
            <span className="mb-2 block text-xs font-medium uppercase text-slate-400">Position Size</span>
            <input className={fieldClass} value={form.position_size} onChange={(event) => update("position_size", event.target.value)} />
          </label>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="block">
            <span className="mb-2 block text-xs font-medium uppercase text-slate-400">User Text</span>
            <textarea className={`${fieldClass} min-h-24`} value={form.user_text} onChange={(event) => update("user_text", event.target.value)} />
          </label>
          <label className="block">
            <span className="mb-2 block text-xs font-medium uppercase text-slate-400">Buy Reason</span>
            <textarea className={`${fieldClass} min-h-24`} value={form.buy_reason} onChange={(event) => update("buy_reason", event.target.value)} />
          </label>
          <label className="block">
            <span className="mb-2 block text-xs font-medium uppercase text-slate-400">Risk Awareness</span>
            <input className={fieldClass} value={form.risk_awareness} onChange={(event) => update("risk_awareness", event.target.value)} />
          </label>
          <label className="block">
            <span className="mb-2 block text-xs font-medium uppercase text-slate-400">Worst Case Plan</span>
            <input className={fieldClass} value={form.worst_case_plan} onChange={(event) => update("worst_case_plan", event.target.value)} />
          </label>
          <label className="block">
            <span className="mb-2 block text-xs font-medium uppercase text-slate-400">
              {form.trade_direction === "short" ? "Profit Plan / 下跌后怎么处理" : "Profit Plan / 上涨后怎么处理"}
            </span>
            <input className={fieldClass} value={form.favorable_plan || ""} onChange={(event) => update("favorable_plan", event.target.value)} />
          </label>
          <label className="block">
            <span className="mb-2 block text-xs font-medium uppercase text-slate-400">Sideways Plan / 横盘多久处理</span>
            <input className={fieldClass} value={form.sideways_plan || ""} onChange={(event) => update("sideways_plan", event.target.value)} />
          </label>
          <label className="block md:max-w-xs">
            <span className="mb-2 block text-xs font-medium uppercase text-slate-400">Horizon</span>
            <input className={fieldClass} value={form.horizon} onChange={(event) => update("horizon", event.target.value)} />
          </label>
        </div>
      </div>
    </section>
  );
}
