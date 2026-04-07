@echo off
chcp 65001 > nul  # Устанавливаем UTF-8 кодировку
set EXCEL_FILE=%1
set OPC_URL=%2

if "%EXCEL_FILE%"=="" (
    echo ❌ Укажите имя Excel файла
    echo Использование: run.bat scenario.xlsx [opc.tcp://192.168.1.3:4840]
    pause
    exit /b
)

if "%OPC_URL%"=="" (
    set OPC_URL=opc.tcp://192.168.1.3:4840
)

echo 🚀 Запуск сценария из %EXCEL_FILE% с URL %OPC_URL%...
python tools/run.py %EXCEL_FILE% --url %OPC_URL% --keep-yaml

pause