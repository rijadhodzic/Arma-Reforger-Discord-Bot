import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ARMA_API_HOST = os.getenv("ARMA_API_HOST", "http://localhost:8080")
ARMA_API_USER = os.getenv("ARMA_API_USER", "admin")
ARMA_API_PASS = os.getenv("ARMA_API_PASS", "")
ADMIN_ROLE_NAME = os.getenv("ADMIN_ROLE_NAME", "Admin")

# ── Arma REST client ─────────────────────────────────────────────────────────

class ArmaClient:
    def __init__(self):
        self.base = ARMA_API_HOST.rstrip("/")
        self.auth = aiohttp.BasicAuth(ARMA_API_USER, ARMA_API_PASS)

    async def _get(self, path: str):
        async with aiohttp.ClientSession(auth=self.auth) as s:
            async with s.get(f"{self.base}{path}") as r:
                r.raise_for_status()
                return await r.json()

    async def _post(self, path: str, payload: dict):
        async with aiohttp.ClientSession(auth=self.auth) as s:
            async with s.post(f"{self.base}{path}", json=payload) as r:
                r.raise_for_status()
                try:
                    return await r.json()
                except Exception:
                    return {"status": r.status}

    async def _delete(self, path: str):
        async with aiohttp.ClientSession(auth=self.auth) as s:
            async with s.delete(f"{self.base}{path}") as r:
                r.raise_for_status()
                return {"status": r.status}

    async def get_players(self):
        return await self._get("/api/v1/session/players")

    async def kick_player(self, uid: str, reason: str = ""):
        return await self._post("/api/v1/session/players/kick", {"uid": uid, "reason": reason})

    async def ban_player(self, uid: str, reason: str = "", duration: int = 0):
        payload = {"uid": uid, "reason": reason}
        if duration > 0:
            payload["timeoutSeconds"] = duration * 60
        return await self._post("/api/v1/session/players/ban", payload)

    async def get_bans(self):
        return await self._get("/api/v1/session/bans")

    async def unban(self, ban_id: str):
        return await self._delete(f"/api/v1/session/bans/{ban_id}")


arma = ArmaClient()

# ── Bot setup ─────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def is_admin():
    async def predicate(interaction: discord.Interaction):
        role = discord.utils.get(interaction.user.roles, name=ADMIN_ROLE_NAME)
        if role is None:
            await interaction.response.send_message(
                f"❌ You need the **{ADMIN_ROLE_NAME}** role to use this command.",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

def player_embed(players: list) -> discord.Embed:
    embed = discord.Embed(title="🎮 Online Players", color=0x2f6f3a)
    if not players:
        embed.description = "*No players online.*"
    else:
        lines = []
        for i, p in enumerate(players, 1):
            name = p.get("name", "Unknown")
            uid = p.get("uid", "?")
            lines.append(f"`{i}.` **{name}**\n└UID: `{uid}`")
        embed.description = "\n\n".join(lines)
        embed.set_footer(text=f"{len(players)} player(s) online")
    return embed

# ── Helper: resolve player name → uid ────────────────────────────────────────

async def resolve_uid(name_or_uid: str):
    """Returns (uid, display_name) or raises ValueError if not found."""
    data = await arma.get_players()
    players = data if isinstance(data, list) else data.get("players", [])
    # exact UID match first
    for p in players:
        if p.get("uid") == name_or_uid:
            return p["uid"], p.get("name", name_or_uid)
    # case-insensitive name match
    needle = name_or_uid.lower()
    matches = [p for p in players if needle in p.get("name", "").lower()]
    if len(matches) == 1:
        return matches[0]["uid"], matches[0].get("name", name_or_uid)
    if len(matches) > 1:
        names = ", ".join(p.get("name", "?") for p in matches)
        raise ValueError(f"Ambiguous name — matched: {names}. Use the UID instead.")
    raise ValueError(f"Player `{name_or_uid}` not found on the server.")

# ── Slash commands ────────────────────────────────────────────────────────────

@bot.tree.command(name="players", description="List all players currently on the Arma Reforger server.")
@is_admin()
async def players(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    try:
        data = await arma.get_players()
        player_list = data if isinstance(data, list) else data.get("players", [])
        await interaction.followup.send(embed=player_embed(player_list))
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to fetch players: `{e}`")


@bot.tree.command(name="kick", description="Kick a player from the Arma Reforger server.")
@app_commands.describe(player="Player name or UID", reason="Reason for kick")
@is_admin()
async def kick(interaction: discord.Interaction, player: str, reason: str = "No reason given"):
    await interaction.response.defer(ephemeral=False)
    try:
        uid, display = await resolve_uid(player)
        await arma.kick_player(uid, reason)
        embed = discord.Embed(
            title="👢 Player Kicked",
            color=0xe67e22,
            description=f"**{display}** has been kicked."
        )
        embed.add_field(name="UID", value=f"`{uid}`", inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.set_footer(text=f"By {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Kick failed: `{e}`")


@bot.tree.command(name="ban", description="Ban a player from the Arma Reforger server.")
@app_commands.describe(
    player="Player name or UID",
    reason="Reason for ban",
    duration="Ban duration in minutes (0 = permanent)"
)
@is_admin()
async def ban(interaction: discord.Interaction, player: str, reason: str = "No reason given", duration: int = 0):
    await interaction.response.defer(ephemeral=False)
    try:
        uid, display = await resolve_uid(player)
        await arma.ban_player(uid, reason, duration)
        duration_str = f"{duration} minute(s)" if duration > 0 else "Permanent"
        embed = discord.Embed(
            title="🔨 Player Banned",
            color=0xe74c3c,
            description=f"**{display}** has been banned."
        )
        embed.add_field(name="UID", value=f"`{uid}`", inline=True)
        embed.add_field(name="Duration", value=duration_str, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"By {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Ban failed: `{e}`")


@bot.tree.command(name="bans", description="List all active bans on the Arma Reforger server.")
@is_admin()
async def bans(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    try:
        data = await arma.get_bans()
        ban_list = data if isinstance(data, list) else data.get("bans", [])
        embed = discord.Embed(title="🚫 Active Bans", color=0xe74c3c)
        if not ban_list:
            embed.description = "*No active bans.*"
        else:
            lines = []
            for b in ban_list:
                bid = b.get("id", "?")
                uid = b.get("uid", "?")
                reason = b.get("reason", "-")
                lines.append(f"ID: `{bid}` · UID: `{uid}`\n└Reason: {reason}")
            embed.description = "\n\n".join(lines)
            embed.set_footer(text=f"{len(ban_list)} active ban(s)")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to fetch bans: `{e}`")


@bot.tree.command(name="unban", description="Remove a ban by ban ID.")
@app_commands.describe(ban_id="The ban ID (from /bans)")
@is_admin()
async def unban(interaction: discord.Interaction, ban_id: str):
    await interaction.response.defer(ephemeral=False)
    try:
        await arma.unban(ban_id)
        embed = discord.Embed(
            title="✅ Ban Removed",
            color=0x2ecc71,
            description=f"Ban `{ban_id}` has been lifted."
        )
        embed.set_footer(text=f"By {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Unban failed: `{e}`")


# ── Events ────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user} — slash commands synced.")
    print(f"   Arma API: {ARMA_API_HOST}")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set in .env")
    bot.run(DISCORD_TOKEN)
