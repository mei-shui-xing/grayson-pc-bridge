@echo off
chcp 65001 >nul
title AI电脑助手 - 启动
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1"
echo.
pause
