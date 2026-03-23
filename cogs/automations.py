import random

import discord
from discord import app_commands
from discord.ext import commands, tasks


class AutomationsCog(commands.Cog):
    """Automatisations & qualité de vie"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        # Démarre la boucle une fois le bot prêt (évite le NoneType ws).
        if not self.status_cycle.is_running():
            self.status_cycle.start()

    def cog_unload(self):
        self.status_cycle.cancel()

    @tasks.loop(minutes=10)
    async def status_cycle(self):
        statuses = [
            "MonPremierBot | /help | réalisé par la team 2k!",
            "Modération, musique, mini-jeux… | réalisé par la team 2k!",
            "Demande /invite pour m'ajouter ! | réalisé par la team 2k!",
        ]
        activity = discord.Game(name=random.choice(statuses))
        await self.bot.change_presence(activity=activity)

    @status_cycle.before_loop
    async def before_status_cycle(self):
        await self.bot.wait_until_ready()

    # Groupe de commandes automatisations
    automatisations = app_commands.Group(name="automatisations", description="Automatisations et utilitaires")

    @automatisations.command(name="say", description="Fait parler le bot dans le canal courant")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def say(self, interaction: discord.Interaction, message: str):
        """Fait parler le bot dans le canal courant."""
        await interaction.channel.send(message)
        await interaction.response.send_message("Message envoyé !", ephemeral=True)

    @automatisations.command(name="poll", description="Crée un sondage simple")
    async def poll(self, interaction: discord.Interaction, question: str, options: str):
        """Crée un sondage simple.

        Utilise `|` pour séparer les options, ex :
        /poll "Ton choix ?" "Oui | Non | Peut-être"
        """
        opts = [opt.strip() for opt in options.split("|") if opt.strip()]
        if len(opts) == 0:
            await interaction.response.send_message("Donne au moins une option (séparées par |).")
            return
        if len(opts) > 10:
            await interaction.response.send_message("Maximum 10 options (séparées par |).")
            return

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        description = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(opts))
        embed = discord.Embed(title=question, description=description, color=discord.Color.blurple())
        message = await interaction.channel.send(embed=embed)
        for i in range(len(opts)):
            await message.add_reaction(emojis[i])
        await interaction.response.send_message("Sondage créé !", ephemeral=True)
