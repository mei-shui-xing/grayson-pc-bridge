@echo off
chcp 65001 >nul
title Grayson电脑助手 - 安装或修复
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0repair.ps1"
echo.
pause
