import discord
from discord import app_commands
from discord.ext import commands


class ModerationCog(commands.Cog):
    """Modération & sécurité - logs, sanctions, auto-modération."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Exemple : envoyer un message de bienvenue dans le premier channel texte.
        if member.guild.system_channel:
            await member.guild.system_channel.send(
                f"Bienvenue {member.mention} ! Tapez /help pour voir les commandes.")

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        # TODO: enregistrer dans un log (fichier ou base de données)
        pass

    # Groupe de commandes modération
    moderation = app_commands.Group(name="modération", description="Commandes de modération")

    @moderation.command(name="kick", description="Expulse un membre du serveur")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison fournie"):
        """Expulse un membre du serveur."""
        await member.kick(reason=reason)
        await interaction.response.send_message(f"{member} a été expulsé. Raison : {reason}")

    @moderation.command(name="ban", description="Bannit un membre du serveur")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison fournie"):
        """Bannit un membre du serveur."""
        await member.ban(reason=reason)
        await interaction.response.send_message(f"{member} a été banni. Raison : {reason}")

    @moderation.command(name="unban", description="Débannit un utilisateur")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user: discord.User, reason: str = "Aucune raison fournie"):
        """Débannit un utilisateur."""
        await interaction.guild.unban(user, reason=reason)
        await interaction.response.send_message(f"{user} a été débanni. Raison : {reason}")

    @moderation.command(name="mute", description="Mute un membre du serveur")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: int = None, reason: str = "Aucune raison fournie"):
        """Mute un membre du serveur."""
        if duration:
            from datetime import timedelta
            await member.timeout(timedelta(minutes=duration), reason=reason)
            await interaction.response.send_message(f"{member} a été mute pour {duration} minutes. Raison : {reason}")
        else:
            await member.timeout(None, reason=reason)
            await interaction.response.send_message(f"{member} a été mute indéfiniment. Raison : {reason}")

    @moderation.command(name="unmute", description="Unmute un membre du serveur")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison fournie"):
        """Unmute un membre du serveur."""
        await member.timeout(None, reason=reason)
        await interaction.response.send_message(f"{member} a été unmute. Raison : {reason}")

    @moderation.command(name="warn", description="Avertit un membre")
    @app_commands.checks.has_permissions(kick_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison fournie"):
        """Avertit un membre."""
        await interaction.response.send_message(f"⚠️ {member} a été averti. Raison : {reason}")

    @moderation.command(name="clear", description="Supprime un nombre de messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int = 10):
        """Supprime un nombre de messages."""
        if amount < 1 or amount > 100:
            await interaction.response.send_message("Le nombre de messages doit être entre 1 et 100.")
            return
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"Supprimé {len(deleted)} messages.", ephemeral=True)

    @moderation.command(name="slowmode", description="Active le mode lent dans le canal")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int = 0):
        """Active le mode lent dans le canal."""
        await interaction.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await interaction.response.send_message("Mode lent désactivé.")
        else:
            await interaction.response.send_message(f"Mode lent activé : {seconds} secondes.")

    @moderation.command(name="lock", description="Verrouille un canal")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Verrouille un canal."""
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(f"🔒 {channel.mention} verrouillé.")

    @moderation.command(name="unlock", description="Déverrouille un canal")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Déverrouille un canal."""
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=None)
        await interaction.response.send_message(f"🔓 {channel.mention} déverrouillé.")
