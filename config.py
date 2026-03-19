from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_TOKEN", "0")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

DATABASE_PATH = os.getenv("DATABASE_PATH", "bigcraft_staff.db")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Amsterdam")

STATS_CHANNEL_ID = int(os.getenv("STATS_CHANNEL_ID", "0"))
REPORTS_CHANNEL_ID = int(os.getenv("REPORTS_CHANNEL_ID", "0"))
REMINDER_CHANNEL_ID = int(os.getenv("REMINDER_CHANNEL_ID", "0"))
DEFAULT_ROLE_ID = int(os.getenv("DEFAULT_ROLE_ID", "0"))


FORUM_AUTOREPLY_CHANNEL_1_ID = int(os.getenv("FORUM_AUTOREPLY_CHANNEL_1_ID", "0"))
FORUM_AUTOREPLY_CHANNEL_2_ID = int(os.getenv("FORUM_AUTOREPLY_CHANNEL_2_ID", "0"))

FORUM_AUTOREPLY_TEXT = os.getenv(
    "FORUM_AUTOREPLY_TEXT",
    "Уважаемый игрок, благодарим вас за поданную жалобу. Модераторы рассмотрят её в ближайшее время. Пожалуйста, убедитесь что вы заполнили жалобу правильно. Проверьте название темы, форму, укажите тайм-коды, если видео больше 1 минуты. Это автоматический ответ.",
)

HELPER_ROLE_ID = int(os.getenv("HELPER_ROLE_ID", "0"))
ML_MODER_ROLE_ID = int(os.getenv("ML_MODER_ROLE_ID", "0"))
MODER_ROLE_ID = int(os.getenv("MODER_ROLE_ID", "0"))
ST_MODER_ROLE_ID = int(os.getenv("ST_MODER_ROLE_ID", "0"))

REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "12"))
REMINDER_MINUTE = int(os.getenv("REMINDER_MINUTE", "0"))
MAX_WARNS = int(os.getenv("MAX_WARNS", "3"))

SUNDAY_REMINDER_TEXT = os.getenv(
    "SUNDAY_REMINDER_TEXT",
    "Напоминание: сегодня нужно сдать отчет!",
)

# 👇 СНАЧАЛА объявляем


# Пользователи с полным доступом к админ-командам.
ROOT_ADMIN_IDS = {
    528972024971001866,
}

# 👇 ПОТОМ используем
STAFF_COMMANDS_CHANNEL_IDS = {
    channel_id
    for channel_id in (STATS_CHANNEL_ID, REPORTS_CHANNEL_ID)
    if channel_id
}


@dataclass(frozen=True)
class RankConfig:
    title: str
    promotion_days: int
    salary: int
    mentor: str
    role_id: int


RANKS = {
    "helper": RankConfig("ХЕЛПЕР", 14, 100, "zolotarev_", HELPER_ROLE_ID),
    "ml_moder": RankConfig("МЛ МОДЕР", 90, 150, "zolotarev_", ML_MODER_ROLE_ID),
    "moder": RankConfig("МОДЕР", 90, 200, "zolotarev_", MODER_ROLE_ID),
    "st_moder": RankConfig("СТ. МОДЕР", 90, 300, "zolotarev_", ST_MODER_ROLE_ID),
}

# Для команды /ssetrank: соответствие Discord role_id -> rank_key
ROLE_ID_TO_RANK_KEY = {
    role_id: rank_key
    for rank_key, role_id in {
        "helper": HELPER_ROLE_ID,
        "ml_moder": ML_MODER_ROLE_ID,
        "moder": MODER_ROLE_ID,
        "st_moder": ST_MODER_ROLE_ID,
    }.items()
    if role_id
}

# цена снятия варна
WARN_BUY_PRICE = 400