from database import get_journal_entry, list_journal_entries, save_journal_entry
from schemas import ImmuneReportRequest


def save_report(payload: ImmuneReportRequest, report: dict, user_id: int) -> int:
    return save_journal_entry(payload.model_dump(), report, user_id)


def list_entries(user_id: int):
    return list_journal_entries(user_id)


def get_entry(journal_id: int, user_id: int):
    return get_journal_entry(journal_id, user_id)
