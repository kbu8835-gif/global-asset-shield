import ScoreCard from "./ScoreCard";

type ImmuneReportProps = {
  report: any | null;
};

function listItems(items: unknown): string[] {
  return Array.isArray(items) ? items.map((item) => String(item)) : [];
}

function normalizeBiases(raw: unknown): Array<Record<string, string>> {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    if (typeof item === "string") {
      return { bias_type: item, severity: "", warning: item, better_question: "" };
    }
    return item as Record<string, string>;
  });
}

function toneForDecision(decision: string): "red" | "yellow" | "green" {
  if (decision.includes("Don't")) return "red";
  if (decision.includes("Small")) return "green";
  return "yellow";
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-5">
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <div className="mt-4 text-sm leading-6 text-slate-300">{children}</div>
    </div>
  );
}

export default function ImmuneReport({ report }: ImmuneReportProps) {
  if (!report) {
    return (
      <section className="mx-auto max-w-6xl px-5 py-8">
        <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-8 text-center text-slate-400">
          Run a scan to see the immune report.
        </div>
      </section>
    );
  }

  const biases = normalizeBiases(report.bias_detection?.biases);

  return (
    <section className="mx-auto max-w-6xl px-5 py-8">
      <div className="mb-5 rounded-lg border border-slate-800 bg-slate-950/80 p-6 shadow-glow">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
          <div>
            <div className="text-sm uppercase tracking-[0.18em] text-slate-500">Immune Report #{report.report_id}</div>
            <h2 className="mt-2 text-3xl font-semibold text-white">
              {report.asset} <span className="text-base font-medium text-slate-400">/ {report.asset_type}</span>
            </h2>
            <p className="mt-3 max-w-3xl text-slate-300">{report.summary}</p>
          </div>
          <div className={`rounded-lg border p-5 text-center ${toneForDecision(report.final_decision) === "red" ? "border-red-400/40 bg-red-500/15" : toneForDecision(report.final_decision) === "green" ? "border-emerald-300/40 bg-emerald-500/15" : "border-amber-300/40 bg-amber-400/15"}`}>
            <div className="text-sm text-slate-400">Final Decision</div>
            <div className="mt-2 text-4xl font-bold text-white">{report.final_decision}</div>
          </div>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <ScoreCard label="Risk" value={report.risk_scan?.risk_score} detail={report.risk_scan?.risk_level} tone="red" />
          <ScoreCard label="Emotion" value={report.emotion_scan?.emotion_score} detail={report.emotion_scan?.emotion_level} tone="yellow" />
          <ScoreCard label="Bias" value={report.bias_detection?.bias_score} detail={`${biases.length} detected`} tone="cyan" />
          <ScoreCard label="Conviction" value={report.conviction_score?.score} detail={report.conviction_score?.level} tone="green" />
        </div>
        <div className="mt-5 rounded-lg border border-slate-800 bg-slate-900/70 p-4">
          <div className="text-sm font-semibold text-white">Position Advice</div>
          <p className="mt-2 text-slate-300">{report.position_advice}</p>
          <p className="mt-2 text-slate-400">{report.decision_reason}</p>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Section title="A. Risk Scan">
          <p className="font-semibold text-white">{report.risk_scan?.risk_score} / {report.risk_scan?.risk_level}</p>
          <ul className="mt-3 space-y-2">
            {listItems(report.risk_scan?.risk_reasons).map((item, index) => <li key={index}>- {item}</li>)}
          </ul>
        </Section>
        <Section title="B. Emotion Scan">
          <p className="font-semibold text-white">{report.emotion_scan?.emotion_score} / {report.emotion_scan?.emotion_level}</p>
          <p className="mt-3">Detected: {listItems(report.emotion_scan?.detected_emotions).join(", ")}</p>
          <p className="mt-3 text-cyan-100">{report.emotion_scan?.intervention_advice}</p>
        </Section>
        <Section title="C. Bias Detector">
          <p className="font-semibold text-white">Bias Score: {report.bias_detection?.bias_score}</p>
          <div className="mt-3 space-y-3">
            {biases.map((bias, index) => (
              <div key={index} className="rounded-lg border border-slate-700 bg-slate-950/60 p-3">
                <div className="font-semibold text-white">{bias.bias_type} {bias.severity}</div>
                <p className="mt-1 text-rose-100">{bias.warning}</p>
                {bias.better_question ? <p className="mt-1 text-slate-400">Better question: {bias.better_question}</p> : null}
              </div>
            ))}
          </div>
        </Section>
        <Section title="D. Devil's Advocate">
          <p className="font-semibold text-rose-100">Against Buying</p>
          <ul className="mt-2 space-y-2">{listItems(report.devil_advocate?.against_buying).map((item, index) => <li key={index}>- {item}</li>)}</ul>
          <p className="mt-4 font-semibold text-emerald-100">Supporting Case</p>
          <ul className="mt-2 space-y-2">{listItems(report.devil_advocate?.supporting_case).map((item, index) => <li key={index}>- {item}</li>)}</ul>
          <p className="mt-4 font-semibold text-cyan-100">Killer Questions</p>
          <ul className="mt-2 space-y-2">{listItems(report.devil_advocate?.killer_questions).map((item, index) => <li key={index}>- {item}</li>)}</ul>
        </Section>
        <Section title="Regret Simulator">
          <div className="space-y-3">
            <p><span className="text-white">Buy and up:</span> {report.regret_simulation?.buy_and_up}</p>
            <p><span className="text-white">Buy and down:</span> {report.regret_simulation?.buy_and_down}</p>
            <p><span className="text-white">Not buy and up:</span> {report.regret_simulation?.not_buy_and_up}</p>
            <p><span className="text-white">Not buy and down:</span> {report.regret_simulation?.not_buy_and_down}</p>
            <p className="text-amber-100">{report.regret_simulation?.likely_regret_pattern}</p>
            <p className="text-rose-100">{report.regret_simulation?.behavior_warning}</p>
          </div>
        </Section>
        <Section title="Conviction Score">
          <p className="font-semibold text-white">{report.conviction_score?.score} / {report.conviction_score?.level}</p>
          <p className="mt-3 font-semibold text-rose-100">Problems</p>
          <ul className="mt-2 space-y-2">{listItems(report.conviction_score?.problems).map((item, index) => <li key={index}>- {item}</li>)}</ul>
          <p className="mt-4 font-semibold text-cyan-100">Improvement Questions</p>
          <ul className="mt-2 space-y-2">{listItems(report.conviction_score?.improvement_questions).map((item, index) => <li key={index}>- {item}</li>)}</ul>
        </Section>
      </div>
    </section>
  );
}

