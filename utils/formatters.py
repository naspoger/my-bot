from __future__ import annotations

from datetime import datetime, timezone

from config import MAX_WARNS, RANKS


def rank_title(rank_key: str) -> str:
    key = (rank_key or "").strip().lower()
    rank = RANKS.get(key)
    return rank.title if rank else "Неизвестный ранг"


def get_days_left(promotion_deadline: str | None) -> str:
    if not promotion_deadline:
        return "не задано"

    try:
        deadline_dt = datetime.fromisoformat(promotion_deadline)
        now_dt = datetime.now(timezone.utc)
        days_left = max((deadline_dt - now_dt).days, 0)
        return f"~{days_left} дн."
    except Exception:
        return "не задано"


def build_stats_message(moderator: dict, warns_count: int) -> str:
    rank_key = (moderator.get("rank_key") or "").strip().lower()
    rank = RANKS.get(rank_key, RANKS["helper"])

    days_left_text = get_days_left(moderator.get("promotion_deadline"))

    mentor_name = moderator.get("mentor_name") or rank.mentor

    return (
        "**Ваша статистика:**\n\n"
        f"🔹 Ник: {moderator.get('nickname', 'Неизвестно')}\n"
        f"🔹 Принято отчетов: {moderator.get('accepted_reports', 0)}\n"
        f"🔹 Ранг: {rank.title}\n"
        f"🔹 Варны: {warns_count}/{MAX_WARNS}\n"
        f"🔹 Предупреждения: {moderator.get('warnings_count', 0)}/3\n"
        f"🔹 BIGCOINS: {moderator.get('bigcoins', 0)}\n\n"
        f"🗓 До следующего повышения осталось: {days_left_text}\n"
        f"Свяжитесь с наставником: {mentor_name}"
    )