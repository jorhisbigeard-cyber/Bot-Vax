import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


def _load_wallet(path: Path, default: dict):
    if not path.exists():
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_wallet(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class EconomyCog(commands.Cog):
    """Système d'économie simple basé sur un fichier JSON."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.wallet_file = self.bot.data_path / "wallets.json"
        self.wallets = _load_wallet(self.wallet_file, {})

    def _get_balance(self, user_id: int) -> int:
        return self.wallets.get(str(user_id), 0)

    def _set_balance(self, user_id: int, amount: int):
        self.wallets[str(user_id)] = amount
        _save_wallet(self.wallet_file, self.wallets)

    # Groupe de commandes économie
    économie = app_commands.Group(name="économie", description="Système d'économie")

    @économie.command(name="balance", description="Affiche le solde d'un joueur")
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        """Affiche le solde d'un joueur."""
        member = member or interaction.user
        bal = self._get_balance(member.id)
        await interaction.response.send_message(f"💰 {member.display_name} a {bal} pièces.")

    @économie.command(name="daily", description="Réclame une récompense quotidienne")
    async def daily(self, interaction: discord.Interaction):
        """Réclame une récompense quotidienne."""
        current = self._get_balance(interaction.user.id)
        reward = 100
        self._set_balance(interaction.user.id, current + reward)
        await interaction.response.send_message(f"Tu as reçu {reward} pièces ! Nouveau solde : {current + reward}.")
