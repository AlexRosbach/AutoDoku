@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  AutoDoku -- Build-Skript
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python wurde nicht gefunden.
    echo Bitte Python 3.11+ installieren: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Create / reuse virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo [1/4] Erstelle virtuelle Umgebung (.venv^)...
    python -m venv .venv
    if errorlevel 1 (echo FEHLER beim Erstellen der venv. & pause & exit /b 1)
) else (
    echo [1/4] Virtuelle Umgebung bereits vorhanden, wird wiederverwendet.
)

call .venv\Scripts\activate.bat

echo [2/4] Installiere / aktualisiere Abhaengigkeiten...
pip install --upgrade pip -q
pip install -r requirements.txt -q
if errorlevel 1 (echo FEHLER beim Installieren der Pakete. & pause & exit /b 1)

echo [3/4] Erstelle EXE mit PyInstaller...
pyinstaller autodoku.spec --clean --noconfirm
if errorlevel 1 (echo FEHLER beim Bauen der EXE. & pause & exit /b 1)

echo [4/4] Pruefe Ergebnis...
if exist "dist\AutoDoku.exe" (
    echo.
    echo ============================================================
    echo  BUILD ERFOLGREICH
    echo  Ausgabe: dist\AutoDoku.exe
    echo  Die EXE laeuft ohne vorherige Installation (portabel).
    echo ============================================================
) else (
    echo.
    echo FEHLER: dist\AutoDoku.exe wurde nicht erstellt.
    pause
    exit /b 1
)

pause
