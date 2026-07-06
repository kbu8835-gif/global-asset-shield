type HeroProps = {
  onStart: () => void;
};

export default function Hero({ onStart }: HeroProps) {
  return (
    <section className="mx-auto flex min-h-[520px] max-w-6xl flex-col justify-center px-5 py-16">
      <div className="max-w-4xl">
        <div className="mb-5 inline-flex rounded-full border border-cyan-300/25 bg-cyan-300/10 px-4 py-2 text-sm text-cyan-100">
          AI 投资免疫系统
        </div>
        <h1 className="text-5xl font-semibold leading-tight tracking-normal text-white md:text-7xl">
          Global Asset Shield Agent V4
        </h1>
        <p className="mt-5 text-2xl font-medium text-cyan-100">AI Investment Immune System</p>
        <p className="mt-8 max-w-3xl text-xl leading-8 text-slate-300">
          Not another AI Analyst. An AI immune system that detects toxic investment decisions before you lose money.
        </p>
        <p className="mt-4 text-lg text-slate-400">不是分析师。是投资免疫系统。</p>
        <p className="mt-8 max-w-2xl text-2xl font-semibold text-white">
          别的 AI 告诉你买什么。我们告诉你什么时候不该买。
        </p>
        <p className="mt-6 max-w-2xl text-xl font-semibold text-cyan-100">
          AI doesn't predict markets. It predicts YOUR mistakes.
        </p>
        <p className="mt-2 text-lg text-slate-300">AI 不预测市场。AI 预测你下一次会犯什么错。</p>
        <button
          onClick={onStart}
          className="mt-10 rounded-lg bg-cyan-300 px-6 py-3 text-base font-semibold text-slate-950 transition hover:bg-cyan-200"
        >
          Start Conversation Scan
        </button>
      </div>
    </section>
  );
}
