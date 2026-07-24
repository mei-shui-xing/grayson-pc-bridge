@echo off
chcp 65001 >nul
title Grayson电脑助手 - 状态
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0status.ps1"
echo.
pause
