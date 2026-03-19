from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import DEFAULT_ROLE_ID, RANKS, ROLE_ID_TO_RANK_KEY
from utils.checks import (
    ensure_staff_channel,
    ensure_reports_channel,
    is_root_admin,
    resolve_replied_message,
)
from utils.formatters import rank_title


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db

    async def cog_check(self, ctx: commands.Context) -> bool:
        if is_root_admin(ctx.author.id):
            return True

        moderator = await self.db.get_moderator(ctx.author.id)
        if moderator and moderator.get("access_level") == "admin":
            return True

        await ctx.reply("У вас нет прав на использование этой команды.", mention_author=False)
        return False

    @commands.hybrid_command(name="spred", description="Выдать предупреждение сотруднику")
    @app_commands.describe(member="Сотрудник", reason="Причина предупреждения")
    @ensure_staff_channel()
    async def spred(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Причина не указана"):
        moderator = await self.db.get_moderator(member.id)
        if not moderator:
            await self.db.ensure_moderator(
                user_id=member.id,
                nickname=member.display_name,
                rank_key="helper",
                access_level="staff",
            )

        new_count, auto_warn = await self.db.add_warning(member.id, issued_by=ctx.author.id)

        if auto_warn:
            warns = await self.db.get_active_warns(member.id)
            await ctx.reply(
                f"Пользователю {member.mention} выдано предупреждение за: {reason}\n"
                f"Это было 3/3 предупреждений.\n"
                f"Предупреждения сброшены, автоматически выдан 1 варн.\n"
                f"Текущие варны: {len(warns)}/3",
                mention_author=False,
            )
        else:
            await ctx.reply(
                f"Пользователю {member.mention} выдано предупреждение за: {reason}\n"
                f"Текущие предупреждения: {new_count}/3",
                mention_author=False,
            )

    @commands.hybrid_command(name="sunpred", description="Снять одно предупреждение сотруднику")
    @app_commands.describe(member="Сотрудник")
    @ensure_staff_channel()
    async def sunpred(self, ctx: commands.Context, member: discord.Member):
        success = await self.db.remove_warning(member.id)

        if not success:
            await ctx.reply(
                f"У пользователя {member.mention} нет предупреждений для снятия.",
                mention_author=False,
            )
            return

        current = await self.db.get_warnings_count(member.id)
        await ctx.reply(
            f"У пользователя {member.mention} снято 1 предупреждение.\n"
            f"Текущие предупреждения: {current}/3",
            mention_author=False,
        )

    @commands.hybrid_command(name="sinvite", description="Добавить сотрудника в систему")
    @app_commands.describe(member="Сотрудник")
    @ensure_staff_channel()
    async def sinvite(self, ctx: commands.Context, member: discord.Member) -> None:
        current = await self.db.get_moderator(member.id)
        guessed_rank = next(
            (ROLE_ID_TO_RANK_KEY[r.id] for r in member.roles if r.id in ROLE_ID_TO_RANK_KEY),
            "helper"
        )

        if current:
            await self.db.update_nickname(member.id, member.display_name)
        else:
            await self.db.upsert_moderator(
                member.id,
                member.display_name,
                guessed_rank,
                access_level="staff"
            )

        await ctx.reply(
            f"{member.mention} добавлен в систему сотрудников.",
            mention_author=False,
        )

    @commands.hybrid_command(name="sremovepass", description="Отключить доступ сотруднику")
    @app_commands.describe(member="Сотрудник")
    @ensure_staff_channel()
    async def sremovepass(self, ctx: commands.Context, member: discord.Member) -> None:
        await self.db.clear_access(member.id)
        await ctx.reply(f"Доступ для {member.mention} отключен.", mention_author=False)

    @commands.command(name="mentor")
    @ensure_staff_channel()
    async def mentor(self, ctx: commands.Context, mentor: discord.Member) -> None:
        replied_message = await resolve_replied_message(ctx)
        if not replied_message:
            return

        target_user = replied_message.author
        moderator = await self.db.get_moderator(target_user.id)
        if not moderator:
            await self.db.upsert_moderator(
                user_id=target_user.id,
                nickname=target_user.display_name,
                rank_key="helper",
                access_level="staff",
            )

        await self.db.set_mentor(target_user.id, mentor.mention)
        await ctx.reply(
            f"Наставник **{mentor.display_name}** назначен сотруднику **{target_user.display_name}**.",
            mention_author=False,
        )

    @commands.hybrid_command(name="saddtime", description="Добавить дни до повышения")
    @app_commands.describe(member="Сотрудник", days="Количество дней")
    @ensure_staff_channel()
    async def saddtime(self, ctx: commands.Context, member: discord.Member, days: int) -> None:
        await self.db.add_promotion_days(member.id, days)
        await ctx.reply(f"{member.mention} добавлено **{days}** дн. до повышения.", mention_author=False)

    @commands.hybrid_command(name="sremovetime", description="Убрать дни до повышения")
    @app_commands.describe(member="Сотрудник", days="Количество дней")
    @ensure_staff_channel()
    async def sremovetime(self, ctx: commands.Context, member: discord.Member, days: int) -> None:
        await self.db.remove_promotion_days(member.id, days)
        await ctx.reply(f"У {member.mention} снято **{days}** дн. до повышения.", mention_author=False)

    @commands.hybrid_command(name="ssetrank", description="Установить ранг сотруднику")
    @app_commands.describe(member="Сотрудник", role="Роль ранга")
    @ensure_staff_channel()
    async def ssetrank(self, ctx: commands.Context, member: discord.Member, role: discord.Role) -> None:
        if role.id not in ROLE_ID_TO_RANK_KEY:
            await ctx.reply("Эта роль не связана ни с одним рангом в config.py/.env.", mention_author=False)
            return

        rank_key = ROLE_ID_TO_RANK_KEY[role.id]
        roles_to_remove = [guild_role for guild_role in member.roles if guild_role.id in ROLE_ID_TO_RANK_KEY]
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="Смена ранга сотрудника")

        await member.add_roles(role, reason="Назначение нового ранга сотрудника")

        existing = await self.db.get_moderator(member.id)
        if existing:
            await self.db.set_rank(member.id, rank_key)
            await self.db.update_nickname(member.id, member.display_name)
        else:
            await self.db.upsert_moderator(
                member.id,
                member.display_name,
                rank_key,
                access_level="staff"
            )

        await ctx.reply(
            f"{member.mention} установлен ранг **{rank_title(rank_key)}** и выдана роль {role.mention}.",
            mention_author=False,
        )

    @commands.hybrid_command(name="bigcoins", description="Установить количество BIGCOINS сотруднику")
    @app_commands.describe(member="Сотрудник", amount="Количество BIGCOINS")
    @ensure_staff_channel()
    async def bigcoins(self, ctx: commands.Context, member: discord.Member, amount: int) -> None:
        if amount < 0:
            await ctx.reply("Количество BIGCOINS не может быть отрицательным.", mention_author=False)
            return

        moderator = await self.db.get_moderator(member.id)
        if not moderator:
            guessed_rank = next(
                (ROLE_ID_TO_RANK_KEY[r.id] for r in member.roles if r.id in ROLE_ID_TO_RANK_KEY),
                "helper"
            )
            await self.db.upsert_moderator(
                member.id,
                member.display_name,
                guessed_rank,
                access_level="staff"
            )

        await self.db.set_bigcoins(member.id, amount)
        await self.db.update_nickname(member.id, member.display_name)

        await ctx.reply(
            f"{member.mention} установлено **{amount} BIGCOINS**.",
            mention_author=False,
        )

    @commands.command(name="saccept")
    @ensure_reports_channel()
    async def saccept(self, ctx: commands.Context) -> None:
        replied = await resolve_replied_message(ctx)
        if not replied:
            return

        author = replied.author
        record = await self.db.get_moderator(author.id)
        if not record or record.get("access_level") == "none":
            await ctx.reply("Автор сообщения не найден в базе сотрудников.", mention_author=False)
            return

        saved = await self.db.log_report_review(replied.id, author.id, ctx.author.id, "accepted")
        if not saved:
            await ctx.reply("Этот отчет уже был рассмотрен ранее.", mention_author=False)
            return

        rank_key = (record.get("rank_key") or "helper").strip().lower()
        salary = RANKS.get(rank_key, RANKS["helper"]).salary
        await self.db.increment_accepted_report(author.id, salary)
        await ctx.reply(
            f"✅ Отчет сотрудника {author.mention} принят. Начислено **{salary} BIGCOINS**.",
            mention_author=False,
        )

    @commands.command(name="sdeny")
    @ensure_reports_channel()
    async def sdeny(self, ctx: commands.Context, *, reason: Optional[str] = None) -> None:
        replied = await resolve_replied_message(ctx)
        if not replied:
            return

        author = replied.author
        record = await self.db.get_moderator(author.id)
        if not record or record.get("access_level") == "none":
            await ctx.reply("Автор сообщения не найден в базе сотрудников.", mention_author=False)
            return

        saved = await self.db.log_report_review(replied.id, author.id, ctx.author.id, "denied", reason=reason)
        if not saved:
            await ctx.reply("Этот отчет уже был рассмотрен ранее.", mention_author=False)
            return

        warn_reason = reason or "Отчет не принят"
        await self.db.add_warn(author.id, warn_reason, ctx.author.id)
        await ctx.reply(
            f"❌ Отчет сотрудника {author.mention} не принят. Выдан 1 варн. Причина: **{warn_reason}**",
            mention_author=False,
        )

    @commands.hybrid_command(name="swarn", description="Выдать варн сотруднику")
    @app_commands.describe(member="Сотрудник", reason="Причина варна")
    @ensure_staff_channel()
    async def swarn(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        await self.db.add_warn(member.id, reason, ctx.author.id)
        await ctx.reply(f"{member.mention} получил варн. Причина: **{reason}**", mention_author=False)

    @commands.hybrid_command(name="sunwarn", description="Снять последний активный варн")
    @app_commands.describe(member="Сотрудник")
    @ensure_staff_channel()
    async def sunwarn(self, ctx: commands.Context, member: discord.Member) -> None:
        removed = await self.db.remove_latest_warn(member.id)
        if not removed:
            await ctx.reply("У пользователя нет активных варнов.", mention_author=False)
            return
        await ctx.reply(f"С {member.mention} снят последний активный варн.", mention_author=False)

    @commands.hybrid_command(name="skick", description="Снять сотрудника с должности")
    @app_commands.describe(member="Сотрудник")
    @ensure_staff_channel()
    async def skick(self, ctx: commands.Context, member: discord.Member) -> None:
        roles_to_remove = [role for role in member.roles if role.id != DEFAULT_ROLE_ID and role != ctx.guild.default_role]
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="Снятие сотрудника с должности")

        await self.db.clear_access(member.id)
        await ctx.reply(
            f"У {member.mention} сняты все роли, кроме дефолтной. Доступ к боту отключен.",
            mention_author=False,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))