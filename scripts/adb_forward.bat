@echo off
set ADB_PATH=C:\Users\yegir\AppData\Local\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools\adb.exe
if not exist "%ADB_PATH%" (
    where adb >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set ADB_PATH=adb
    ) else (
        echo [ERROR] adb.exe not found!
        exit /b 1
    )
)

echo [ATLAS] Checking ADB devices...
"%ADB_PATH%" devices

echo.
echo [ATLAS] Forwarding port 8088 (Termux bridge)...
"%ADB_PATH%" forward tcp:8088 tcp:8088
if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Port forward established: http://127.0.0.1:8088 -^> Android:8088
) else (
    echo [ERROR] Port forward failed. Ensure phone is connected with USB Debugging enabled.
)
