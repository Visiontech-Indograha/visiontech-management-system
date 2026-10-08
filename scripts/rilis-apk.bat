@echo off
rem Pembungkus Windows untuk scripts/rilis-apk.sh (Git Bash). Contoh:
rem   scripts\rilis-apk.bat bangun --catatan "Pembaruan otomatis"
rem   scripts\rilis-apk.bat kirim
set "GITBASH=C:\Program Files\Git\bin\bash.exe"
if not exist "%GITBASH%" (
  echo Git Bash tidak ditemukan di "%GITBASH%".
  exit /b 1
)
"%GITBASH%" "%~dp0rilis-apk.sh" %*
