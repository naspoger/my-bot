from __future__ import annotations

import aiosqlite
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from config import DATABASE_PATH, RANKS, REMINDER_CHANNEL_ID, REMINDER_HOUR, REMINDER_MINUTE


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Database:
    def __init__(self, path: str = DATABASE_PATH):
        self.path = path

    def connect(self) -> aiosqlite.Connection:
        return aiosqlite.connect(self.path)

    async def spend_bigcoins(self, user_id: int, amount: int) -> bool:
        moderator = await self.get_moderator(user_id)
        if not moderator:
            return False

        current = int(moderator.get("bigcoins", 0) or 0)
        if current < amount:
            return False

        async with self.connect() as db:
            await db.execute(
                """
                UPDATE moderators
                SET bigcoins = bigcoins - ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (amount, utc_now().isoformat(), user_id),
            )
            await db.commit()

        return True

    async def spend_bigcoins(self, user_id: int, amount: int) -> bool:
        moderator = await self.get_moderator(user_id)
        if not moderator:
            return False

        current = int(moderator.get("bigcoins", 0) or 0)
        if current < amount:
            return False

        async with self.connect() as db:
            await db.execute(
                """
                UPDATE moderators
                SET bigcoins = bigcoins - ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (amount, utc_now().isoformat(), user_id),
            )
            await db.commit()

        return True
                
    async def set_bigcoins(self, user_id: int, amount: int) -> bool:
        moderator = await self.get_moderator(user_id)
        if not moderator:
            return False

        async with self.connect() as db:
            await db.execute(
                """
                UPDATE moderators
                SET bigcoins = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (amount, utc_now().isoformat(), user_id),
            )
            await db.commit()

        return True

    async def get_warnings_count(self, user_id: int) -> int:
        moderator = await self.get_moderator(user_id)
        if not moderator:
            return 0
        return int(moderator.get("warnings_count", 0) or 0)

    async def get_warnings_count(self, user_id: int) -> int:
        moderator = await self.get_moderator(user_id)
        if not moderator:
            return 0
        return int(moderator.get("warnings_count", 0) or 0)

    async def add_warning(self, user_id: int, issued_by: Optional[int] = None) -> tuple[int, bool]:
        moderator = await self.get_moderator(user_id)
        if not moderator:
            return 0, False

        current = int(moderator.get("warnings_count", 0) or 0)
        current += 1

        if current >= 3:
            async with self.connect() as db:
                await db.execute(
                    """
                    UPDATE moderators
                    SET warnings_count = 0,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (utc_now().isoformat(), user_id),
                )
                await db.commit()

            await self.add_warn(
                user_id=user_id,
                reason="Автоматический варн за 3/3 предупреждений",
                issued_by=issued_by,
            )
            return 0, True

        async with self.connect() as db:
            await db.execute(
                """
                UPDATE moderators
                SET warnings_count = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (current, utc_now().isoformat(), user_id),
            )
            await db.commit()

        return current, False

    async def remove_warning(self, user_id: int) -> bool:
        moderator = await self.get_moderator(user_id)
        if not moderator:
            return False

        current = int(moderator.get("warnings_count", 0) or 0)
        if current <= 0:
            return False

        current -= 1

        async with self.connect() as db:
            await db.execute(
                """
                UPDATE moderators
                SET warnings_count = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (current, utc_now().isoformat(), user_id),
            )
            await db.commit()

        return True        

    async def add_warning(self, user_id: int, issued_by: Optional[int] = None) -> tuple[int, bool]:
        """
        Добавляет предупреждение.
        Возвращает:
        (новое_количество_предов, был_ли_выдан_авто_варн)
        """
        moderator = await self.get_moderator(user_id)
        if not moderator:
            return 0, False

        current = int(moderator.get("warnings_count", 0) or 0)
        current += 1

        if current >= 3:
            # сбрасываем предупреждения и выдаём 1 варн
            async with self.connect() as db:
                await db.execute(
                    """
                    UPDATE moderators
                    SET warnings_count = 0,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (utc_now().isoformat(), user_id),
                )
                await db.commit()

            await self.add_warn(
                user_id=user_id,
                reason="Автоматический варн за 3/3 предупреждений",
                issued_by=issued_by,
            )
            return 0, True

        async with self.connect() as db:
            await db.execute(
                """
                UPDATE moderators
                SET warnings_count = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (current, utc_now().isoformat(), user_id),
            )
            await db.commit()

        return current, False

    async def remove_warning(self, user_id: int) -> bool:
        moderator = await self.get_moderator(user_id)
        if not moderator:
            return False

        current = int(moderator.get("warnings_count", 0) or 0)
        if current <= 0:
            return False

        current -= 1

        async with self.connect() as db:
            await db.execute(
                """
                UPDATE moderators
                SET warnings_count = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (current, utc_now().isoformat(), user_id),
            )
            await db.commit()

        return True

    async def init(self) -> None:
        async with self.connect() as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON")
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS moderators (
                    user_id INTEGER PRIMARY KEY,
                    nickname TEXT NOT NULL,
                    rank_key TEXT NOT NULL,
                    accepted_reports INTEGER NOT NULL DEFAULT 0,
                    bigcoins INTEGER NOT NULL DEFAULT 0,
                    promotion_deadline TEXT,
                    mentor_name TEXT,
                    promotion_notified INTEGER NOT NULL DEFAULT 0,
                    warnings_count INTEGER NOT NULL DEFAULT 0,
                    access_level TEXT NOT NULL DEFAULT 'staff',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    reason TEXT,
                    issued_by INTEGER,
                    issued_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS report_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL UNIQUE,
                    author_id INTEGER NOT NULL,
                    reviewer_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scheduler_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

            # миграции для старой базы
            cursor = await db.execute("PRAGMA table_info(moderators)")
            cols = [row[1] for row in await cursor.fetchall()]
            await cursor.close()

            if "warnings_count" not in cols:
                await db.execute(
                    "ALTER TABLE moderators ADD COLUMN warnings_count INTEGER NOT NULL DEFAULT 0"
                )

            if "mentor_name" not in cols:
                await db.execute("ALTER TABLE moderators ADD COLUMN mentor_name TEXT")

            if "promotion_notified" not in cols:
                await db.execute(
                    "ALTER TABLE moderators ADD COLUMN promotion_notified INTEGER NOT NULL DEFAULT 0"
                )

            await db.execute(
                "INSERT OR IGNORE INTO scheduler_settings(key, value) VALUES ('reminder_channel_id', ?)",
                (str(REMINDER_CHANNEL_ID),),
            )
            await db.execute(
                "INSERT OR IGNORE INTO scheduler_settings(key, value) VALUES ('reminder_hour', ?)",
                (str(REMINDER_HOUR),),
            )
            await db.execute(
                "INSERT OR IGNORE INTO scheduler_settings(key, value) VALUES ('reminder_minute', ?)",
                (str(REMINDER_MINUTE),),
            )
            await db.commit()

    async def get_scheduler_settings(self) -> Dict[str, str]:
        async with self.connect() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT key, value FROM scheduler_settings")
            rows = await cursor.fetchall()
            await cursor.close()
            return {row["key"]: row["value"] for row in rows}

    async def get_ready_for_promotion(self) -> List[Dict[str, Any]]:
        async with self.connect() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM moderators
                WHERE promotion_deadline IS NOT NULL
                  AND promotion_notified = 0
                """
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return [dict(row) for row in rows]

    async def mark_promotion_notified(self, user_id: int) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                UPDATE moderators
                SET promotion_notified = 1,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (utc_now().isoformat(), user_id),
            )
            await db.commit()

    async def reset_promotion_notification(self, user_id: int) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                UPDATE moderators
                SET promotion_notified = 0,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (utc_now().isoformat(), user_id),
            )
            await db.commit()

    async def upsert_moderator(
        self,
        user_id: int,
        nickname: str,
        rank_key: str,
        access_level: str = "staff",
    ) -> None:
        rank_key = (rank_key or "helper").strip().lower()
        if rank_key not in RANKS:
            rank_key = "helper"

        now = utc_now().isoformat()
        promotion_days = RANKS[rank_key].promotion_days
        deadline = (utc_now() + timedelta(days=promotion_days)).isoformat() if promotion_days > 0 else None

        async with self.connect() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT user_id, promotion_deadline FROM moderators WHERE user_id = ?",
                (user_id,),
            )
            exists = await cursor.fetchone()
            await cursor.close()

            if exists:
                await db.execute(
                    """
                    UPDATE moderators
                    SET nickname = ?,
                        rank_key = ?,
                        access_level = ?,
                        promotion_deadline = COALESCE(promotion_deadline, ?),
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (nickname, rank_key, access_level, deadline, now, user_id),
                )
            else:
                await db.execute(
                    """
                    INSERT INTO moderators (
                        user_id, nickname, rank_key, accepted_reports, bigcoins,
                        promotion_deadline, mentor_name, promotion_notified,
                        access_level, created_at, updated_at
                    ) VALUES (?, ?, ?, 0, 0, ?, NULL, 0, ?, ?, ?)
                    """,
                    (user_id, nickname, rank_key, deadline, access_level, now, now),
                )

            await db.commit()

    async def get_moderator(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with self.connect() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM moderators WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            await cursor.close()
            return dict(row) if row else None

    async def update_nickname(self, user_id: int, nickname: str) -> None:
        async with self.connect() as db:
            await db.execute(
                "UPDATE moderators SET nickname = ?, updated_at = ? WHERE user_id = ?",
                (nickname, utc_now().isoformat(), user_id),
            )
            await db.commit()

    async def set_access_level(self, user_id: int, level: str) -> None:
        async with self.connect() as db:
            await db.execute(
                "UPDATE moderators SET access_level = ?, updated_at = ? WHERE user_id = ?",
                (level, utc_now().isoformat(), user_id),
            )
            await db.commit()

    async def set_rank(self, user_id: int, rank_key: str) -> None:
        rank_key = (rank_key or "helper").strip().lower()
        if rank_key not in RANKS:
            rank_key = "helper"

        promotion_days = RANKS[rank_key].promotion_days
        deadline = (utc_now() + timedelta(days=promotion_days)).isoformat() if promotion_days > 0 else None

        async with self.connect() as db:
            await db.execute(
                """
                UPDATE moderators
                SET rank_key = ?,
                    promotion_deadline = ?,
                    promotion_notified = 0,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (rank_key, deadline, utc_now().isoformat(), user_id),
            )
            await db.commit()

    async def set_mentor(self, user_id: int, mentor_name: str) -> None:
        async with self.connect() as db:
            await db.execute(
                "UPDATE moderators SET mentor_name = ?, updated_at = ? WHERE user_id = ?",
                (mentor_name, utc_now().isoformat(), user_id),
            )
            await db.commit()

    async def add_promotion_days(self, user_id: int, days: int) -> None:
        moderator = await self.get_moderator(user_id)
        if not moderator:
            return

        current_deadline = moderator.get("promotion_deadline")
        base_dt = datetime.fromisoformat(current_deadline) if current_deadline else utc_now()
        new_dt = base_dt + timedelta(days=days)

        async with self.connect() as db:
            await db.execute(
                """
                UPDATE moderators
                SET promotion_deadline = ?,
                    promotion_notified = 0,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (new_dt.isoformat(), utc_now().isoformat(), user_id),
            )
            await db.commit()

    async def remove_promotion_days(self, user_id: int, days: int) -> None:
        await self.add_promotion_days(user_id, -days)

    async def increment_accepted_report(self, user_id: int, salary: int) -> None:
        async with self.connect() as db:
            await db.execute(
                """
                UPDATE moderators
                SET accepted_reports = accepted_reports + 1,
                    bigcoins = bigcoins + ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (salary, utc_now().isoformat(), user_id),
            )
            await db.commit()

    async def get_active_warns(self, user_id: int) -> List[Dict[str, Any]]:
        async with self.connect() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM warnings WHERE user_id = ? AND active = 1 ORDER BY issued_at DESC",
                (user_id,),
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return [dict(row) for row in rows]

    async def add_warn(self, user_id: int, reason: Optional[str], issued_by: Optional[int]) -> int:
        now = utc_now().isoformat()
        async with self.connect() as db:
            cursor = await db.execute(
                "INSERT INTO warnings(user_id, reason, issued_by, issued_at, active) VALUES (?, ?, ?, ?, 1)",
                (user_id, reason, issued_by, now),
            )
            await db.commit()
            warn_id = cursor.lastrowid
            await cursor.close()
            return warn_id

    async def remove_latest_warn(self, user_id: int) -> bool:
        async with self.connect() as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id FROM warnings WHERE user_id = ? AND active = 1 ORDER BY issued_at DESC LIMIT 1",
                (user_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()

            if not row:
                return False

            await db.execute("UPDATE warnings SET active = 0 WHERE id = ?", (row["id"],))
            await db.commit()
            return True

    async def clear_access(self, user_id: int) -> None:
        async with self.connect() as db:
            await db.execute(
                "UPDATE moderators SET access_level = 'none', updated_at = ? WHERE user_id = ?",
                (utc_now().isoformat(), user_id),
            )
            await db.commit()

    async def log_report_review(
        self,
        message_id: int,
        author_id: int,
        reviewer_id: int,
        status: str,
        reason: Optional[str] = None,
    ) -> bool:
        now = utc_now().isoformat()
        try:
            async with self.connect() as db:
                await db.execute(
                    """
                    INSERT INTO report_reviews(message_id, author_id, reviewer_id, status, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (message_id, author_id, reviewer_id, status, reason, now),
                )
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            return False

    async def has_access(self, user_id: int) -> bool:
        moderator = await self.get_moderator(user_id)
        if not moderator:
            return False
        return moderator.get("access_level") in ("admin", "staff")

    async def is_admin(self, user_id: int) -> bool:
        moderator = await self.get_moderator(user_id)
        if not moderator:
            return False
        return moderator.get("access_level") == "admin"

    async def ensure_moderator(
        self,
        user_id: int,
        nickname: str,
        rank_key: str = "helper",
        access_level: str = "staff",
    ) -> None:
        moderator = await self.get_moderator(user_id)
        if moderator:
            return

        await self.upsert_moderator(
            user_id=user_id,
            nickname=nickname,
            rank_key=rank_key,
            access_level=access_level,
        )