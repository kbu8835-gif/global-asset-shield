import { useState } from "react";
import type { ImmuneReportPayload } from "../api";

type ConversationScanProps = {
  loading: boolean;
  onSubmit: (payload: ImmuneReportPayload) => void;
};

type Step = "asset" | "direction" | "intent" | "position" | "favorable" | "sideways" | "worstCase" | "risk" | "ready" | "running";

const intentReasons: Record<string, string> = {
  KOL推荐: "看到KOL推荐，感觉马上要起飞",
  朋友推荐: "朋友推荐，说这个机会不能错过",
  涨很多了怕踏空: "已经涨了很多，我怕再不上车就错过",
  自己研究: "我自己研究后觉得值得关注",
  抄底补仓: "已经跌了很多，我想补仓回本",
};

const intentOptions = ["KOL推荐", "朋友推荐", "涨很多了怕踏空", "自己研究", "抄底补仓"];
const directionOptions = [
  { value: "long", label: "做多 / 买入", prompt: "想买入或看涨" },
  { value: "short", label: "做空 / 看跌", prompt: "想做空或看跌" },
] as const;
const positionOptions = ["5%", "10%", "30%", "50%", "ALL IN"];
const worstCaseSuggestions = ["下跌 10% 就止损", "等 24 小时再决定", "不补仓，先复盘"];
const shortWorstCaseSuggestions = ["上涨 10% 就止损", "不加空，先复盘", "等收盘再决定"];
const favorableSuggestions = ["分批止盈，不临时加仓", "继续持有，但移动止损", "先保存利润，再复盘"];
const shortFavorableSuggestions = ["分批止盈空单", "跌到目标位先减仓", "不贪心，移动止盈"];
const sidewaysSuggestions = ["横盘 3 天重新评估", "没有新证据就不加仓", "等成交量确认再行动"];
const riskSuggestions = ["流动性不足", "KOL 喊单情绪过热", "我说不清最大风险"];
const assetTypeLabels = {
  crypto: "加密货币",
  stock: "美股",
  cn_stock: "A股",
} as const;

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
  const [assetType, setAssetType] = useState<"crypto" | "stock" | "cn_stock">("crypto");
  const [tradeDirection, setTradeDirection] = useState<"long" | "short">("long");
  const [intent, setIntent] = useState("");
  const [positionSize, setPositionSize] = useState("");
  const [favorablePlan, setFavorablePlan] = useState("");
  const [sidewaysPlan, setSidewaysPlan] = useState("");
  const [worstCasePlan, setWorstCasePlan] = useState("");
  const [riskAwareness, setRiskAwareness] = useState("");

  const assetLabel = asset.trim() || "this asset";
  const ready = step === "ready" || step === "running";
  const directionEnabled = assetType !== "cn_stock";

  const buildPayload = (): ImmuneReportPayload => {
    const cleanedAsset = asset.trim() || "PEPE";
    const buyReason = intentReasons[intent] || "我想先做一次免疫扫描";
    const effectiveDirection = directionEnabled ? tradeDirection : "long";
    const directionText = directionOptions.find((option) => option.value === effectiveDirection)?.prompt || "想买入或看涨";
    const adverseMove = effectiveDirection === "short" ? "上涨 25%" : "下跌 25%";
    const favorableMove = effectiveDirection === "short" ? "下跌" : "上涨";
    const userText = `我对 ${cleanedAsset} 的方向是${directionText}，因为 ${intent || "不清楚"}，准备投入 ${positionSize || "未确定"}。如果${favorableMove}，我会${favorablePlan || "还没想清楚"}；如果横盘，我会${sidewaysPlan || "还没想清楚"}；如果${adverseMove}，我会${worstCasePlan || "还没想清楚"}。`;
    return {
      asset: cleanedAsset,
      asset_type: assetType,
      trade_direction: effectiveDirection,
      user_intent: intent,
      user_text: userText,
      buy_reason: buyReason,
      risk_awareness: riskAwareness,
      worst_case_plan: worstCasePlan,
      favorable_plan: favorablePlan,
      sideways_plan: sidewaysPlan,
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
          <p className="mt-2 text-sm text-slate-400">不知道填什么也没关系。用默认 PEPE 跑一遍，就能看到完整免疫报告。</p>
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
                  onChange={(event) => {
                    const nextType = event.target.value as "crypto" | "stock" | "cn_stock";
                    setAssetType(nextType);
                    if (nextType === "cn_stock") {
                      setTradeDirection("long");
                    }
                  }}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300"
                >
                  <option value="crypto">加密货币</option>
                  <option value="stock">美股</option>
                  <option value="cn_stock">A股</option>
                </select>
                <button className={chipClass} onClick={() => setStep(assetType === "cn_stock" ? "intent" : "direction")}>
                  Next
                </button>
              </div>
            </div>
          </div>

          {directionEnabled && (step !== "asset" || ready) && (
            <>
              {userBubble(`${assetLabel} / ${assetTypeLabels[assetType]}`)}
              {aiBubble(`What are you planning to do with ${assetLabel}?`, step === "direction")}
              <div className="flex flex-wrap justify-end gap-2">
                {directionOptions.map((option) => (
                  <button
                    key={option.value}
                    className={`${chipClass} ${tradeDirection === option.value ? "border-cyan-300 bg-cyan-300/15" : ""}`}
                    onClick={() => {
                      setTradeDirection(option.value);
                      setStep("intent");
                    }}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </>
          )}

          {(step === "intent" || step === "position" || step === "favorable" || step === "sideways" || step === "worstCase" || step === "risk" || ready) && (
            <>
              {directionEnabled ? userBubble(directionOptions.find((option) => option.value === tradeDirection)?.label) : userBubble(`${assetLabel} / ${assetTypeLabels[assetType]}`)}
              {aiBubble(
                tradeDirection === "short"
                  ? `为什么想做空 ${assetLabel}？`
                  : `为什么想做多 ${assetLabel}？`,
                step === "intent",
              )}
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

          {(step === "position" || step === "favorable" || step === "sideways" || step === "worstCase" || step === "risk" || ready) && (
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
                      setStep("favorable");
                    }}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </>
          )}

          {(step === "favorable" || step === "sideways" || step === "worstCase" || step === "risk" || ready) && (
            <>
              {userBubble(positionSize)}
              {aiBubble(
                tradeDirection === "short"
                  ? `如果 ${assetLabel} 下跌，你准备怎么处理盈利空单？`
                  : `如果 ${assetLabel} 上涨，你准备怎么处理盈利仓位？`,
                step === "favorable",
              )}
              <div className="flex justify-end">
                <div className="w-full max-w-xl">
                  <div className="mb-2 flex flex-wrap justify-end gap-2">
                    {(tradeDirection === "short" ? shortFavorableSuggestions : favorableSuggestions).map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-cyan-300 hover:text-cyan-100"
                        onClick={() => setFavorablePlan(suggestion)}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      value={favorablePlan}
                      onChange={(event) => setFavorablePlan(event.target.value)}
                      className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300"
                      placeholder={tradeDirection === "short" ? "下跌到目标位分批止盈" : "上涨后分批止盈，不临时加仓"}
                    />
                    <button className={chipClass} onClick={() => setStep("sideways")} disabled={!favorablePlan.trim()}>
                      Next
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}

          {(step === "sideways" || step === "worstCase" || step === "risk" || ready) && (
            <>
              {userBubble(favorablePlan)}
              {aiBubble(`如果 ${assetLabel} 横盘，没有结果，你最多等多久？`, step === "sideways")}
              <div className="flex justify-end">
                <div className="w-full max-w-xl">
                  <div className="mb-2 flex flex-wrap justify-end gap-2">
                    {sidewaysSuggestions.map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-cyan-300 hover:text-cyan-100"
                        onClick={() => setSidewaysPlan(suggestion)}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      value={sidewaysPlan}
                      onChange={(event) => setSidewaysPlan(event.target.value)}
                      className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-300"
                      placeholder="横盘 3 天没有新证据就重新评估"
                    />
                    <button className={chipClass} onClick={() => setStep("worstCase")} disabled={!sidewaysPlan.trim()}>
                      Next
                    </button>
                  </div>
                </div>
              </div>
            </>
          )}

          {(step === "worstCase" || step === "risk" || ready) && (
            <>
              {userBubble(sidewaysPlan)}
              {aiBubble(
                tradeDirection === "short"
                  ? `假如 ${assetLabel} 上涨 25%，你怎么办？`
                  : `假如 ${assetLabel} 下跌 25%，你怎么办？`,
                step === "worstCase",
              )}
              <div className="flex justify-end">
                <div className="w-full max-w-xl">
                  <div className="mb-2 flex flex-wrap justify-end gap-2">
                    {(tradeDirection === "short" ? shortWorstCaseSuggestions : worstCaseSuggestions).map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-cyan-300 hover:text-cyan-100"
                        onClick={() => setWorstCasePlan(suggestion)}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
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
              </div>
            </>
          )}

          {(step === "risk" || ready) && (
            <>
              {userBubble(worstCasePlan)}
              {aiBubble(
                tradeDirection === "short"
                  ? `你现在做空 ${assetLabel}，最担心什么风险？`
                  : `你现在做多 ${assetLabel}，最担心什么风险？`,
                step === "risk",
              )}
              <div className="flex justify-end">
                <div className="w-full max-w-xl">
                  <div className="mb-2 flex flex-wrap justify-end gap-2">
                    {riskSuggestions.map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-cyan-300 hover:text-cyan-100"
                        onClick={() => setRiskAwareness(suggestion)}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
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
                    setTradeDirection("long");
                    setPositionSize("");
                    setFavorablePlan("");
                    setSidewaysPlan("");
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
              <p className="text-right text-xs text-slate-500">报告会自动保存到 Journal，并更新你的 Investment DNA。</p>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
