@echo off

REM Check if Python and PyInstaller are available
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python and try again.
    exit /b
)

python -m pip show pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo PyInstaller is not installed. Installing PyInstaller...
    python -m pip install pyinstaller
)

REM Clean up previous builds
echo Cleaning up previous builds...
rd /s /q build >nul 2>nul
rd /s /q dist >nul 2>nul
del /f /q notifyme.spec >nul 2>nul

REM Create the .exe using PyInstaller
echo Creating the executable...
pyinstaller --onefile --windowed notifyme.py

if exist "dist\notifyme.exe" (
    echo Executable created successfully.
) else (
    echo Failed to create the executable.
    exit /b
)

REM Create a shortcut in the Windows startup folder
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "EXE_PATH=%~dp0dist\notifyme.exe"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\NotifyMe.lnk"

echo Creating a shortcut in the startup folder...
powershell -Command ^
    "$WshShell = New-Object -ComObject WScript.Shell; ^
    $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); ^
    $Shortcut.TargetPath = '%EXE_PATH%'; ^
    $Shortcut.WorkingDirectory = '%~dp0'; ^
    $Shortcut.Save()"

if exist "%SHORTCUT_PATH%" (
    echo Shortcut created successfully in the startup folder.
) else (
    echo Failed to create the shortcut.
    exit /b
)

echo All done! NotifyMe will start automatically on system startup.
pause
