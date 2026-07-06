import { useState } from "react";
import { login, register, setToken, type User } from "../api";

type AuthPageProps = {
  onAuthenticated: (user: User) => void;
};

const inputClass = "w-full rounded-lg border border-slate-800 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none focus:border-cyan-300";

export default function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("demo@globalassetshield.ai");
  const [username, setUsername] = useState("Demo User");
  const [password, setPassword] = useState("demo123456");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    setLoading(true);
    setError("");
    try {
      const result =
        mode === "login"
          ? await login({ email, password })
          : await register({ email, username, password });
      setToken(result.access_token);
      onAuthenticated(result.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const demoLogin = async () => {
    setEmail("demo@globalassetshield.ai");
    setPassword("demo123456");
    setMode("login");
    setLoading(true);
    setError("");
    try {
      const result = await login({ email: "demo@globalassetshield.ai", password: "demo123456" });
      setToken(result.access_token);
      onAuthenticated(result.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Demo login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen px-5 py-10 text-slate-100">
      <section className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <div className="text-sm uppercase tracking-[0.24em] text-cyan-200">Global Asset Shield V1.0 Beta</div>
          <h1 className="mt-4 text-5xl font-semibold leading-tight text-white md:text-7xl">
            AI Investment Immune System
          </h1>
          <p className="mt-6 max-w-2xl text-xl leading-8 text-slate-300">
            别的 AI 告诉你买什么。我们告诉你什么时候不该买。
          </p>
          <p className="mt-5 max-w-xl text-base leading-7 text-slate-400">
            登录后，你的 Notebook、Journal、DNA 和 KOL Intelligence 都会和其他用户隔离。你的投资行为模式，只属于你自己。
          </p>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-950/85 p-6 shadow-2xl shadow-cyan-950/20">
          <div className="flex rounded-lg border border-slate-800 bg-slate-900/70 p-1">
            <button
              className={`flex-1 rounded-md px-4 py-2 text-sm font-semibold ${mode === "login" ? "bg-cyan-300 text-slate-950" : "text-slate-300"}`}
              onClick={() => setMode("login")}
            >
              Login
            </button>
            <button
              className={`flex-1 rounded-md px-4 py-2 text-sm font-semibold ${mode === "register" ? "bg-cyan-300 text-slate-950" : "text-slate-300"}`}
              onClick={() => setMode("register")}
            >
              Register
            </button>
          </div>

          <div className="mt-5 space-y-3">
            <input className={inputClass} value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" />
            {mode === "register" ? (
              <input className={inputClass} value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Username" />
            ) : null}
            <input className={inputClass} type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" />
          </div>

          {error ? <div className="mt-4 rounded-lg border border-red-400/40 bg-red-500/10 p-3 text-sm text-red-100">{error}</div> : null}

          <button
            onClick={submit}
            disabled={loading}
            className="mt-5 w-full rounded-lg bg-cyan-300 px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-60"
          >
            {loading ? "Working..." : mode === "login" ? "Login" : "Create Account"}
          </button>
          <button
            onClick={demoLogin}
            disabled={loading}
            className="mt-3 w-full rounded-lg border border-slate-700 px-4 py-3 text-sm font-semibold text-slate-100 hover:border-cyan-300/60 disabled:opacity-60"
          >
            Demo Login
          </button>
        </div>
      </section>
    </main>
  );
}
