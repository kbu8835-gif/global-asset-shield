from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserPublic(BaseModel):
    id: int
    email: str
    username: Optional[str] = None
    created_at: Optional[str] = None
    is_active: int = 1


class AuthRegisterRequest(BaseModel):
    email: str
    username: Optional[str] = None
    password: str = Field(min_length=8)


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user: UserPublic
    access_token: str
    token_type: str = "bearer"


class RiskScan(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    risk_level: str
    risk_reasons: List[str]
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class KOLCheckRequest(BaseModel):
    kol_name: str
    asset: str
    call_text: str
    call_time: Optional[datetime] = None
    price_at_call: Optional[float] = None
    current_price: Optional[float] = None


class KOLCheckResponse(BaseModel):
    kol_name: str
    asset: str
    call_text: str
    call_time: datetime
    price_at_call: Optional[float]
    current_price: Optional[float]
    result: str
    credibility_score: int = Field(ge=0, le=100)
    risk_reasons: List[str]


class ImmuneReportRequest(BaseModel):
    asset: str
    asset_type: str
    user_intent: Optional[str] = None
    user_text: Optional[str] = None
    buy_reason: Optional[str] = None
    risk_awareness: Optional[str] = None
    worst_case_plan: Optional[str] = None
    position_size: Optional[str] = None
    horizon: Optional[str] = None


class ImmuneReportResponse(BaseModel):
    report_id: int
    asset: str
    asset_type: str
    risk_scan: Dict[str, Any]
    emotion_scan: Dict[str, Any]
    bias_detection: Dict[str, Any]
    devil_advocate: Dict[str, Any]
    regret_simulation: Dict[str, Any]
    conviction_score: Dict[str, Any]
    final_decision: str
    decision_reason: str
    position_advice: str
    journal_saved: bool
    summary: str
    kol_risk_scan: Optional[Dict[str, Any]] = None


class JournalEntry(BaseModel):
    id: int
    created_at: str
    asset: str
    asset_type: str
    user_intent: Optional[str] = None
    user_text: Optional[str] = None
    buy_reason: Optional[str] = None
    position_size: Optional[str] = None
    risk_awareness: Optional[str] = None
    worst_case_plan: Optional[str] = None
    risk_score: int
    emotion_score: int
    bias_score: int
    conviction_score: int
    decision: Optional[str] = None
    final_decision: str
    summary: str
    review_status: str
    full_report_json: Optional[str] = None


class InvestmentDNAResponse(BaseModel):
    investor_type: str
    discipline: int = Field(ge=0, le=100)
    patience: int = Field(ge=0, le=100)
    risk_appetite: int = Field(ge=0, le=100)
    kol_dependency: int = Field(ge=0, le=100)
    conviction: int = Field(ge=0, le=100)
    emotion_control: int = Field(ge=0, le=100)
    independent_thinking: int = Field(ge=0, le=100)
    summary: str
    kol_summary: Optional[str] = None
    top_kol_influences: List[str] = Field(default_factory=list)


class KOLProfileCreate(BaseModel):
    name: str
    twitter_handle: Optional[str] = None
    telegram_handle: Optional[str] = None
    youtube_channel: Optional[str] = None
    website: Optional[str] = None
    bio: Optional[str] = None


class KOLProfileUpdate(BaseModel):
    name: Optional[str] = None
    twitter_handle: Optional[str] = None
    telegram_handle: Optional[str] = None
    youtube_channel: Optional[str] = None
    website: Optional[str] = None
    bio: Optional[str] = None


class KOLProfile(BaseModel):
    id: int
    name: str
    twitter_handle: Optional[str] = None
    telegram_handle: Optional[str] = None
    youtube_channel: Optional[str] = None
    website: Optional[str] = None
    bio: Optional[str] = None
    trust_score: int = 50
    total_calls: int = 0
    win_rate_7d: float = 0
    win_rate_30d: float = 0
    average_roi_7d: float = 0
    average_roi_30d: float = 0
    average_max_gain: float = 0
    average_max_drawdown: float = 0
    risk_level: str = "Unknown"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class KOLCallCreate(BaseModel):
    kol_id: Optional[int] = None
    kol_name: Optional[str] = None
    asset: str
    asset_type: str = "crypto"
    call_time: Optional[str] = None
    call_price: Optional[float] = None
    current_price: Optional[float] = None
    source: Optional[str] = "manual"
    source_url: Optional[str] = None
    call_text: Optional[str] = None
    call_type: Optional[str] = "unknown"
    time_horizon: Optional[str] = None
    status: Optional[str] = "open"
    roi_7d: Optional[float] = None
    roi_30d: Optional[float] = None
    max_gain: Optional[float] = None
    max_drawdown: Optional[float] = None


class KOLCallUpdate(BaseModel):
    kol_id: Optional[int] = None
    kol_name: Optional[str] = None
    asset: Optional[str] = None
    asset_type: Optional[str] = None
    call_time: Optional[str] = None
    call_price: Optional[float] = None
    current_price: Optional[float] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    call_text: Optional[str] = None
    call_type: Optional[str] = None
    time_horizon: Optional[str] = None
    status: Optional[str] = None
    roi_7d: Optional[float] = None
    roi_30d: Optional[float] = None
    max_gain: Optional[float] = None
    max_drawdown: Optional[float] = None
    result_label: Optional[str] = None


class KOLCall(BaseModel):
    id: int
    kol_id: Optional[int] = None
    kol_name: Optional[str] = None
    asset: str
    asset_type: str = "crypto"
    call_time: Optional[str] = None
    call_price: Optional[float] = None
    current_price: Optional[float] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    call_text: Optional[str] = None
    call_type: Optional[str] = None
    time_horizon: Optional[str] = None
    status: str = "open"
    roi_7d: Optional[float] = None
    roi_30d: Optional[float] = None
    current_roi: Optional[float] = None
    max_gain: Optional[float] = None
    max_drawdown: Optional[float] = None
    result_label: Optional[str] = None
    emotion_tags: Optional[str] = None
    bias_tags: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class KOLDependencyResponse(BaseModel):
    kol_dependency: int
    kol_related_count: int
    total_decisions: int
    top_kol_names: List[str]
    summary: str


class ReviewRequest(BaseModel):
    journal_id: int
    current_price: float
    user_result_text: str


class ReviewResponse(BaseModel):
    journal_id: int
    original_decision: str
    review_result: str
    mistake_type: str
    lesson: str
    next_time_rule: str
    review_status: str


class NotebookCreate(BaseModel):
    asset: str
    asset_type: str = "crypto"
    title: Optional[str] = None
    decision: Optional[str] = "Wait"
    status: Optional[str] = "Open"
    entry_type: Optional[str] = "manual"
    notes: Optional[str] = ""
    buy_reason: Optional[str] = ""
    risk_awareness: Optional[str] = ""
    worst_case_plan: Optional[str] = ""
    position_size: Optional[str] = ""


class NotebookUpdate(BaseModel):
    title: Optional[str] = None
    decision: Optional[str] = None
    status: Optional[str] = None
    entry_type: Optional[str] = None
    notes: Optional[str] = None
    buy_reason: Optional[str] = None
    user_text: Optional[str] = None
    risk_awareness: Optional[str] = None
    worst_case_plan: Optional[str] = None
    position_size: Optional[str] = None
    mistakes: Optional[str] = None
    lesson: Optional[str] = None
    next_action: Optional[str] = None
    review_date: Optional[str] = None


class NotebookReviewRequest(BaseModel):
    user_result_text: str
    current_price: Optional[float] = None


class NotebookListItem(BaseModel):
    id: int
    title: str
    asset: str
    asset_type: str
    decision: str
    status: str
    entry_type: str
    created_at: str
    updated_at: str
    review_date: Optional[str] = None


class NotebookDetail(NotebookListItem):
    user_intent: Optional[str] = None
    user_text: Optional[str] = None
    buy_reason: Optional[str] = None
    risk_awareness: Optional[str] = None
    worst_case_plan: Optional[str] = None
    position_size: Optional[str] = None
    notes: Optional[str] = None
    mistakes: Optional[str] = None
    lesson: Optional[str] = None
    next_action: Optional[str] = None
    ai_analysis: Dict[str, Any] = Field(default_factory=dict)
    ai_coach: str
    timeline: List[Dict[str, str]]
