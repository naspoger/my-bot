from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks

from config import (
    BOT_TOKEN,
    FORUM_AUTOREPLY_CHANNEL_1_ID,
    FORUM_AUTOREPLY_CHANNEL_2_ID,
    FORUM_AUTOREPLY_TEXT,
    GUILD_ID,
    STATS_CHANNEL_ID,
    SUNDAY_REMINDER_TEXT,
    TIMEZONE,
)
from database import Database

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bigcraft_staff_bot")


class BigCraftBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        super().__init__(
            command_prefix="/",
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )
        self.db = Database()
        self.tz = ZoneInfo(TIMEZONE)
        self.reminder_loop.start()

    async def setup_hook(self) -> None:
        await self.db.init()
        await self.load_extension("handlers.staff")
        await self.load_extension("handlers.admin")
        logger.info("Расширения загружены.")
        self.loop.create_task(self.promotion_ready_loop())

    async def on_ready(self) -> None:
        try:
            if GUILD_ID:
                guild = discord.Object(id=GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info("Синхронизировано guild-команд: %s", len(synced))
            else:
                synced = await self.tree.sync()
                logger.info("Синхронизировано global-команд: %s", len(synced))
        except Exception:
            logger.exception("Не удалось синхронизировать slash-команды")

        logger.info("Бот запущен как %s (%s)", self.user, self.user.id)

    async def on_thread_create(self, thread: discord.Thread) -> None:
        if thread.guild is None or thread.owner_id == self.user.id:
            return

        allowed_forum_ids = {
            forum_id
            for forum_id in (FORUM_AUTOREPLY_CHANNEL_1_ID, FORUM_AUTOREPLY_CHANNEL_2_ID)
            if forum_id
        }
        if not allowed_forum_ids:
            return

        parent = thread.parent
        if parent is None or parent.id not in allowed_forum_ids:
            return

        try:
            await thread.send(FORUM_AUTOREPLY_TEXT)
            logger.info(
                "Отправлен автоответ в форум-тему %s (parent=%s)",
                thread.id,
                parent.id,
            )
        except Exception:
            logger.exception("Не удалось отправить автоответ в тему форума %s", thread.id)


    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("Не хватает аргументов для команды.", mention_author=False)
            return
        if isinstance(error, commands.BadArgument):
            await ctx.reply("Неверный формат аргументов команды.", mention_author=False)
            return
        if isinstance(error, commands.MemberNotFound):
            await ctx.reply("Пользователь не найден на сервере.", mention_author=False)
            return
        if isinstance(error, commands.CheckFailure):
            return

        logger.exception("Ошибка команды", exc_info=error)
        await ctx.reply(f"Произошла ошибка: `{error}`", mention_author=False)

    async def promotion_ready_loop(self) -> None:
        await self.wait_until_ready()

        while not self.is_closed():
            try:
                channel = self.get_channel(STATS_CHANNEL_ID)
                if channel is not None:
                    moderators = await self.db.get_ready_for_promotion()
                    now = datetime.now(timezone.utc)

                    for moderator in moderators:
                        raw_deadline = moderator.get("promotion_deadline")
                        if not raw_deadline:
                            continue

                        try:
                            deadline = datetime.fromisoformat(raw_deadline)
                        except Exception:
                            continue

                        if deadline <= now:
                            await channel.send(
                                f"<@{moderator['user_id']}> готов к повышению."
                            )
                            await self.db.mark_promotion_notified(moderator["user_id"])

            except Exception as e:
                logger.exception("Ошибка проверки готовых к повышению: %s", e)

            await asyncio.sleep(3600)

    @tasks.loop(minutes=1)
    async def reminder_loop(self) -> None:
        try:
            settings = await self.db.get_scheduler_settings()
            channel_id = int(settings.get("reminder_channel_id", "0"))
            hour = int(settings.get("reminder_hour", "12"))
            minute = int(settings.get("reminder_minute", "0"))

            if not channel_id:
                return

            now_local = datetime.now(self.tz)
            if now_local.weekday() != 6:
                return
            if now_local.hour != hour or now_local.minute != minute:
                return

            channel = self.get_channel(channel_id)
            if channel is None:
                guild = self.get_guild(GUILD_ID) if GUILD_ID else None
                if guild:
                    channel = guild.get_channel(channel_id)

            if channel is None:
                logger.warning("Не найден reminder channel: %s", channel_id)
                return

            async for message in channel.history(limit=5):
                if message.author.id == self.user.id and message.content == SUNDAY_REMINDER_TEXT:
                    delta = now_local.replace(tzinfo=None) - message.created_at.astimezone(self.tz).replace(tzinfo=None)
                    if delta.total_seconds() < 60:
                        return
                    break

            await channel.send(SUNDAY_REMINDER_TEXT)
            logger.info("Еженедельное напоминание отправлено в канал %s", channel_id)
        except Exception:
            logger.exception("Ошибка в reminder_loop")

    @reminder_loop.before_loop
    async def before_reminder_loop(self) -> None:
        await self.wait_until_ready()


async def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_DISCORD_BOT_TOKEN_HERE":
        raise RuntimeError("Укажите BOT_TOKEN в .env файле перед запуском.")

    bot = BigCraftBot()
    async with bot:
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())