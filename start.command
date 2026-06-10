#!/usr/bin/env bash
# ============================================================
#  IT Help Desk Support Agent - macOS / Linux launcher
#  First time on macOS: run once `chmod +x start.command`
# ============================================================
set -e
cd "$(dirname "$0")"

# Skip Streamlit's first-run email prompt.
mkdir -p "$HOME/.streamlit"
if [ ! -f "$HOME/.streamlit/credentials.toml" ]; then
    printf '[general]\nemail = ""\n' > "$HOME/.streamlit/credentials.toml"
fi

if [ ! -f "venv/bin/activate" ]; then
    echo ""
    echo "[ERRORE] Virtual environment non trovato nella cartella 'venv/'."
    echo "Per crearlo, esegui una volta sola nella root del progetto:"
    echo "    python3 -m venv venv"
    echo "    source venv/bin/activate"
    echo "    pip install -r requirements.txt"
    echo ""
    read -n 1 -s -r -p "Premi un tasto per chiudere..."
    exit 1
fi

if [ ! -f "key.env" ]; then
    echo ""
    echo "[ATTENZIONE] File 'key.env' non trovato: avvio in modalita' degradata."
    echo "Copia key.env.example in key.env e inserisci la tua ANTHROPIC_API_KEY."
    echo ""
fi

# shellcheck disable=SC1091
source venv/bin/activate

if ! python -c "import streamlit" >/dev/null 2>&1; then
    echo "[ERRORE] Streamlit non risulta installato nel virtual environment."
    echo "Esegui:  source venv/bin/activate && pip install -r requirements.txt"
    read -n 1 -s -r -p "Premi un tasto per chiudere..."
    exit 1
fi

echo ""
echo "============================================================"
echo " Avvio del frontend IT Help Desk in corso..."
echo " Per chiudere il server, premi Ctrl+C in questo terminale."
echo "============================================================"
echo ""

python -m streamlit run src/app.py --browser.gatherUsageStats=false
