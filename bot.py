import json
import logging
import os
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


def load_config(path: str = "config.json") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. Copy config.example.json to config.json."
        )

    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s:%(name)s: %(message)s",
    )


class MonPremierBot(commands.Bot):
    def __init__(self, config: dict):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=config.get("PREFIX", "!"),
            intents=intents,
            help_command=None,
        )

        self.config = config
        self.owner_id = config.get("OWNER_ID")

        # Data folder
        self.data_path = Path("data")
        self.data_path.mkdir(exist_ok=True)

    async def setup_hook(self) -> None:
        # Register cogs
        from cogs.moderation import ModerationCog
        from cogs.fun import FunCog
        from cogs.economy import EconomyCog
        from cogs.automations import AutomationsCog
        from cogs.stats import StatsCog
        from cogs.music import MusicCog
        from cogs.tickets import TicketsCog

        await self.add_cog(ModerationCog(self))
        await self.add_cog(FunCog(self))
        await self.add_cog(EconomyCog(self))
        await self.add_cog(AutomationsCog(self))
        await self.add_cog(StatsCog(self))
        await self.add_cog(MusicCog(self))
        await self.add_cog(TicketsCog(self))

        # Sync global commands (or per-guild if GUILD_ID set)
        guild_id = self.config.get("GUILD_ID")
        if guild_id:
            guild = discord.Object(id=guild_id)
            await self.tree.sync(guild=guild)
            logging.info(f"Synced commands to guild {guild_id}")
        else:
            await self.tree.sync()
            logging.info("Synced global commands")

    async def on_ready(self):
        logging.info(f"Connected as {self.user} (ID: {self.user.id})")
        if self.owner_id:
            owner = await self.fetch_user(int(self.owner_id))
            logging.info(f"Bot owner set to {owner}")


def main():
    setup_logging()

    # Charge un fichier .env si présent pour faciliter le développement.
    load_dotenv()

    config = load_config()

    bot = MonPremierBot(config)

    # Prefer token from environment variable to avoid committing it to config files.
    token = os.getenv("DISCORD_TOKEN") or config.get("DISCORD_TOKEN")
    logging.info("Token source: %s", "env" if os.getenv("DISCORD_TOKEN") else "config")
    logging.info("Token loaded: %s (len=%s)", "yes" if token else "no", len(token) if token else 0)

    if not token or token in ("YOUR_TOKEN_HERE", ""):  # aide à détecter un placeholder
        raise RuntimeError(
            "DISCORD_TOKEN is not set. "
            "Place ton token dans la variable d'environnement DISCORD_TOKEN "
            "ou dans config.json (mais ne le commit pas)."
        )

    try:
        bot.run(token)
    except discord.LoginFailure:
        raise RuntimeError(
            "Échec de connexion : token invalide. "
            "Vérifie ton token et régénère-le dans le Portail Développeur Discord."
        )


if __name__ == "__main__":
    main()
