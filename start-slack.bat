@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo  IT Help Desk -- Slack Bot
echo ============================================================
echo.

if not exist "venv\Scripts\activate.bat" (
    echo [ERRORE] Virtual environment non trovato nella cartella venv\.
    echo Crea l'ambiente e installa le dipendenze:
    echo     python -m venv venv
    echo     venv\Scripts\activate
    echo     pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "venv\Lib\site-packages\slack_bolt" (
    echo [ERRORE] slack-bolt non installato. Esegui:
    echo     venv\Scripts\activate
    echo     pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "key.env" (
    echo [ATTENZIONE] key.env non trovato: servono SLACK_BOT_TOKEN e SLACK_APP_TOKEN.
    echo Copia key.env.example in key.env e inserisci i token.
    echo.
)

echo Attivazione virtual environment...
call "venv\Scripts\activate.bat"

echo Avvio del bot Slack (Socket Mode). Premi Ctrl+C per fermare.
echo.
python "src\slack_bot.py"

echo.
echo Bot fermato.
pause
endlocal
