# Start the bot (Windows)
# Usage: .\start_bot.ps1

$env:DISCORD_TOKEN = "YOUR_TOKEN_HERE"

# Optionnel : définir GUILD_ID pour dev
# $env:GUILD_ID = "123456789012345678"

& "${PWD}\.venv\Scripts\python.exe" "${PWD}\run_bot.py"
