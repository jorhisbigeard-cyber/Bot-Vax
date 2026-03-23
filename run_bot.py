"""Run the bot in a restart loop.

This script restarts the bot if it crashes unexpectedly, which can help keep it
alive longer on a machine where it can run continuously.

For true 24/7 uptime, host the bot on a server / VPS and run this script under a
supervisor (systemd, PM2, NSSM, etc.).
"""

import os
import time
import traceback
from pathlib import Path

# Ensure we are running from the project root so imports work correctly.
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

from bot import main as bot_main


def main():
    while True:
        try:
            bot_main()
        except Exception:
            print("Bot crashed, restarting in 5 seconds...")
            traceback.print_exc()
            time.sleep(5)
        else:
            # If bot_main returns normally, exit.
            break


if __name__ == "__main__":
    main()
