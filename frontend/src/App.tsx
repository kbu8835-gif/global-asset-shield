import { useEffect, useRef, useState } from "react";
import {
  clearToken,
  createImmuneReport,
  getMe,
  getInvestmentDNA,
  getInvestmentJournalHealth,
  getToken,
  logout,
  type ImmuneReportPayload,
  type InvestmentJournalHealth,
  type InvestmentDNA as InvestmentDNAType,
  type User,
} from "./api";
import AuthPage from "./components/AuthPage";
import Hero from "./components/Hero";
import ConversationScan from "./components/ConversationScan";
import DataHealthPage from "./components/DataHealthPage";
import FriendlyError from "./components/FriendlyError";
import ImmuneForm from "./components/ImmuneForm";
import ImmuneReport from "./components/ImmuneReport";
import InvestmentDNA from "./components/InvestmentDNA";
import KOLIntelligence from "./components/KOLIntelligence";
import NotebookWorkspace from "./components/NotebookWorkspace";
import OnboardingGuide from "./components/OnboardingGuide";
import ScanProgress from "./components/ScanProgress";
import UserMenu from "./components/UserMenu";

const defaultForm: ImmuneReportPayload = {
  asset: "PEPE",
  asset_type: "crypto",
  trade_direction: "long",
  user_intent: "KOL推荐",
  user_text: "这个币已经涨了40%，我怕踏空，想梭哈",
  buy_reason: "看到KOL推荐，感觉马上要起飞",
  risk_awareness: "不太清楚风险",
  worst_case_plan: "跌了就再看看",
  position_size: "50%",
  horizon: "短线",
};

export default function App() {
  const scanRef = useRef<HTMLDivElement>(null);
  const reportRef = useRef<HTMLDivElement>(null);
  const [mainView, setMainView] = useState<"conversation" | "notebook" | "kol" | "dna" | "data">("conversation");
  const [scanMode, setScanMode] = useState<"conversation" | "advanced">("conversation");
  const [form, setForm] = useState<ImmuneReportPayload>(defaultForm);
  const [report, setReport] = useState<any | null>(null);
  const [notebookFocusId, setNotebookFocusId] = useState<number | null>(null);
  const [dna, setDna] = useState<InvestmentDNAType | null>(null);
  const [health, setHealth] = useState<InvestmentJournalHealth | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [loadingDNA, setLoadingDNA] = useState(false);
  const [bootingAuth, setBootingAuth] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState("");

  const loadDNA = async () => {
    setLoadingDNA(true);
    try {
      setDna(await getInvestmentDNA());
      if (user?.id) {
        setHealth(await getInvestmentJournalHealth(String(user.id)));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Investment DNA");
    } finally {
      setLoadingDNA(false);
    }
  };

  const submitScan = async (payload: ImmuneReportPayload) => {
    setLoadingReport(true);
    setError("");
    try {
      const nextReport = await createImmuneReport(payload);
      setReport(nextReport);
      await loadDNA();
      window.setTimeout(() => reportRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create immune report");
    } finally {
      setLoadingReport(false);
    }
  };

  const runScan = async () => {
    await submitScan(form);
  };

  const openReportNotebook = (id: number) => {
    setNotebookFocusId(id);
    setMainView("notebook");
    window.setTimeout(() => scanRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
  };

  const handleAuthenticated = (nextUser: User) => {
    setUser(nextUser);
    setError("");
  };

  const handleLogout = async () => {
    await logout();
    clearToken();
    setUser(null);
    setReport(null);
    setDna(null);
    setHealth(null);
    setError("");
  };

  useEffect(() => {
    const bootstrap = async () => {
      if (!getToken()) {
        setBootingAuth(false);
        return;
      }
      try {
        setUser(await getMe());
      } catch {
        clearToken();
        setUser(null);
      } finally {
        setBootingAuth(false);
      }
    };
    bootstrap();
    const expire = () => {
      setUser(null);
      setError("Session expired. Please login again.");
    };
    window.addEventListener("auth:expired", expire);
    return () => window.removeEventListener("auth:expired", expire);
  }, []);

  useEffect(() => {
    if (!user) return;
    loadDNA();
  }, [user?.id]);

  if (bootingAuth) {
    return (
      <main className="flex min-h-screen items-center justify-center text-slate-100">
        <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-6 text-sm text-slate-300">Loading secure workspace...</div>
      </main>
    );
  }

  if (!user) {
    return <AuthPage onAuthenticated={handleAuthenticated} />;
  }

  return (
    <main className="min-h-screen text-slate-100">
      <UserMenu user={user} onLogout={handleLogout} />
      <Hero onStart={() => scanRef.current?.scrollIntoView({ behavior: "smooth" })} />
      <OnboardingGuide activeView={mainView} onSelectView={setMainView} />
      <section ref={scanRef} className="mx-auto max-w-6xl px-5 pt-2">
        <div className="flex flex-wrap gap-2 rounded-lg border border-slate-800 bg-slate-950/80 p-1">
          {[
            ["conversation", "Conversation"],
            ["notebook", "Notebook"],
            ["kol", "KOL"],
            ["dna", "DNA"],
            ["data", "Data"],
          ].map(([key, label]) => (
            <button
              key={key}
              className={`rounded-md px-4 py-2 text-sm font-semibold ${mainView === key ? "bg-cyan-300 text-slate-950" : "text-slate-300 hover:text-white"}`}
              onClick={() => setMainView(key as "conversation" | "notebook" | "kol" | "dna" | "data")}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      {mainView === "conversation" ? (
        <>
          <section className="mx-auto max-w-6xl px-5 pt-4">
            <div className="inline-flex rounded-lg border border-slate-800 bg-slate-950/80 p-1">
              <button
                className={`rounded-md px-4 py-2 text-sm font-semibold ${scanMode === "conversation" ? "bg-cyan-300 text-slate-950" : "text-slate-300 hover:text-white"}`}
                onClick={() => setScanMode("conversation")}
              >
                Conversation Mode
              </button>
              <button
                className={`rounded-md px-4 py-2 text-sm font-semibold ${scanMode === "advanced" ? "bg-cyan-300 text-slate-950" : "text-slate-300 hover:text-white"}`}
                onClick={() => setScanMode("advanced")}
              >
                Advanced Form
              </button>
            </div>
          </section>
          {scanMode === "conversation" ? (
            <ConversationScan loading={loadingReport} onSubmit={submitScan} />
          ) : (
            <ImmuneForm form={form} loading={loadingReport} onChange={setForm} onSubmit={runScan} />
          )}
          <ScanProgress visible={loadingReport} />
          <FriendlyError message={error} />
          <div ref={reportRef}>
            <ImmuneReport report={report} onOpenNotebook={openReportNotebook} />
          </div>
        </>
      ) : null}

      {mainView === "notebook" ? (
        <>
          <FriendlyError message={error} />
          <NotebookWorkspace onError={setError} focusNotebookId={notebookFocusId} />
        </>
      ) : null}

      {mainView === "kol" ? (
        <>
          <FriendlyError message={error} />
          <KOLIntelligence onError={setError} />
        </>
      ) : null}

      {mainView === "dna" ? (
        <>
          <FriendlyError message={error} />
          <InvestmentDNA dna={dna} health={health} loading={loadingDNA} onRefresh={loadDNA} />
        </>
      ) : null}

      {mainView === "data" ? (
        <>
          <FriendlyError message={error} />
          <DataHealthPage onError={setError} />
        </>
      ) : null}
    </main>
  );
}
