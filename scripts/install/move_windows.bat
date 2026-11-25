@echo off
rem FLOKTRON - move and backup on Windows (double-click). One archive with the whole setup, password-protected (docs\MOVE.md).
cd /d "%~dp0\..\.."
where python >nul 2>nul || (echo Python not found - install it from python.org, tick "Add to PATH" & pause & exit /b 1)
python -c "import openpyxl, yaml, pyzipper, tzdata" 2>nul || python -m pip install --user -q openpyxl pyyaml pyzipper tzdata
echo FLOKTRON in: %CD%
echo   1  Pack everything for a move (to another computer or AI assistant)
echo   2  Unpack a move archive here
echo   3  Check an archive
echo   4  Backup now
echo   5  Pack for a new manager (handover: without people's contacts)
set /p ans=Choose 1-5: 
if "%ans%"=="1" goto pack
if "%ans%"=="2" goto unpack
if "%ans%"=="3" goto check
if "%ans%"=="4" goto backup
if "%ans%"=="5" goto handover
echo Nothing done.
goto end
:pack
python scripts\move.py pack
goto end
:handover
python scripts\move.py pack --profile handover
goto end
:backup
python scripts\move.py backup
goto end
:unpack
set /p f=Drag the archive file here and press Enter: 
python scripts\move.py unpack %f%
goto end
:check
set /p f=Drag the archive file here and press Enter: 
python scripts\move.py check %f%
:end
pause
