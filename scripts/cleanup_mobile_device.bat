@echo off
set ADB_PATH=C:\Users\yegir\AppData\Local\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools\adb.exe
if not exist "%ADB_PATH%" (
    where adb >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set ADB_PATH=adb
    ) else (
        echo [ERROR] adb.exe not found. Nothing to clean up.
        exit /b 1
    )
)

echo =========================================================
echo  ATLAS Mobile Teardown & Device Cleanup
echo =========================================================

echo [1/4] Removing ADB port forwarding rules...
"%ADB_PATH%" forward --remove tcp:8088 >nul 2>&1
"%ADB_PATH%" forward --remove-all >nul 2>&1
echo       Port forwards removed.

echo [2/4] Revoking Termux storage permissions on Android...
"%ADB_PATH%" shell pm revoke com.termux android.permission.READ_EXTERNAL_STORAGE >nul 2>&1
"%ADB_PATH%" shell pm revoke com.termux android.permission.WRITE_EXTERNAL_STORAGE >nul 2>&1
echo       Termux permissions reverted to original default.

echo [3/4] Deleting temporary bridge files from Android device...
"%ADB_PATH%" shell rm -f /data/local/tmp/termux_bridge.py >nul 2>&1
"%ADB_PATH%" shell rm -f /sdcard/termux_bridge.py >nul 2>&1
echo       Temporary bridge files deleted.

echo [4/4] Stopping host ADB background daemon...
"%ADB_PATH%" kill-server >nul 2>&1
echo       ADB daemon stopped.

echo.
echo =========================================================
echo  Cleanup Complete! 
echo  On your phone: You can now unplug USB and turn OFF 
echo  'USB Debugging' under Developer Options in Settings.
echo =========================================================
