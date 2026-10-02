@echo off
rem Menjalankan emulator Android tanpa membuka Android Studio.
rem Pemakaian: dobel-klik berkas ini, atau  scripts\jalankan-emulator.bat [NAMA_AVD]
rem Tanpa argumen: AVD pertama dari daftar (emulator -list-avds).

setlocal
set "SDK=%ANDROID_HOME%"
if "%SDK%"=="" set "SDK=%LOCALAPPDATA%\Android\Sdk"
set "EMU=%SDK%\emulator\emulator.exe"
set "ADB=%SDK%\platform-tools\adb.exe"

if not exist "%EMU%" (
  echo Emulator tidak ditemukan di "%EMU%". Pasang "Android Emulator" lewat SDK Manager.
  pause
  exit /b 1
)

set "AVD=%~1"
if "%AVD%"=="" for /f "usebackq delims=" %%a in (`"%EMU%" -list-avds`) do if not defined AVD set "AVD=%%a"
if "%AVD%"=="" (
  echo Belum ada AVD. Buat sekali lewat Android Studio ^> Device Manager.
  pause
  exit /b 1
)

echo Menyalakan emulator %AVD% ...
start "Emulator %AVD%" "%EMU%" -avd "%AVD%" -netdelay none -netspeed full

rem Tunggu sampai Android selesai boot agar `flutter run` langsung bisa dipakai.
"%ADB%" wait-for-device
:tunggu
for /f "usebackq delims=" %%b in (`"%ADB%" shell getprop sys.boot_completed 2^>nul`) do set "BOOT=%%b"
if not "%BOOT%"=="1" (
  timeout /t 2 /nobreak >nul
  goto tunggu
)
echo Emulator %AVD% siap.
endlocal
