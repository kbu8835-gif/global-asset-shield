type ScoreCardProps = {
  label: string;
  value: string | number;
  detail?: string;
  tone?: "red" | "yellow" | "green" | "cyan";
};

const toneClasses = {
  red: "border-red-400/30 bg-red-500/10 text-red-100",
  yellow: "border-amber-300/30 bg-amber-400/10 text-amber-100",
  green: "border-emerald-300/30 bg-emerald-400/10 text-emerald-100",
  cyan: "border-cyan-300/30 bg-cyan-400/10 text-cyan-100",
};

export default function ScoreCard({ label, value, detail, tone = "cyan" }: ScoreCardProps) {
  return (
    <div className={`rounded-lg border p-4 ${toneClasses[tone]}`}>
      <div className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">{label}</div>
      <div className="mt-2 text-3xl font-semibold tracking-normal">{value}</div>
      {detail ? <div className="mt-2 text-sm text-slate-300">{detail}</div> : null}
    </div>
  );
}

