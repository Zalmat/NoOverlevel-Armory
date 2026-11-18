@echo off
chcp 65001 >nul
title WoW Forever Armory Server
cd /d "%~dp0"

echo [1/3] Проверка Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo =========================================================
    echo ОШИБКА: Python не найден!
    echo Пожалуйста, установите Python с https://www.python.org/downloads/
    echo ВАЖНО: При установке поставьте галочку "Add Python to PATH".
    echo =========================================================
    echo.
    goto :END
)

echo [2/3] Проверка файлов...
if not exist "server-v8.py" (
    echo ОШИБКА: Файл server-v8.py не найден в папке!
    goto :END
)

echo [3/3] Запуск сервера...
python server-v8.py
echo.
echo =========================================================
echo СЕРВЕР ОСТАНОВЛЕН (или произошла ошибка).
echo Если вы видите это сообщение сразу после запуска, 
echo проверьте текст выше на наличие красных ошибок Python.
echo =========================================================

:END
echo.
echo Нажмите любую клавишу, чтобы закрыть это окно...
pause >nul