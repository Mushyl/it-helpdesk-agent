@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo  IT Help Desk Agent -- Avvio in corso...
echo ============================================================
echo.

REM Skip Streamlit's first-run email prompt by pre-creating an empty
REM credentials file in the user's home directory (only if missing).
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    > "%USERPROFILE%\.streamlit\credentials.toml" echo [general]
    >> "%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

if not exist "venv\Scripts\activate.bat" (
    echo [ERRORE] Virtual environment non trovato nella cartella venv\.
    echo.
    echo Per crearlo, esegui una volta sola nella root del progetto:
    echo     python -m venv venv
    echo     venv\Scripts\activate
    echo     pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

if not exist "key.env" (
    echo [ATTENZIONE] File key.env non trovato nella root del progetto.
    echo Il sistema partira' in modalita' degradata.
    echo Per ottenere risposte da Claude, crea key.env con:
    echo     ANTHROPIC_API_KEY=sk-ant-...
    echo.
)

echo Attivazione virtual environment...
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERRORE] Impossibile attivare il virtual environment.
    pause
    exit /b 1
)

echo Avvio del server Streamlit. Il browser si aprira' automaticamente.
echo Per chiudere il server, premi Ctrl+C in questa finestra.
echo.

python -m streamlit run "src\app.py" --browser.gatherUsageStats=false

echo.
echo Server fermato.
pause
endlocal
