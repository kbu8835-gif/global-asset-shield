import { useState } from "react";
import type { ImmuneReportPayload } from "../api";

type ConversationScanProps = {
  loading: boolean;
  onSubmit: (payload: ImmuneReportPayload) => void;
};

type Step = "asset" | "intent" | "position" | "worstCase" | "risk" | "ready" | "running";

const intentReasons: Record<string, string> = {
  KOL推荐: "看到KOL推荐，感觉马上要起飞",
  朋友推荐: "朋友推荐，说这个机会不能错过",
  涨很多了怕踏空: "已经涨了很多，我怕再不上车就错过",
  自己研究: "我自己研究后觉得值得关注",
  抄底补仓: "已经跌了很多，我想补仓回本",
};

const intentOptions = ["KOL推荐", "朋友推荐", "涨很多了怕踏空", "自己研究", "抄底补仓"];
const positionOptions = ["5%", "10%", "30%", "50%", "ALL IN"];

function aiBubble(text: string, active = false) {
  return (
    <div className={`flex justify-start ${active ? "opacity-100" : "opacity-80"}`}>
      <div className={`max-w-2xl rounded-lg border px-4 py-3 text-sm leading-6 ${active ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-50" : "border-slate-800 bg-slate-900/80 text-slate-300"}`}>
        <span className="mr-2 text-cyan-300">AI</span>
        {text}
      </div>
    </div>
  );
}

function userBubble(text?: string) {
  if (!text) return null;
  return (
    <div className="flex justify-end">
      <div className="max-w-xl rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white">
        {text}
      </div>
    </div>
  );
}

export default function ConversationScan({ loading, onSubmit }: ConversationScanProps) {
  const [step, setStep] = useState<Step>("asset");
  const [asset, setAsset] = useState("PEPE");
  const [assetType, setAssetType] = useState<"crypto" | "stock">("crypto");
  const [intent, setIntent] = useState("");
  const [positionSize, setPositionSize] = useState("");
  const [worstCasePlan, setWorstCasePlan] = useState("");
  const [riskAwareness, setRiskAwareness] = useState("");

  const assetLabel = asset.trim() || "this asset";
  const ready = step === "ready" || step === "running";

  const buildPayload = (): ImmuneReportPayload => {
    const cleanedAsset = asset.trim() || "PEPE";
    const buyReason = intentReasons[intent] || "我想先做一次免疫扫描";
    const userText = `我想买 ${cleanedAsset}，因为 ${intent || "不清楚"}，准备投入 ${positionSize || "未确定"}，如果跌 40%，我会${worstCasePlan || "还没想清楚"}。`;
    return {
      asset: cleanedAsset,
      asset_type: assetType,
      user_intent: intent,
      user_text: userText,
      buy_reason: buyReason,
      risk_awareness: riskAwareness,
      worst_case_plan: worstCasePlan,
      position_size: positionSize,
      horizon: "短线",
    };
  };

  const startScan = () => {
    setStep("running");
    onSubmit(buildPayload());
  };

  const chipClass =
    "rounded-lg border border-slate-700 bg-slate-950/80 px-4 py-2 text-sm text-slate-100 transition hover:border-cyan-300 hover:bg-cyan-300/10";

  return (
    <section className="mx-auto max-w-6xl px-5 py-8">
      <div className="rounded-lg border border-cyan-300/20 bg-slate-950/80 p-5 shadow-glow">
        <div className="mb-5">
          <div className="text-sm uppercase tracking-[0.18em] text-cyan-200">Conversation Mode</div>
          <h2 className="mt-2 text-2xl font-semibold text-white">AI 对话式免疫扫描</h2>
          <p className="mt-2 text-sm text-slate-400">Less form. More agent. The market changes. Your behavior repeats.</p>
        </div>

        <div className="space-y-4">
          {aiBubble("Today, what asset do you want to test?", step === "asset")}
          <div className="flex justify-end">
            <div className="w-full max-w-xl rounded-lg border border-slate-800 bg-slate-900/70 p-3">
              <div className="grid gap-3 md:grid-cols-[1fr_140px_auto]">
                <input
                  value={asset}
                  onChange={(event) => setAsset(event.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300"
                  placeholder="PEPE"
                />
                <select
                  value={assetType}
                  onChange={(event) => setAssetType(event.target.value as "crypto" | "stock")}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300"
                >
                  <option value="crypto">crypto</option>
                  <option value="stock">stock</option>
                </select>
                <button className={chipClass} onClick={() => setStep("intent")}>
                  Next
                </button>
              </div>
            </div>
          </div>

          {(step !== "asset" || ready) && (
            <>
              {userBubble(`${assetLabel} / ${assetType}`)}
              {aiBubble(`Why do you want to buy ${assetLabel}?`, step === "intent")}
              <div className="flex flex-wrap justify-end gap-2">
                {intentOptions.map((option) => (
                  <button
                    key={option}
                    className={`${chipClass} ${intent === option ? "border-cyan-300 bg-cyan-300/15" : ""}`}
                    onClick={() => {
                      setIntent(option);
                      setStep("position");
                    }}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </>
          )}

          {(step === "position" || step === "worstCase" || step === "risk" || ready) && (
            <>
              {userBubble(intent)}
              {aiBubble("How much of your portfolio are you planning to put in?", step === "position")}
              <div className="flex flex-wrap justify-end gap-2">
                {positionOptions.map((option) => (
                  <button
                    key={option}
                    className={`${chipClass} ${positionSize === option ? "border-cyan-300 bg-cyan-300/15" : ""}`}
                    onClick={() => {
                      setPositionSize(option);
                      setStep("worstCase");
                    }}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </>
          )}

          {(step === "worstCase" || step === "risk" || ready) && (
            <>
              {userBubble(positionSize)}
              {aiBubble(`If ${assetLabel} drops 40% tomorrow, what will you do?`, step === "worstCase")}
              <div className="flex justify-end">
                <div className="flex w-full max-w-xl gap-2">
                  <input
                    value={worstCasePlan}
                    onChange={(event) => setWorstCasePlan(event.target.value)}
                    className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300"
                    placeholder="跌了就再看看"
                  />
                  <button className={chipClass} onClick={() => setStep("risk")} disabled={!worstCasePlan.trim()}>
                    Next
                  </button>
                </div>
              </div>
            </>
          )}

          {(step === "risk" || ready) && (
            <>
              {userBubble(worstCasePlan)}
              {aiBubble(`What is the biggest risk of ${assetLabel}?`, step === "risk")}
              <div className="flex justify-end">
                <div className="flex w-full max-w-xl gap-2">
                  <input
                    value={riskAwareness}
                    onChange={(event) => setRiskAwareness(event.target.value)}
                    className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300"
                    placeholder="不太清楚"
                  />
                  <button className={chipClass} onClick={() => setStep("ready")} disabled={!riskAwareness.trim()}>
                    Done
                  </button>
                </div>
              </div>
            </>
          )}

          {ready && (
            <>
              {userBubble(riskAwareness)}
              {aiBubble(loading || step === "running" ? "Immune scan running..." : "Ready. Start immune scan?", true)}
              <div className="flex justify-end gap-2">
                <button
                  className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-300"
                  onClick={() => {
                    setStep("asset");
                    setIntent("");
                    setPositionSize("");
                    setWorstCasePlan("");
                    setRiskAwareness("");
                  }}
                >
                  Reset
                </button>
                <button
                  className="rounded-lg bg-cyan-300 px-5 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={startScan}
                  disabled={loading || step === "running"}
                >
                  Start Immune Scan
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

