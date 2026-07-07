type ScanProgressProps = {
  visible: boolean;
};

const checks = [
  "连接行情和安全数据",
  "识别 FOMO、KOL 驱动和仓位冲动",
  "生成反方辩手和后悔模拟",
  "保存到 Journal，并更新 Investment DNA",
];

export default function ScanProgress({ visible }: ScanProgressProps) {
  if (!visible) return null;

  return (
    <section className="mx-auto max-w-6xl px-5 py-2">
      <div className="rounded-lg border border-cyan-300/30 bg-cyan-300/10 p-4">
        <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
          <div>
            <div className="font-semibold text-cyan-50">免疫扫描正在运行</div>
            <p className="mt-1 text-sm text-cyan-100/80">如果 Render 正在冷启动，第一次可能需要多等几秒。</p>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-900 md:w-56">
            <div className="h-full w-2/3 animate-pulse rounded-full bg-cyan-300" />
          </div>
        </div>
        <div className="mt-4 grid gap-2 md:grid-cols-4">
          {checks.map((check) => (
            <div key={check} className="rounded-md border border-cyan-200/20 bg-slate-950/50 px-3 py-2 text-xs text-cyan-50">
              {check}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
