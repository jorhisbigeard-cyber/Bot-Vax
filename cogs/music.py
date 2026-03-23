import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
import yt_dlp as youtube_dl
from collections import deque
import random
import json
import os
from pathlib import Path

# Configuration yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class MusicControlView(discord.ui.View):
    """Panneau de contrôle musical avec boutons."""

    def __init__(self, cog, guild):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild = guild

    def _get_vc(self):
        return self.guild.voice_client

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.secondary)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self._get_vc()
        if not vc:
            return await interaction.response.send_message("❌ Bot pas connecté", ephemeral=True)
        if vc.is_playing():
            vc.pause()
            button.emoji = "▶️"
        elif vc.is_paused():
            vc.resume()
            button.emoji = "⏸️"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self._get_vc()
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
        await interaction.response.send_message("⏭️ Piste suivante", ephemeral=True)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        queue = self.cog.get_queue(self.guild.id)
        if len(queue) < 2:
            return await interaction.response.send_message("❌ Pas assez de pistes", ephemeral=True)
        lst = list(queue)
        random.shuffle(lst)
        queue.clear()
        queue.extend(lst)
        await interaction.response.send_message("🔀 File mélangée", ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary)
    async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        mode = self.cog.loop_modes.get(self.guild.id, 'none')
        if mode == 'none':
            self.cog.loop_modes[self.guild.id] = 'track'
            button.style = discord.ButtonStyle.success
            msg = "🔁 Répétition de la piste activée"
        elif mode == 'track':
            self.cog.loop_modes[self.guild.id] = 'queue'
            button.style = discord.ButtonStyle.primary
            msg = "🔁 Répétition de la file activée"
        else:
            self.cog.loop_modes[self.guild.id] = 'none'
            button.style = discord.ButtonStyle.secondary
            msg = "🔁 Répétition désactivée"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self._get_vc()
        if vc:
            self.cog.queues[self.guild.id] = deque()
            if self.guild.id in self.cog.current_tracks:
                del self.cog.current_tracks[self.guild.id]
            vc.stop()
        await interaction.response.send_message("⏹️ Lecture arrêtée", ephemeral=True)
        self.stop()


class SilenceAudio(discord.AudioSource):
    """Source audio silencieuse pour maintenir la connexion vocale active."""
    def read(self):
        # Retourne 20ms de silence PCM (3840 bytes = 48000Hz * 2ch * 2bytes * 0.02s)
        return b'\x00' * 3840

    def is_opus(self):
        return False


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('webpage_url', '')
        self.duration = data.get('duration', 0)
        self.thumbnail = data.get('thumbnail', '')
        self.uploader = data.get('uploader', 'Inconnu')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class MusicCog(commands.Cog):
    """Système de musique complet avec yt-dlp."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues = {}  # guild_id: deque of tracks
        self.current_tracks = {}  # guild_id: current track info
        self.loop_modes = {}  # guild_id: 'none', 'track', 'queue'
        self.volumes = {}  # guild_id: volume level (0-100)
        self.playlists = {}  # guild_id: {name: [tracks]}

        # Paramètres optionnels
        self.auto_disconnect = bot.config.get("MUSIC_AUTO_DISCONNECT", 60) if bot.config.get("MUSIC_AUTO_DISCONNECT") is not None else 60
        self.auto_reconnect = bot.config.get("MUSIC_AUTO_RECONNECT", True)

        self.data_path = Path("data")
        self.data_path.mkdir(exist_ok=True)
        self.check_alone.start()  # Démarrer la tâche de vérification
        self.keep_alive_task.start()  # Garder la connexion vocale active
        self.load_playlists()  # Charger les playlists sauvegardées

    def cog_unload(self):
        """Sauvegarder les données lors du déchargement."""
        self.save_playlists()
        self.check_alone.cancel()
        self.keep_alive_task.cancel()

    @tasks.loop(seconds=20)
    async def keep_alive_task(self):
        """Maintient la connexion vocale active avec du silence PCM."""
        for guild in self.bot.guilds:
            vc = guild.voice_client
            if vc and vc.is_connected() and not vc.is_playing() and not vc.is_paused():
                try:
                    vc.play(SilenceAudio(), after=lambda e: None)
                except Exception:
                    pass

    @keep_alive_task.before_loop
    async def before_keep_alive(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=1)
    async def check_alone(self):
        """Vérifie si le bot est seul dans les salons vocaux et se déconnecte."""
        if not self.auto_disconnect:
            return

        for guild in self.bot.guilds:
            vc = guild.voice_client
            if vc and vc.is_connected():
                # Compter les membres (exclure les bots)
                members = [m for m in vc.channel.members if not m.bot]
                if len(members) == 0:
                    # Attendre auto_disconnect secondes avant de quitter
                    await asyncio.sleep(self.auto_disconnect)
                    # Revérifier
                    members = [m for m in vc.channel.members if not m.bot]
                    if len(members) == 0:
                        await vc.disconnect()
                        # Ne pas vider la file pour pouvoir reprendre plus tard
                        if guild.id in self.current_tracks:
                            del self.current_tracks[guild.id]

    @check_alone.before_loop
    async def before_check_alone(self):
        await self.bot.wait_until_ready()

    def save_playlists(self):
        """Sauvegarde les playlists dans un fichier JSON."""
        try:
            data = {}
            for guild_id, playlists in self.playlists.items():
                data[str(guild_id)] = playlists

            with open(self.data_path / "playlists.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des playlists: {e}")

    def load_playlists(self):
        """Charge les playlists depuis le fichier JSON."""
        try:
            playlist_file = self.data_path / "playlists.json"
            if playlist_file.exists():
                with open(playlist_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for guild_id_str, playlists in data.items():
                    self.playlists[int(guild_id_str)] = playlists
        except Exception as e:
            print(f"Erreur lors du chargement des playlists: {e}")

    def get_queue(self, guild_id):
        """Récupère la file d'attente d'une guilde."""
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    def get_playlists(self, guild_id):
        """Récupère les playlists d'une guilde."""
        if guild_id not in self.playlists:
            self.playlists[guild_id] = {}
        return self.playlists[guild_id]

    async def play_next(self, guild):
        """Joue la piste suivante dans la file."""
        queue = self.get_queue(guild.id)
        loop_mode = self.loop_modes.get(guild.id, 'none')

        if not queue and loop_mode != 'track':
            return

        if loop_mode == 'track' and guild.id in self.current_tracks:
            # Rejouer la piste actuelle
            track = self.current_tracks[guild.id]
        elif queue:
            track = queue.popleft()
            if loop_mode == 'queue':
                queue.append(track)  # Remettre à la fin pour la boucle
        else:
            return

        self.current_tracks[guild.id] = track

        vc = guild.voice_client
        if vc:
            # Appliquer le volume
            volume = self.volumes.get(guild.id, 50) / 100
            track.source.volume = volume

            def after_playing(error):
                if error:
                    print(f'Player error: {error}')
                asyncio.run_coroutine_threadsafe(self.play_next(guild), self.bot.loop)

            vc.play(track.source, after=after_playing)

            # Envoyer un embed de la musique en cours avec boutons
            embed = discord.Embed(
                title="🎵 Lecture en cours",
                description=f"**{track.title}**\nPar {track.uploader}",
                color=discord.Color.blue()
            )
            if track.thumbnail:
                embed.set_thumbnail(url=track.thumbnail)
            embed.add_field(name="Durée", value=self.format_duration(track.duration), inline=True)

            view = MusicControlView(self, guild)

            # Essayer d'envoyer dans le canal de texte
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(embed=embed, view=view)
                    break

    # Groupe de commandes musique
    music = app_commands.Group(name="music", description="Commandes musique")

    @music.command(name="join", description="Faire rejoindre le bot dans ton salon vocal")
    async def join(self, interaction: discord.Interaction):
        """Fait rejoindre le bot dans le salon vocal."""
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Tu dois être dans un salon vocal !", ephemeral=True)
            return

        await interaction.response.defer()

        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client

        if vc and vc.is_connected():
            await vc.move_to(channel)
        else:
            vc = await channel.connect()

        await interaction.followup.send(f"✅ Rejoint {channel.mention}")

    @music.command(name="leave", description="Faire quitter le salon vocal")
    async def leave(self, interaction: discord.Interaction):
        """Fait quitter le salon vocal."""
        vc = interaction.guild.voice_client
        if vc and vc.is_connected():
            await interaction.response.defer()
            await vc.disconnect()
            if interaction.guild.id in self.queues:
                self.queues[interaction.guild.id].clear()
            if interaction.guild.id in self.current_tracks:
                del self.current_tracks[interaction.guild.id]
            await interaction.followup.send("👋 Déconnecté du salon vocal")
        else:
            await interaction.response.send_message("❌ Je ne suis pas connecté à un salon vocal", ephemeral=True)

    @music.command(name="play", description="Lire une musique depuis YouTube/Spotify/etc")
    async def play(self, interaction: discord.Interaction, query: str):
        """Joue une musique depuis YouTube/Spotify/etc."""
        await interaction.response.defer()

        # Vérifier si l'utilisateur est dans un salon vocal
        if not interaction.user.voice:
            await interaction.followup.send("❌ Tu dois être dans un salon vocal !", ephemeral=True)
            return

        # Rejoindre le salon si nécessaire
        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            await self.join(interaction)

        # Extraire les informations de la piste
        try:
            player = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
            player.requester = interaction.user.mention
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur lors de la recherche: {str(e)}", ephemeral=True)
            return

        queue = self.get_queue(interaction.guild.id)

        # Si rien ne joue actuellement, commencer la lecture
        vc = interaction.guild.voice_client
        if not vc.is_playing() and not vc.is_paused():
            self.current_tracks[interaction.guild.id] = player
            await self.play_next(interaction.guild)
            await interaction.followup.send(f"🎵 Lecture de **{player.title}**")
        else:
            # Ajouter à la file
            queue.append(player)
            position = len(queue)
            await interaction.followup.send(f"✅ **{player.title}** ajouté à la file (position {position})")

    @music.command(name="pause", description="Mettre la musique en pause")
    async def pause(self, interaction: discord.Interaction):
        """Met en pause la musique."""
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Musique mise en pause")
        else:
            await interaction.response.send_message("❌ Aucune musique en cours", ephemeral=True)

    @music.command(name="resume", description="Reprendre la musique")
    async def resume(self, interaction: discord.Interaction):
        """Reprend la musique."""
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Musique reprise")
        else:
            await interaction.response.send_message("❌ Aucune musique en pause", ephemeral=True)

    @music.command(name="stop", description="Arrêter la musique et vider la file")
    async def stop(self, interaction: discord.Interaction):
        """Arrête la musique et vide la file."""
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            self.get_queue(interaction.guild.id).clear()
            if interaction.guild.id in self.current_tracks:
                del self.current_tracks[interaction.guild.id]
            await interaction.response.send_message("⏹️ Musique arrêtée et file vidée")
        else:
            await interaction.response.send_message("❌ Pas connecté à un salon vocal", ephemeral=True)

    @music.command(name="skip", description="Passer à la musique suivante")
    async def skip(self, interaction: discord.Interaction):
        """Passe à la musique suivante."""
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ Musique passée")
        else:
            await interaction.response.send_message("❌ Aucune musique en cours", ephemeral=True)

    @music.command(name="nowplaying", description="Voir la musique en cours")
    async def nowplaying(self, interaction: discord.Interaction):
        """Affiche la musique en cours."""
        if interaction.guild.id not in self.current_tracks:
            await interaction.response.send_message("❌ Aucune musique en cours", ephemeral=True)
            return

        track = self.current_tracks[interaction.guild.id]
        vc = interaction.guild.voice_client

        embed = discord.Embed(
            title="🎵 Lecture en cours",
            description=f"**{track.title}**\nPar {track.uploader}",
            color=discord.Color.blue()
        )

        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)

        embed.add_field(name="Durée", value=self.format_duration(track.duration), inline=True)
        embed.add_field(name="Demandé par", value=getattr(track, 'requester', 'Inconnu'), inline=True)

        # Informations de progression
        if vc and vc.is_playing():
            embed.add_field(name="Statut", value="▶️ En cours", inline=True)
        elif vc and vc.is_paused():
            embed.add_field(name="Statut", value="⏸️ En pause", inline=True)
        else:
            embed.add_field(name="Statut", value="⏹️ Arrêté", inline=True)

        # Mode boucle
        loop_mode = self.loop_modes.get(interaction.guild.id, 'none')
        loop_emoji = {'none': '➡️', 'track': '🔂', 'queue': '🔁'}
        embed.add_field(name="Boucle", value=f"{loop_emoji[loop_mode]} {loop_mode.title()}", inline=True)

        # Volume
        volume = self.volumes.get(interaction.guild.id, 50)
        volume_emoji = "🔊" if volume > 50 else "🔉" if volume > 0 else "🔇"
        embed.add_field(name="Volume", value=f"{volume_emoji} {volume}%", inline=True)

        await interaction.response.send_message(embed=embed)

    @music.command(name="queue", description="Voir la file d'attente")
    async def queue(self, interaction: discord.Interaction):
        """Affiche la file d'attente."""
        queue = self.get_queue(interaction.guild.id)
        if not queue and interaction.guild.id not in self.current_tracks:
            await interaction.response.send_message("❌ File vide", ephemeral=True)
            return

        embed = discord.Embed(title="📜 File d'attente", color=discord.Color.green())

        # Musique actuelle
        if interaction.guild.id in self.current_tracks:
            track = self.current_tracks[interaction.guild.id]
            embed.add_field(
                name="🎵 En cours",
                value=f"**{track.title}** - {track.uploader}",
                inline=False
            )

        # File d'attente
        if queue:
            queue_list = []
            for i, track in enumerate(list(queue)[:10]):  # Max 10 éléments
                queue_list.append(f"{i+1}. **{track.title}** - {track.uploader}")
            embed.add_field(
                name=f"📋 Suivant ({len(queue)})",
                value="\n".join(queue_list),
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @music.command(name="remove", description="Retirer une musique de la file")
    async def remove(self, interaction: discord.Interaction, position: int):
        """Retire une musique de la file."""
        queue = self.get_queue(interaction.guild.id)
        if 1 <= position <= len(queue):
            removed_track = queue[position - 1]
            del queue[position - 1]
            await interaction.response.send_message(f"✅ Retiré **{removed_track.title}** de la file")
        else:
            await interaction.response.send_message("❌ Position invalide", ephemeral=True)

    @music.command(name="clear", description="Vider toute la file")
    async def clear(self, interaction: discord.Interaction):
        """Vide toute la file d'attente."""
        queue = self.get_queue(interaction.guild.id)
        queue.clear()
        await interaction.response.send_message("🗑️ File d'attente vidée")

    @music.command(name="volume", description="Modifier le volume (0-100%)")
    async def volume(self, interaction: discord.Interaction, level: int):
        """Change le volume (0-100)."""
        if not 0 <= level <= 100:
            await interaction.response.send_message("❌ Le volume doit être entre 0 et 100", ephemeral=True)
            return

        self.volumes[interaction.guild.id] = level
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = level / 100

        await interaction.response.send_message(f"🔊 Volume réglé à {level}%")

    @music.command(name="loop", description="Boucler la musique ou la file")
    async def loop(self, interaction: discord.Interaction, mode: str):
        """Active/désactive la boucle. Modes: none, track, queue"""
        if mode not in ['none', 'track', 'queue']:
            await interaction.response.send_message("❌ Modes valides: none, track, queue", ephemeral=True)
            return

        self.loop_modes[interaction.guild.id] = mode
        await interaction.response.send_message(f"🔁 Mode boucle: {mode}")

    @music.command(name="seek", description="Avancer ou reculer dans la musique")
    async def seek(self, interaction: discord.Interaction, seconds: int):
        """Avance ou recule dans la musique (en secondes)."""
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message("❌ Aucune musique en cours", ephemeral=True)
            return

        if interaction.guild.id not in self.current_tracks:
            await interaction.response.send_message("❌ Aucune musique en cours", ephemeral=True)
            return

        track = self.current_tracks[interaction.guild.id]
        if seconds < 0 or seconds > track.duration:
            await interaction.response.send_message(f"❌ La position doit être entre 0 et {track.duration} secondes", ephemeral=True)
            return

        # Arrêter la musique actuelle et recommencer avec seek
        vc.stop()

        # Créer une nouvelle source avec seek
        try:
            ffmpeg_options_seek = {
                'options': f'-vn -ss {seconds}',
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
            }
            new_source = discord.FFmpegPCMAudio(track.data['url'], **ffmpeg_options_seek)
            new_source.volume = self.volumes.get(interaction.guild.id, 50) / 100

            def after_seek(error):
                if error:
                    print(f'Seek error: {error}')
                asyncio.run_coroutine_threadsafe(self.play_next(interaction.guild), self.bot.loop)

            vc.play(new_source, after=after_seek)
            await interaction.response.send_message(f"⏩ Seek à {self.format_duration(seconds)}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur lors du seek: {str(e)}", ephemeral=True)

    @music.command(name="shuffle", description="Mélanger la file")
    async def shuffle(self, interaction: discord.Interaction):
        """Mélange la file d'attente."""
        queue = self.get_queue(interaction.guild.id)
        if len(queue) > 1:
            queue_list = list(queue)
            random.shuffle(queue_list)
            self.queues[interaction.guild.id] = deque(queue_list)
            await interaction.response.send_message("🔀 File mélangée")
        else:
            await interaction.response.send_message("❌ Pas assez de musiques dans la file", ephemeral=True)

    @music.command(name="lyrics", description="Afficher les paroles de la musique")
    async def lyrics(self, interaction: discord.Interaction):
        """Affiche les paroles de la musique en cours."""
        if interaction.guild.id not in self.current_tracks:
            await interaction.response.send_message("❌ Aucune musique en cours", ephemeral=True)
            return

        track = self.current_tracks[interaction.guild.id]

        # Extraire artiste et titre
        title = track.title
        uploader = track.uploader

        # Nettoyer le titre pour la recherche
        if ' - ' in title:
            parts = title.split(' - ', 1)
            artist = parts[0].strip()
            song_title = parts[1].strip()
        else:
            artist = uploader
            song_title = title

        await interaction.response.defer()

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"https://api.lyrics.ovh/v1/{artist}/{song_title}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        lyrics = data.get('lyrics', 'Paroles non trouvées')

                        # Limiter la longueur pour Discord
                        if len(lyrics) > 4000:
                            lyrics = lyrics[:4000] + "..."

                        embed = discord.Embed(
                            title=f"🎤 Paroles - {title}",
                            description=lyrics,
                            color=discord.Color.purple()
                        )
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("❌ Paroles non trouvées pour cette musique", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur lors de la recherche des paroles: {str(e)}", ephemeral=True)

    @music.command(name="filters", description="Activer des effets audio")
    async def filters(self, interaction: discord.Interaction, filter_name: str):
        """Active un effet audio."""
        available_filters = ['bassboost', 'nightcore', 'vaporwave', '8d', 'karaoke', 'treble', 'speed', 'slow']
        if filter_name not in available_filters:
            await interaction.response.send_message(f"❌ Filtres disponibles: {', '.join(available_filters)}", ephemeral=True)
            return

        await interaction.response.send_message(f"🎛️ Filtre {filter_name} non implémenté (nécessite ffmpeg avancé)")

    # Sous-groupe pour les playlists
    playlist_group = app_commands.Group(name="playlist", description="Gestion des playlists", parent=music)

    @playlist_group.command(name="add", description="Ajouter une playlist YouTube/Spotify")
    async def playlist_add(self, interaction: discord.Interaction, name: str, url: str):
        """Ajoute une playlist."""
        await interaction.response.defer()

        try:
            # Extraire les informations de la playlist
            data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

            if 'entries' not in data:
                await interaction.followup.send("❌ URL invalide ou playlist vide", ephemeral=True)
                return

            tracks = []
            for entry in data['entries'][:50]:  # Limiter à 50 pistes
                if entry:
                    track_data = {
                        'title': entry.get('title', 'Titre inconnu'),
                        'url': entry.get('webpage_url', ''),
                        'duration': entry.get('duration', 0),
                        'thumbnail': entry.get('thumbnail', ''),
                        'uploader': entry.get('uploader', 'Inconnu')
                    }
                    tracks.append(track_data)

            playlists = self.get_playlists(interaction.guild.id)
            playlists[name] = tracks

            await interaction.followup.send(f"✅ Playlist **{name}** ajoutée avec {len(tracks)} pistes")
            
            # Sauvegarder les playlists
            self.save_playlists()

        except Exception as e:
            await interaction.followup.send(f"❌ Erreur lors de l'ajout de la playlist: {str(e)}", ephemeral=True)

    @playlist_group.command(name="play", description="Lire une playlist")
    async def playlist_play(self, interaction: discord.Interaction, name: str):
        """Joue une playlist."""
        playlists = self.get_playlists(interaction.guild.id)

        if name not in playlists:
            await interaction.followup.send("❌ Playlist non trouvée", ephemeral=True)
            return

        if not interaction.user.voice:
            await interaction.followup.send("❌ Tu dois être dans un salon vocal !", ephemeral=True)
            return

        await interaction.response.defer()

        # Rejoindre le salon si nécessaire
        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            try:
                await self.join_via_interaction(interaction)
                vc = interaction.guild.voice_client
            except Exception as e:
                await interaction.followup.send(f"❌ Impossible de rejoindre le salon vocal: {str(e)}", ephemeral=True)
                return

        queue = self.get_queue(interaction.guild.id)
        tracks_added = 0

        for track_data in playlists[name]:
            try:
                player = YTDLSource(
                    discord.FFmpegPCMAudio(track_data['url'], **ffmpeg_options),
                    data=track_data
                )
                player.requester = interaction.user.mention
                queue.append(player)
                tracks_added += 1
            except:
                continue  # Ignorer les pistes qui ne marchent pas

        if tracks_added > 0:
            # Démarrer la lecture si rien ne joue
            vc = interaction.guild.voice_client
            if not vc.is_playing() and not vc.is_paused():
                await self.play_next(interaction.guild)

            await interaction.followup.send(f"✅ Ajouté {tracks_added} pistes de la playlist **{name}** à la file")
        else:
            await interaction.followup.send("❌ Aucune piste valide trouvée dans la playlist", ephemeral=True)

    @playlist_group.command(name="remove", description="Supprimer une playlist")
    async def playlist_remove(self, interaction: discord.Interaction, name: str):
        """Supprime une playlist."""
        playlists = self.get_playlists(interaction.guild.id)

        if name not in playlists:
            await interaction.followup.send("❌ Playlist non trouvée", ephemeral=True)
            return

        del playlists[name]
        await interaction.response.send_message(f"✅ Playlist **{name}** supprimée")
        
        # Sauvegarder les playlists
        self.save_playlists()

    @playlist_group.command(name="list", description="Voir les playlists enregistrées")
    async def playlist_list(self, interaction: discord.Interaction):
        """Liste les playlists."""
        playlists = self.get_playlists(interaction.guild.id)

        if not playlists:
            await interaction.response.send_message("❌ Aucune playlist enregistrée", ephemeral=True)
            return

        embed = discord.Embed(
            title="📝 Playlists enregistrées",
            color=discord.Color.green()
        )

        for name, tracks in playlists.items():
            embed.add_field(
                name=name,
                value=f"{len(tracks)} pistes",
                inline=True
            )

        await interaction.response.send_message(embed=embed)

    async def join_via_interaction(self, interaction: discord.Interaction):
        """Méthode helper pour rejoindre via interaction."""
        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client

        if vc and vc.is_connected():
            await vc.move_to(channel)
        else:
            await channel.connect()

    @music.command(name="status", description="Voir le statut détaillé du bot musique")
    async def status(self, interaction: discord.Interaction):
        """Affiche le statut détaillé du bot musique."""
        embed = discord.Embed(
            title="🎵 Statut du Bot Musique",
            color=discord.Color.blue()
        )

        # Informations générales
        embed.add_field(
            name="🤖 Bot",
            value=f"Connecté: {len(self.bot.guilds)} serveurs\nLatence: {round(self.bot.latency * 1000)}ms",
            inline=True
        )

        # Informations vocales
        vc = interaction.guild.voice_client
        if vc and vc.is_connected():
            members = len([m for m in vc.channel.members if not m.bot])
            embed.add_field(
                name="🎤 Salon Vocal",
                value=f"Connecté à {vc.channel.name}\n{members} membres humains",
                inline=True
            )
        else:
            embed.add_field(
                name="🎤 Salon Vocal",
                value="Non connecté",
                inline=True
            )

        # Informations musique
        queue = self.get_queue(interaction.guild.id)
        current = self.current_tracks.get(interaction.guild.id)
        loop_mode = self.loop_modes.get(interaction.guild.id, 'none')
        volume = self.volumes.get(interaction.guild.id, 50)

        music_info = f"File: {len(queue)} pistes\n"
        music_info += f"Boucle: {loop_mode}\n"
        music_info += f"Volume: {volume}%"

        if current:
            music_info += f"\nEn cours: {current.title}"

        embed.add_field(
            name="🎵 Musique",
            value=music_info,
            inline=False
        )

        # Playlists
        playlists = self.get_playlists(interaction.guild.id)
        if playlists:
            playlist_info = f"{len(playlists)} playlists\n"
            total_tracks = sum(len(tracks) for tracks in playlists.values())
            playlist_info += f"{total_tracks} pistes totales"
        else:
            playlist_info = "Aucune playlist"

        embed.add_field(
            name="📝 Playlists",
            value=playlist_info,
            inline=True
        )

        await interaction.response.send_message(embed=embed)

    @music.command(name="fix", description="Réparer une connexion vocale bloquée")
    async def fix(self, interaction: discord.Interaction):
        """Répare une connexion vocale bloquée."""
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await asyncio.sleep(1)
            
            if interaction.user.voice:
                channel = interaction.user.voice.channel
                vc = await channel.connect()
                await interaction.response.send_message("🔧 Connexion réparée")
            else:
                await interaction.response.send_message("❌ Rejoins un salon vocal d'abord", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Pas connecté à un salon vocal", ephemeral=True)
        embed = discord.Embed(
            title="🎵 Aide - Commandes Musique",
            description="Liste complète des commandes musique disponibles",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="🎧 Commandes de base",
            value="`/music play` - Lire une musique\n`/music pause` - Mettre en pause\n`/music resume` - Reprendre\n`/music stop` - Arrêter\n`/music skip` - Passer\n`/music nowplaying` - Musique en cours\n`/music queue` - File d'attente\n`/music remove` - Retirer de la file\n`/music clear` - Vider la file",
            inline=False
        )

        embed.add_field(
            name="🔊 Commandes avancées",
            value="`/music volume` - Modifier le volume\n`/music loop` - Boucler\n`/music seek` - Avancer/reculer\n`/music shuffle` - Mélanger\n`/music lyrics` - Paroles\n`/music filters` - Effets audio",
            inline=False
        )

        embed.add_field(
            name="🛠️ Utilitaires",
            value="`/music join` - Rejoindre vocal\n`/music leave` - Quitter vocal\n`/music ping` - Latence\n`/music status` - Statut détaillé\n`/music fix` - Réparer connexion\n`/music help` - Cette aide",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def keep_alive(self, vc):
        """Joue un silence pour éviter que Discord déconnecte le bot."""
        if vc and vc.is_connected() and not vc.is_playing() and not vc.is_paused():
            vc.play(discord.FFmpegPCMAudio("anull", pipe=False, executable="ffmpeg",
                before_options="-f lavfi -i anullsrc=r=48000:cl=stereo",
                options="-t 0.1 -vn"))

    async def on_voice_state_update(self, member, before, after):
        """Gère les changements d'état vocal."""
        if member == self.bot.user:
            # Le bot a changé de salon vocal
            if before.channel and not after.channel:
                # Le bot a quitté un salon vocal - NE PAS vider la file
                pass
            elif after.channel and not before.channel:
                # Le bot a rejoint un salon vocal
                pass
            return

        # Si un utilisateur rejoint un salon vocal et que le bot a une file en attente,
        # on peut reconnecter et relancer la lecture automatiquement.
        if not self.auto_reconnect:
            return

        # L'utilisateur vient de rejoindre un salon vocal
        if after.channel and not before.channel:
            guild = member.guild
            vc = guild.voice_client
            if vc and vc.is_connected():
                return

            queue = self.get_queue(guild.id)
            # S'il y a des pistes en attente, le bot rejoint et commence à jouer
            if queue:
                try:
                    vc = await member.voice.channel.connect()
                    if not vc.is_playing() and not vc.is_paused():
                        await self.play_next(guild)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Nettoie les données quand le bot quitte une guilde."""
        guild_id = guild.id
        if guild_id in self.queues:
            del self.queues[guild_id]
        if guild_id in self.current_tracks:
            del self.current_tracks[guild_id]
        if guild_id in self.loop_modes:
            del self.loop_modes[guild_id]
        if guild_id in self.volumes:
            del self.volumes[guild_id]
        if guild_id in self.playlists:
            del self.playlists[guild_id]