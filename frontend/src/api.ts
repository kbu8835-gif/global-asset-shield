const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");
const TOKEN_KEY = "global_asset_shield_token";

export type User = {
  id: number;
  email: string;
  username?: string | null;
  created_at?: string | null;
  is_active: number;
};

export type AuthResponse = {
  user: User;
  access_token: string;
  token_type: string;
};

export type ImmuneReportPayload = {
  asset: string;
  asset_type: "crypto" | "stock";
  user_intent?: string;
  user_text?: string;
  buy_reason?: string;
  risk_awareness?: string;
  worst_case_plan?: string;
  position_size?: string;
  horizon?: string;
};

export type ReviewPayload = {
  journal_id: number;
  current_price: number;
  user_result_text: string;
};

export type JournalEntry = {
  id: number;
  created_at: string;
  asset: string;
  asset_type: string;
  final_decision: string;
  summary: string;
  review_status: string;
};

export type InvestmentDNA = {
  investor_type: string;
  discipline: number;
  patience: number;
  risk_appetite: number;
  kol_dependency: number;
  conviction: number;
  emotion_control: number;
  independent_thinking: number;
  summary: string;
};

export type NotebookListItem = {
  id: number;
  title: string;
  asset: string;
  asset_type: string;
  decision: string;
  status: string;
  entry_type: string;
  created_at: string;
  updated_at: string;
  review_date?: string | null;
};

export type NotebookDetail = NotebookListItem & {
  user_intent?: string | null;
  user_text?: string | null;
  buy_reason?: string | null;
  risk_awareness?: string | null;
  worst_case_plan?: string | null;
  position_size?: string | null;
  notes?: string | null;
  mistakes?: string | null;
  lesson?: string | null;
  next_action?: string | null;
  ai_analysis: Record<string, any>;
  ai_coach: string;
  timeline: Array<{ date: string; event: string }>;
};

export type NotebookUpdate = Partial<{
  title: string;
  decision: string;
  status: string;
  entry_type: string;
  notes: string;
  buy_reason: string;
  user_text: string;
  risk_awareness: string;
  worst_case_plan: string;
  position_size: string;
  mistakes: string;
  lesson: string;
  next_action: string;
  review_date: string;
}>;

export type KOLProfile = {
  id: number;
  name: string;
  twitter_handle?: string | null;
  youtube_channel?: string | null;
  bio?: string | null;
  trust_score: number;
  total_calls: number;
  win_rate_7d: number;
  win_rate_30d: number;
  average_roi_7d: number;
  average_roi_30d: number;
  average_max_drawdown: number;
  risk_level: string;
};

export type KOLCall = {
  id: number;
  kol_id?: number | null;
  kol_name?: string | null;
  asset: string;
  asset_type: string;
  call_time?: string | null;
  call_price?: number | null;
  current_price?: number | null;
  source?: string | null;
  source_url?: string | null;
  call_text?: string | null;
  call_type?: string | null;
  roi_7d?: number | null;
  roi_30d?: number | null;
  current_roi?: number | null;
  result_label?: string | null;
};

export type KOLDependency = {
  kol_dependency: number;
  kol_related_count: number;
  total_decisions: number;
  top_kol_names: string[];
  summary: string;
};

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  const token = getToken();
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options?.headers || {}),
      },
      ...options,
    });
  } catch {
    throw new Error("Backend is not running. Please start backend at http://127.0.0.1:8010");
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearToken();
      window.dispatchEvent(new CustomEvent("auth:expired"));
    }
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function register(payload: { email: string; username?: string; password: string }) {
  return requestJson<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify(payload) });
}

export function login(payload: { email: string; password: string }) {
  return requestJson<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(payload) });
}

export function getMe() {
  return requestJson<User>("/auth/me");
}

export function logout() {
  clearToken();
  return requestJson<{ success: boolean }>("/auth/logout", { method: "POST" }).catch(() => ({ success: true }));
}

export function createImmuneReport(payload: ImmuneReportPayload) {
  return requestJson<any>("/immune/report", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getJournal() {
  return requestJson<JournalEntry[]>("/journal");
}

export function getInvestmentDNA() {
  return requestJson<InvestmentDNA>("/dna");
}

export function reviewJournal(id: number, payload: ReviewPayload) {
  return requestJson<any>(`/journal/${id}/review`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getNotebooks() {
  return requestJson<NotebookListItem[]>("/notebook");
}

export function getNotebook(id: number) {
  return requestJson<NotebookDetail>(`/notebook/${id}`);
}

export function createNotebook(payload: {
  asset: string;
  asset_type?: string;
  title?: string;
  decision?: string;
  notes?: string;
}) {
  return requestJson<NotebookDetail>("/notebook", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateNotebook(id: number, payload: NotebookUpdate) {
  return requestJson<NotebookDetail>(`/notebook/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function reviewNotebook(id: number, payload: { user_result_text: string; current_price?: number }) {
  return requestJson<NotebookDetail>(`/notebook/${id}/review`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getKolProfiles() {
  return requestJson<KOLProfile[]>("/kol/profiles");
}

export function createKolProfile(payload: { name: string; twitter_handle?: string; youtube_channel?: string; bio?: string }) {
  return requestJson<KOLProfile>("/kol/profiles", { method: "POST", body: JSON.stringify(payload) });
}

export function updateKolProfile(id: number, payload: Partial<KOLProfile>) {
  return requestJson<KOLProfile>(`/kol/profiles/${id}`, { method: "PUT", body: JSON.stringify(payload) });
}

export function deleteKolProfile(id: number) {
  return requestJson<{ deleted: boolean }>(`/kol/profiles/${id}`, { method: "DELETE" });
}

export function recalculateKolProfile(id: number) {
  return requestJson<KOLProfile>(`/kol/profiles/${id}/recalculate`, { method: "POST" });
}

export function getKolCalls(kolId?: number) {
  return requestJson<KOLCall[]>(kolId ? `/kol/profiles/${kolId}/calls` : "/kol/calls");
}

export function createKolCall(payload: Partial<KOLCall>) {
  return requestJson<KOLCall>("/kol/calls", { method: "POST", body: JSON.stringify(payload) });
}

export function updateKolCall(id: number, payload: Partial<KOLCall>) {
  return requestJson<KOLCall>(`/kol/calls/${id}`, { method: "PUT", body: JSON.stringify(payload) });
}

export function deleteKolCall(id: number) {
  return requestJson<{ deleted: boolean }>(`/kol/calls/${id}`, { method: "DELETE" });
}

export function refreshKolCall(id: number) {
  return requestJson<KOLCall>(`/kol/calls/${id}/refresh`, { method: "POST" });
}

export function getKolDependency() {
  return requestJson<KOLDependency>("/kol/dependency");
}
