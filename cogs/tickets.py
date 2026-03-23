import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View, Button


class TicketsCog(commands.Cog):
    """Système de tickets pour le support."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Groupe de commandes tickets
    tickets = app_commands.Group(name="tickets", description="Système de tickets")

    @tickets.command(name="panel", description="Envoie le panneau de tickets")
    async def panel(self, interaction: discord.Interaction):
        """Envoie le panneau de tickets avec menu déroulant."""
        # Vérifier si l'utilisateur a les permissions
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
            return

        # Obtenir la bannière du serveur
        server_banner = interaction.guild.banner.url if interaction.guild.banner else None

        embed = discord.Embed(
            title="🎫 Centre de Support",
            description="Choisissez le type de ticket dans le menu ci-dessous.",
            color=0x2b2d31
        )
        if server_banner:
            embed.set_image(url=server_banner)

        # Créer le menu déroulant
        select = Select(
            custom_id="ticket_select",
            placeholder="Choisissez un type de ticket...",
            options=[
                discord.SelectOption(
                    label="Support général",
                    value="support",
                    emoji="💬",
                    description="Pour toute question générale"
                ),
                discord.SelectOption(
                    label="Plainte / Signalement",
                    value="report",
                    emoji="⚠️",
                    description="Pour signaler un problème"
                ),
                discord.SelectOption(
                    label="Partenariat",
                    value="partner",
                    emoji="🤝",
                    description="Pour proposer un partenariat"
                )
            ]
        )

        async def select_callback(interaction: discord.Interaction):
            await self.create_ticket(interaction, select.values[0])

        select.callback = select_callback

        view = View()
        view.add_item(select)

        await interaction.response.send_message(embed=embed, view=view)

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        """Crée un ticket basé sur le type sélectionné."""
        user = interaction.user

        # Définir les permissions
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Ajouter les permissions pour le rôle staff si configuré
        staff_role_id = self.bot.config.get("STAFF_ROLE_ID")
        if staff_role_id:
            staff_role = interaction.guild.get_role(int(staff_role_id))
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Créer le canal
        type_names = {
            "support": "support",
            "report": "signalement",
            "partner": "partenariat"
        }

        channel_name = f"ticket-{type_names.get(ticket_type, 'general')}-{user.name}"
        channel = await interaction.guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            category=interaction.channel.category
        )

        # Embed de bienvenue dans le ticket
        embed = discord.Embed(
            title="🎫 Ticket ouvert",
            description=f"**Type:** {ticket_type.title()}\n**Créé par:** {user.mention}\n\nMerci d'avoir ouvert un ticket. Un membre du staff va vous répondre.",
            color=0x2b2d31
        )

        # Bouton pour fermer
        close_button = Button(label="Fermer le ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")

        async def close_callback(interaction: discord.Interaction):
            # Vérifier permissions
            if interaction.user.guild_permissions.manage_channels or interaction.user == user:
                await interaction.response.send_message("🔒 Fermeture du ticket dans 3 secondes...")
                await interaction.message.edit(view=None)  # Désactiver le bouton
                # Attendre 3 secondes puis supprimer
                import asyncio
                await asyncio.sleep(3)
                await channel.delete()
            else:
                await interaction.response.send_message("❌ Vous n'avez pas la permission de fermer ce ticket.", ephemeral=True)

        close_button.callback = close_callback

        view = View()
        view.add_item(close_button)

        await channel.send(content=f"{user.mention}", embed=embed, view=view)
        await interaction.response.send_message(f"✅ Votre ticket a été créé : {channel.mention}", ephemeral=True)

    @tickets.command(name="close", description="Ferme le ticket actuel")
    async def close(self, interaction: discord.Interaction):
        """Ferme le ticket actuel."""
        if "ticket" in interaction.channel.name:
            await interaction.response.send_message("🔒 Fermeture du ticket dans 3 secondes...")
            import asyncio
            await asyncio.sleep(3)
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ Cette commande ne peut être utilisée que dans un canal ticket.", ephemeral=True)

    @tickets.command(name="add", description="Ajoute quelqu'un au ticket")
    async def add(self, interaction: discord.Interaction, member: discord.Member):
        """Ajoute quelqu'un au ticket."""
        if "ticket" in interaction.channel.name:
            await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
            await interaction.response.send_message(f"✅ {member.mention} ajouté au ticket.")
        else:
            await interaction.response.send_message("❌ Cette commande ne peut être utilisée que dans un canal ticket.", ephemeral=True)