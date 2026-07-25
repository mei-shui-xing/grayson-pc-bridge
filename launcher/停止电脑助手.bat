@echo off
chcp 65001 >nul
title AI电脑助手 - 停止
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
echo.
pause
