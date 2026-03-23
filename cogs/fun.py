import random

import discord
from discord import app_commands
from discord.ext import commands


class FunCog(commands.Cog):
    """Fun, mini‑jeux, commandes RP."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Groupe de commandes fun
    fun = app_commands.Group(name="fun", description="Commandes amusantes")

    @fun.command(name="ping", description="Test de latence")
    async def ping(self, interaction: discord.Interaction):
        """Test de latence."""
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong ! Latence : {latency} ms")

    @fun.command(name="8ball", description="Répond à une question comme un 8-ball")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        """Répond à une question comme un 8-ball."""
        responses = [
            "Oui.",
            "Non.",
            "Peut-être.",
            "C'est possible.",
            "Demande plus tard.",
            "Je n'en suis pas sûr.",
        ]
        await interaction.response.send_message(f"🎱 {random.choice(responses)}")

    @fun.command(name="coinflip", description="Lance une pièce")
    async def coinflip(self, interaction: discord.Interaction):
        """Lance une pièce."""
        await interaction.response.send_message(random.choice(["Pile", "Face"]))

    @fun.command(name="meme", description="Envoie un meme aléatoire")
    async def meme(self, interaction: discord.Interaction):
        """Envoie un meme aléatoire."""
        memes = [
            "https://i.imgur.com/ABC123.jpg",  # Placeholder
            "https://i.imgur.com/DEF456.jpg",  # Placeholder
        ]
        await interaction.response.send_message(random.choice(memes))

    @fun.command(name="joke", description="Raconte une blague")
    async def joke(self, interaction: discord.Interaction):
        """Raconte une blague."""
        jokes = [
            "Pourquoi les plongeurs plongent-ils toujours en arrière et jamais en avant ? Parce que sinon ils tombent dans le bateau !",
            "Quel est le comble pour un électricien ? De ne pas être au courant !",
        ]
        await interaction.response.send_message(random.choice(jokes))

    @fun.command(name="avatar", description="Affiche l'avatar d'un utilisateur")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        """Affiche l'avatar d'un utilisateur."""
        member = member or interaction.user
        embed = discord.Embed(title=f"Avatar de {member.display_name}")
        embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await interaction.response.send_message(embed=embed)
