from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import APP_CONCEPT, APP_DESCRIPTION, APP_NAME, APP_VERSION, CORS_ORIGINS
from auth import get_current_user, get_current_user_or_demo, login_user, register_user
from database import init_db, is_database_connected
from immune.dna import build_investment_dna
from immune.journal import get_entry, list_entries
from immune.kol_intelligence import (
    build_kol_behavior_profile,
    calculate_user_kol_dependency,
    capture_kol_call,
    capture_kol_calls_batch,
    create_kol_call,
    create_kol_profile,
    delete_kol_call,
    delete_kol_profile,
    get_kol_call,
    get_kol_profile,
    list_kol_calls,
    list_kol_profiles,
    recalculate_kol_profile_stats,
    refresh_kol_call,
    update_kol_call,
    update_kol_profile,
)
from immune.notebook import create_notebook, get_notebook, list_notebooks, review_notebook, update_notebook
from immune.orchestrator import build_immune_report
from immune.review import review_journal
from journal import (
    create_investment_journal_entry,
    get_investment_dna,
    get_investment_health,
    list_investment_journal_entries,
    submit_investment_outcome,
)
from scanner.crypto import scan_crypto
from scanner.cn_stock import scan_cn_stock
from scanner.data_health import build_data_health
from scanner.kol import check_kol_call
from scanner.stock import scan_stock
from schemas import (
    ImmuneReportRequest,
    AuthLoginRequest,
    AuthRegisterRequest,
    KOLCallCreate,
    KOLCallUpdate,
    KOLBatchCaptureRequest,
    KOLCaptureRequest,
    KOLCheckRequest,
    KOLProfileCreate,
    KOLProfileUpdate,
    InvestmentJournalCreateRequest,
    InvestmentOutcomeRequest,
    NotebookCreate,
    NotebookReviewRequest,
    NotebookUpdate,
    ReviewRequest,
    UserPublic,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title=APP_NAME, description=APP_DESCRIPTION, version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "concept": APP_CONCEPT,
        "status": "running",
    }


@app.get("/health")
def health():
    connected = is_database_connected()
    return {
        "status": "ok" if connected else "degraded",
        "database": "connected" if connected else "disconnected",
        "version": APP_VERSION,
    }


@app.get("/data/health")
def data_health():
    return build_data_health()


@app.get("/scan/crypto/{token}")
def crypto_scan(token: str):
    return scan_crypto(token)


@app.get("/scan/stock/{symbol}")
def stock_scan(symbol: str):
    normalized = symbol.strip().upper().replace(".SH", "").replace(".SZ", "").replace("SH", "").replace("SZ", "")
    if normalized.isdigit() and len(normalized) <= 6:
        return scan_cn_stock(symbol)
    return scan_stock(symbol)


@app.get("/scan/cn-stock/{symbol}")
def cn_stock_scan(symbol: str):
    return scan_cn_stock(symbol)


@app.post("/auth/register")
def auth_register(payload: AuthRegisterRequest):
    return register_user(payload)


@app.post("/auth/login")
def auth_login(payload: AuthLoginRequest):
    return login_user(payload)


@app.get("/auth/me")
def auth_me(user: UserPublic = Depends(get_current_user)):
    return user


@app.post("/auth/logout")
def auth_logout():
    return {"success": True}


@app.post("/immune/report")
def immune_report(payload: ImmuneReportRequest, user: UserPublic = Depends(get_current_user_or_demo)):
    return build_immune_report(payload, user.id)


@app.get("/journal")
def journal_list(user: UserPublic = Depends(get_current_user_or_demo)):
    return list_entries(user.id)


@app.post("/journal/create")
def investment_journal_create(payload: InvestmentJournalCreateRequest):
    return create_investment_journal_entry(payload)


@app.post("/journal/outcome")
def investment_journal_outcome(payload: InvestmentOutcomeRequest):
    try:
        return submit_investment_outcome(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/journal/dna/{user_id}")
def investment_journal_dna(user_id: str):
    return get_investment_dna(user_id)


@app.get("/journal/health/{user_id}")
def investment_journal_health(user_id: str):
    return get_investment_health(user_id)


@app.get("/journal/{journal_id:int}")
def journal_detail(journal_id: int, user: UserPublic = Depends(get_current_user_or_demo)):
    entry = get_entry(journal_id, user.id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry


@app.post("/journal/{journal_id:int}/review")
def journal_review(journal_id: int, payload: ReviewRequest, user: UserPublic = Depends(get_current_user_or_demo)):
    if payload.journal_id != journal_id:
        raise HTTPException(status_code=400, detail="journal_id in path and body must match")
    try:
        return review_journal(payload, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/journal/{user_id}")
def investment_journal_by_user(user_id: str):
    return list_investment_journal_entries(user_id)


@app.post("/kol/check")
def kol_check(payload: KOLCheckRequest):
    return check_kol_call(payload)


@app.get("/dna")
def investment_dna(user: UserPublic = Depends(get_current_user_or_demo)):
    return build_investment_dna(user.id)


@app.get("/kol/profiles")
def kol_profiles(user: UserPublic = Depends(get_current_user_or_demo)):
    return list_kol_profiles(user.id)


@app.post("/kol/profiles")
def kol_profile_create(payload: KOLProfileCreate, user: UserPublic = Depends(get_current_user_or_demo)):
    return create_kol_profile(payload, user.id)


@app.get("/kol/profiles/{kol_id}")
def kol_profile_detail(kol_id: int, user: UserPublic = Depends(get_current_user_or_demo)):
    profile = get_kol_profile(kol_id, user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="KOL profile not found")
    return profile


@app.put("/kol/profiles/{kol_id}")
def kol_profile_update(kol_id: int, payload: KOLProfileUpdate, user: UserPublic = Depends(get_current_user_or_demo)):
    profile = update_kol_profile(kol_id, payload, user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="KOL profile not found")
    return profile


@app.delete("/kol/profiles/{kol_id}")
def kol_profile_delete(kol_id: int, user: UserPublic = Depends(get_current_user_or_demo)):
    if not delete_kol_profile(kol_id, user.id):
        raise HTTPException(status_code=404, detail="KOL profile not found")
    return {"deleted": True}


@app.get("/kol/profiles/{kol_id}/calls")
def kol_profile_calls(kol_id: int, user: UserPublic = Depends(get_current_user_or_demo)):
    return list_kol_calls(user.id, kol_id)


@app.get("/kol/profiles/{kol_id}/risk-profile")
def kol_profile_risk_profile(kol_id: int, user: UserPublic = Depends(get_current_user_or_demo)):
    if get_kol_profile(kol_id, user.id) is None:
        raise HTTPException(status_code=404, detail="KOL profile not found")
    return build_kol_behavior_profile(kol_id, user.id)


@app.post("/kol/profiles/{kol_id}/recalculate")
def kol_profile_recalculate(kol_id: int, user: UserPublic = Depends(get_current_user_or_demo)):
    profile = recalculate_kol_profile_stats(kol_id, user.id)
    if profile is None:
        raise HTTPException(status_code=404, detail="KOL profile not found")
    return profile


@app.get("/kol/calls")
def kol_calls(user: UserPublic = Depends(get_current_user_or_demo)):
    return list_kol_calls(user.id)


@app.post("/kol/calls")
def kol_call_create(payload: KOLCallCreate, user: UserPublic = Depends(get_current_user_or_demo)):
    return create_kol_call(payload, user.id)


@app.post("/kol/capture")
def kol_call_capture(payload: KOLCaptureRequest, user: UserPublic = Depends(get_current_user_or_demo)):
    return capture_kol_call(payload, user.id)


@app.post("/kol/capture/batch")
def kol_call_capture_batch(payload: KOLBatchCaptureRequest, user: UserPublic = Depends(get_current_user_or_demo)):
    return capture_kol_calls_batch(payload, user.id)


@app.get("/kol/calls/{call_id}")
def kol_call_detail(call_id: int, user: UserPublic = Depends(get_current_user_or_demo)):
    call = get_kol_call(call_id, user.id)
    if call is None:
        raise HTTPException(status_code=404, detail="KOL call not found")
    return call


@app.put("/kol/calls/{call_id}")
def kol_call_update(call_id: int, payload: KOLCallUpdate, user: UserPublic = Depends(get_current_user_or_demo)):
    call = update_kol_call(call_id, payload, user.id)
    if call is None:
        raise HTTPException(status_code=404, detail="KOL call not found")
    return call


@app.delete("/kol/calls/{call_id}")
def kol_call_delete(call_id: int, user: UserPublic = Depends(get_current_user_or_demo)):
    if not delete_kol_call(call_id, user.id):
        raise HTTPException(status_code=404, detail="KOL call not found")
    return {"deleted": True}


@app.post("/kol/calls/{call_id}/refresh")
def kol_call_refresh(call_id: int, user: UserPublic = Depends(get_current_user_or_demo)):
    call = refresh_kol_call(call_id, user.id)
    if call is None:
        raise HTTPException(status_code=404, detail="KOL call not found")
    return call


@app.get("/kol/dependency")
def kol_dependency(user: UserPublic = Depends(get_current_user_or_demo)):
    return calculate_user_kol_dependency(user.id)


@app.get("/notebook")
def notebook_list(user: UserPublic = Depends(get_current_user_or_demo)):
    return list_notebooks(user.id)


@app.get("/notebook/{notebook_id}")
def notebook_detail(notebook_id: int, user: UserPublic = Depends(get_current_user_or_demo)):
    notebook = get_notebook(notebook_id, user.id)
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return notebook


@app.post("/notebook")
def notebook_create(payload: NotebookCreate, user: UserPublic = Depends(get_current_user_or_demo)):
    return create_notebook(payload, user.id)


@app.put("/notebook/{notebook_id}")
def notebook_update(notebook_id: int, payload: NotebookUpdate, user: UserPublic = Depends(get_current_user_or_demo)):
    notebook = update_notebook(notebook_id, payload, user.id)
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return notebook


@app.post("/notebook/{notebook_id}/review")
def notebook_review(notebook_id: int, payload: NotebookReviewRequest, user: UserPublic = Depends(get_current_user_or_demo)):
    notebook = review_notebook(notebook_id, payload, user.id)
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return notebook
