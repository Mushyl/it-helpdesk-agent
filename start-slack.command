#!/usr/bin/env bash
# ============================================================
#  IT Help Desk - Slack Bot launcher (macOS / Linux)
#  First time: chmod +x start-slack.command
# ============================================================
set -e
cd "$(dirname "$0")"

if [ ! -f "venv/bin/activate" ]; then
    echo "[ERRORE] Virtual environment non trovato nella cartella 'venv/'."
    echo "Crea l'ambiente:  python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    read -n 1 -s -r -p "Premi un tasto per chiudere..."
    exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate

if ! python -c "import slack_bolt" >/dev/null 2>&1; then
    echo "[ERRORE] slack-bolt non installato. Esegui: pip install -r requirements.txt"
    read -n 1 -s -r -p "Premi un tasto per chiudere..."
    exit 1
fi

if [ ! -f "key.env" ]; then
    echo "[ATTENZIONE] key.env non trovato: servono SLACK_BOT_TOKEN e SLACK_APP_TOKEN."
fi

echo ""
echo "Avvio del bot Slack (Socket Mode). Premi Ctrl+C per fermare."
echo ""
python src/slack_bot.py
