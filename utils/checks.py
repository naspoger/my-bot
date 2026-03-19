from __future__ import annotations

import discord
from discord.ext import commands

from config import ROOT_ADMIN_IDS, STATS_CHANNEL_ID, REPORTS_CHANNEL_ID


def is_root_admin(user_id: int) -> bool:
    return user_id in ROOT_ADMIN_IDS


def _is_allowed_channel(ctx: commands.Context, allowed_channel_id: int) -> bool:
    if not allowed_channel_id:
        return True

    # Обычный текстовый канал
    if ctx.channel.id == allowed_channel_id:
        return True

    # Форум/тред: команда пишется внутри поста, а parent — это сам форум-канал
    parent = getattr(ctx.channel, "parent", None)
    if parent and parent.id == allowed_channel_id:
        return True

    return False


def ensure_staff_channel():
    async def predicate(ctx: commands.Context) -> bool:
        if _is_allowed_channel(ctx, STATS_CHANNEL_ID):
            return True

        await ctx.reply(
            "Эту команду можно использовать только в стафф-канале.",
            mention_author=False,
        )
        return False

    return commands.check(predicate)


def ensure_reports_channel():
    async def predicate(ctx: commands.Context) -> bool:
        if _is_allowed_channel(ctx, REPORTS_CHANNEL_ID):
            return True

        await ctx.reply(
            "Эту команду можно использовать только в канале отчетов.",
            mention_author=False,
        )
        return False

    return commands.check(predicate)


def ensure_root_admin():
    async def predicate(ctx: commands.Context) -> bool:
        if is_root_admin(ctx.author.id):
            return True

        await ctx.reply(
            "У вас нет прав на использование этой команды.",
            mention_author=False,
        )
        return False

    return commands.check(predicate)


async def resolve_replied_message(ctx: commands.Context) -> discord.Message | None:
    if not ctx.message.reference:
        await ctx.reply(
            "Эту команду нужно использовать ответом на сообщение.",
            mention_author=False,
        )
        return None

    try:
        return await ctx.channel.fetch_message(ctx.message.reference.message_id)
    except Exception:
        await ctx.reply(
            "Не удалось получить сообщение, на которое вы ответили.",
            mention_author=False,
        )
        return None