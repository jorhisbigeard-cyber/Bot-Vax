# MonPremierBot

Bot Discord modulaire en Python (discord.py) avec une architecture conçue pour évoluer vers un bot "all-in-one" (modération, musique, économie, mini-jeux, etc.).

## 🧩 Structure

- `bot.py` — point d'entrée principal.
- `cogs/` — modules (cogs) séparés par fonctionnalités.
- `utils/` — fonctions utilitaires réutilisables.
- `data/` — stockage local (JSON). À remplacer par une base de données pour production.

## 🚀 Installation

1. Crée un environnement virtuel (recommandé) :

```powershell
python -m venv myenv
.
myenv\Scripts\Activate.ps1
```

2. Installe les dépendances :

```powershell
pip install -r requirements.txt
```

3. Configure ton token :

- Soit via variable d'environnement `DISCORD_TOKEN` (recommandé)
- Soit en créant un fichier `.env` (par exemple en copiant `.env.example`) :

```powershell
copy .env.example .env
notepad .env
```

> Ne commite jamais `.env` ni `config.json` contenant un token.

## ⚙️ Config

- `DISCORD_TOKEN` : token du bot (ou variable d'environnement).
- `GUILD_ID` (optionnel) : serveur de développement pour les commandes applicatives.

## ▶️ Lancer

### Option 1 — En local (recommandé)

1) Copie `.env.example` en `.env` :

```powershell
copy .env.example .env
```

2) Modifie `.env` et colle ton token :

```env
DISCORD_TOKEN=TON_TOKEN_ICI
```

3) Lance le bot en mode redémarrage automatique :

```powershell
c:/Users/greg8/Desktop/MonPremierBot/.venv/Scripts/python.exe run_bot.py
```

### Option 2 — Commande directe

```powershell
$env:DISCORD_TOKEN="TON_TOKEN_ICI"; & "c:/Users/greg8/Desktop/MonPremierBot/.venv/Scripts/python.exe" bot.py
```

### Option 3 — Script Windows

Exécute :

```powershell
.\start_bot.ps1
```

---

## 🧭 Concepts

Ce bot utilise les **slash commands (interactions)** et les **cogs** de discord.py pour séparer les responsabilités dans plusieurs fichiers.

Tu peux ajouter des fonctionnalités en créant un nouveau `Cog` dans `cogs/` et en l'ajoutant dans `bot.py`.
