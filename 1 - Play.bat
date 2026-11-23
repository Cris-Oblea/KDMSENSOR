@echo off
rem ===================================================================
rem  DanceEvolution Arcade - the launcher
rem
rem  One small window: every mod (each explained; choosing one switches
rem  on what it needs), the controls (spice2x: bind your buttons before
rem  the first game, the cabinet has no keyboard) and Play. Your last
rem  choice is saved. Every option on its first value = Konami's game.
rem
rem  The game's own files are NEVER changed: the chosen mods are built
rem  into mods\active from Konami's originals and loaded from there.
rem ===================================================================
cd /d "%~dp0"
if not exist "%~dp0mods\play_mods.ps1" (
  echo [ERROR] mods\ is missing from this folder.
  pause
  exit /b 1
)
rem  Windows PowerShell by its full path: a PATH another program rewrote must not stop the launcher.
start "" "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0mods\play_mods.ps1"
