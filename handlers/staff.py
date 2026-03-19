from __future__ import annotations
from config import WARN_BUY_PRICE
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils import build_stats_message, ensure_staff_channel


class StaffCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def _resolve_target_member(
        self,
        ctx: commands.Context,
        member: discord.Member | None,
    ) -> discord.Member | None:
        # Если никого не указали — смотрим себя
        if member is None:
            return ctx.author

        # Если указали другого пользователя — это доступно только админу
        if member.id != ctx.author.id:
            is_admin = await self.db.is_admin(ctx.author.id)
            if not is_admin:
                await ctx.reply(
                    "Вы можете смотреть только свою статистику.",
                    mention_author=False,
                )
                return None

        return member

    async def _show_stats(
        self,
        ctx: commands.Context,
        member: discord.Member | None = None,
    ):
        target = await self._resolve_target_member(ctx, member)
        if target is None:
            return

        moderator = await self.db.get_moderator(target.id)
        if not moderator:
            await ctx.reply(
                "Этот пользователь не зарегистрирован в системе.",
                mention_author=False,
            )
            return

        warns = await self.db.get_active_warns(target.id)
        message = build_stats_message(moderator, len(warns))
        await ctx.reply(message, mention_author=False)

    @commands.hybrid_command(name="swarnbuy", description="Снять один варн за BIGCOINS")
    @ensure_staff_channel()
    async def swarnbuy(self, ctx: commands.Context):
        moderator = await self.db.get_moderator(ctx.author.id)
        if not moderator:
            await ctx.reply("Вы не зарегистрированы в системе.", mention_author=False)
            return

        warns = await self.db.get_active_warns(ctx.author.id)
        if not warns:
            await ctx.reply("У вас нет активных варнов для снятия.", mention_author=False)
            return

        current_bigcoins = int(moderator.get("bigcoins", 0) or 0)
        if current_bigcoins < WARN_BUY_PRICE:
            await ctx.reply(
                f"Для снятия варна нужно {WARN_BUY_PRICE} BIGCOINS.\n"
                f"У вас сейчас: {current_bigcoins} BIGCOINS.",
                mention_author=False,
            )
            return

        spent = await self.db.spend_bigcoins(ctx.author.id, WARN_BUY_PRICE)
        if not spent:
            await ctx.reply("Не удалось списать BIGCOINS.", mention_author=False)
            return

        removed = await self.db.remove_latest_warn(ctx.author.id)
        if not removed:
            await ctx.reply("Не удалось снять варн.", mention_author=False)
            return

        updated = await self.db.get_moderator(ctx.author.id)
        left_bigcoins = int(updated.get("bigcoins", 0) or 0)

        active_warns = await self.db.get_active_warns(ctx.author.id)

        await ctx.reply(
            f"✅ Вы успешно сняли 1 варн за {WARN_BUY_PRICE} BIGCOINS.\n"
            f"🔹 Варны: {len(active_warns)}/3\n"
            f"🔹 BIGCOINS: {left_bigcoins}",
            mention_author=False,
        )
        
    @commands.hybrid_command(name="sstart", description="Показать свою статистику")
    @ensure_staff_channel()
    async def sstart(self, ctx: commands.Context):
        await self._show_stats(ctx)

    @commands.hybrid_command(name="sstats", description="Показать статистику сотрудника")
    @app_commands.describe(member="Сотрудник")
    @ensure_staff_channel()
    async def sstats(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._show_stats(ctx, member)

    @commands.hybrid_command(name="swarns", description="Показать активные варны")
    @app_commands.describe(member="Сотрудник")
    @ensure_staff_channel()
    async def swarns(self, ctx: commands.Context, member: discord.Member | None = None):
        target = await self._resolve_target_member(ctx, member)
        if target is None:
            return

        warns = await self.db.get_active_warns(target.id)

        if not warns:
            if target.id == ctx.author.id:
                await ctx.reply("У вас нет активных варнов.", mention_author=False)
            else:
                await ctx.reply(
                    f"У пользователя {target.mention} нет активных варнов.",
                    mention_author=False,
                )
            return

        title = (
            "**Ваши активные варны:**"
            if target.id == ctx.author.id
            else f"**Активные варны пользователя {target.mention}:**"
        )

        lines = [title, ""]

        for i, warn in enumerate(warns, start=1):
            reason = warn.get("reason") or "Причина не указана"

            issued_at_raw = warn.get("issued_at")
            if issued_at_raw:
                try:
                    dt = datetime.fromisoformat(issued_at_raw)
                    dt = dt.astimezone()
                    issued_at = dt.strftime("%d.%m.%Y %H:%M")
                except Exception:
                    issued_at = issued_at_raw
            else:
                issued_at = "Неизвестно"

            issued_by = warn.get("issued_by")
            issued_by_text = f"<@{issued_by}>" if issued_by else "Неизвестно"

            lines.append(
                f"**{i}. {reason}**\n"
                f"📅 {issued_at}\n"
                f"👤 Выдал: {issued_by_text}\n"
            )

        await ctx.reply("\n".join(lines), mention_author=False)


async def setup(bot):
    await bot.add_cog(StaffCog(bot))