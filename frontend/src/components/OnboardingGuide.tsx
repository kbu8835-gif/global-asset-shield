type OnboardingGuideProps = {
  activeView: string;
  onSelectView: (view: "conversation" | "notebook" | "kol" | "dna" | "data") => void;
};

const steps = [
  {
    view: "conversation",
    title: "1. 先做一次免疫扫描",
    text: "输入资产和买入冲动，系统会同时检查资产风险、情绪、偏差和仓位。",
  },
  {
    view: "notebook",
    title: "2. 把决策写进 Notebook",
    text: "别让投资理由停在脑子里。写下来，之后才能复盘。",
  },
  {
    view: "dna",
    title: "3. 看你的 Investment DNA",
    text: "市场每天变，但你的行为会重复。DNA 会指出你最常犯的错。",
  },
  {
    view: "kol",
    title: "4. 管理你正在相信谁",
    text: "记录 KOL 喊单，不是为了崇拜胜率，而是避免把判断外包。",
  },
] as const;

export default function OnboardingGuide({ activeView, onSelectView }: OnboardingGuideProps) {
  return (
    <section className="mx-auto max-w-6xl px-5 pt-5">
      <div className="rounded-lg border border-slate-800 bg-slate-950/75 p-5">
        <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end">
          <div>
            <div className="text-sm uppercase tracking-[0.18em] text-cyan-200">How to use it</div>
            <h2 className="mt-2 text-2xl font-semibold text-white">普通用户只需要按这条线走</h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-slate-400">
            这不是预测价格的工具。它帮你在下单前停一下，在复盘后变聪明一点。
          </p>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-4">
          {steps.map((step) => (
            <button
              key={step.view}
              className={`rounded-lg border p-4 text-left transition ${
                activeView === step.view
                  ? "border-cyan-300/60 bg-cyan-300/10"
                  : "border-slate-800 bg-slate-900/60 hover:border-cyan-300/40"
              }`}
              onClick={() => onSelectView(step.view)}
            >
              <div className="font-semibold text-white">{step.title}</div>
              <p className="mt-2 text-sm leading-6 text-slate-400">{step.text}</p>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
