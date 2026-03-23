import discord
from discord import app_commands
from discord.ext import commands


class StatsCog(commands.Cog):
    """Statistiques & tracking basiques."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Groupe de commandes utilitaires
    utilitaires = app_commands.Group(name="utilitaires", description="Infos et gestion")

    @utilitaires.command(name="serverstats", description="Affiche des statistiques serveur simples")
    async def serverstats(self, interaction: discord.Interaction):
        """Affiche des statistiques serveur simples."""
        guild = interaction.guild
        embed = discord.Embed(title="Statistiques du serveur", color=discord.Color.green())
        embed.add_field(name="Membres", value=guild.member_count, inline=True)
        embed.add_field(name="Textuels", value=len(guild.text_channels), inline=True)
        embed.add_field(name="Vocaux", value=len(guild.voice_channels), inline=True)
        await interaction.response.send_message(embed=embed)

    @utilitaires.command(name="userinfo", description="Affiche des informations sur un utilisateur")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        """Affiche des informations sur un utilisateur."""
        member = member or interaction.user
        embed = discord.Embed(title=f"Infos de {member}", color=discord.Color.blurple())
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Compte créé le", value=member.created_at.strftime("%Y-%m-%d %H:%M"), inline=True)
        embed.add_field(name="Rejoint le", value=member.joined_at.strftime("%Y-%m-%d %H:%M"), inline=True)
        await interaction.response.send_message(embed=embed)

    @utilitaires.command(name="serverinfo", description="Affiche des informations sur le serveur")
    async def serverinfo(self, interaction: discord.Interaction):
        """Affiche des informations sur le serveur."""
        guild = interaction.guild
        embed = discord.Embed(title=f"Informations sur {guild.name}", color=discord.Color.blue())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="Propriétaire", value=guild.owner.mention, inline=True)
        embed.add_field(name="Créé le", value=guild.created_at.strftime("%Y-%m-%d %H:%M"), inline=True)
        embed.add_field(name="Niveau de boost", value=guild.premium_tier, inline=True)
        embed.add_field(name="Membres", value=guild.member_count, inline=True)
        embed.add_field(name="Rôles", value=len(guild.roles), inline=True)
        embed.add_field(name="Emojis", value=len(guild.emojis), inline=True)
        await interaction.response.send_message(embed=embed)

    @utilitaires.command(name="botinfo", description="Affiche des informations sur le bot")
    async def botinfo(self, interaction: discord.Interaction):
        """Affiche des informations sur le bot."""
        embed = discord.Embed(title="Informations du bot", color=discord.Color.purple())
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url)
        embed.add_field(name="Nom", value=self.bot.user.name, inline=True)
        embed.add_field(name="ID", value=self.bot.user.id, inline=True)
        embed.add_field(name="Créé le", value=self.bot.user.created_at.strftime("%Y-%m-%d %H:%M"), inline=True)
        embed.add_field(name="Serveurs", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Utilisateurs", value=sum(guild.member_count for guild in self.bot.guilds), inline=True)
        embed.add_field(name="Latence", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Développé par", value="la team 2k!", inline=True)
        await interaction.response.send_message(embed=embed)

    @utilitaires.command(name="help", description="Affiche toutes les commandes disponibles")
    async def help(self, interaction: discord.Interaction):
        """Affiche toutes les commandes disponibles."""
        embed = discord.Embed(title="Aide - Commandes du bot", color=discord.Color.green())

        embed.add_field(name="👮 /modération", value="`ban`, `kick`, `mute`, `unmute`, `warn`, `clear`, `slowmode`, `lock`, `unlock`", inline=False)
        embed.add_field(name="🎵 /musique", value="`play`, `pause`, `resume`, `skip`, `stop`, `queue`, `volume`", inline=False)
        embed.add_field(name="🎉 /fun", value="`ping`, `8ball`, `coinflip`, `meme`, `joke`, `avatar`", inline=False)
        embed.add_field(name="💰 /économie", value="`balance`, `daily`", inline=False)
        embed.add_field(name="🛠️ /utilitaires", value="`help`, `userinfo`, `serverinfo`, `botinfo`", inline=False)
        embed.add_field(name="🎫 /tickets", value="`ticket`, `close`, `add`, `remove`", inline=False)
        embed.add_field(name="🤖 /automatisations", value="`say`, `poll`", inline=False)

        embed.set_footer(text="Toutes les commandes sont disponibles en slash commands | réalisé par la team 2k!")
        await interaction.response.send_message(embed=embed)
