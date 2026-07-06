type ReviewPanelProps = {
  review: any | null;
};

export default function ReviewPanel({ review }: ReviewPanelProps) {
  if (!review) return null;

  return (
    <section className="mx-auto max-w-6xl px-5 pb-12">
      <div className="rounded-lg border border-amber-300/30 bg-amber-400/10 p-5">
        <div className="text-sm uppercase tracking-[0.18em] text-amber-100">AI Review</div>
        <h2 className="mt-2 text-2xl font-semibold text-white">Journal #{review.journal_id} Review</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-slate-700 bg-slate-950/50 p-4">
            <div className="text-sm text-slate-400">Mistake Type</div>
            <div className="mt-2 text-xl font-semibold text-amber-100">{review.mistake_type}</div>
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-950/50 p-4">
            <div className="text-sm text-slate-400">Original Decision</div>
            <div className="mt-2 text-xl font-semibold text-white">{review.original_decision}</div>
          </div>
        </div>
        <p className="mt-5 text-slate-200">{review.review_result}</p>
        <p className="mt-4 text-cyan-100">{review.lesson}</p>
        <p className="mt-4 rounded-lg border border-slate-700 bg-slate-950/60 p-4 text-white">{review.next_time_rule}</p>
      </div>
    </section>
  );
}

