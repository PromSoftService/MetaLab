# MetaLab

## Быстрый старт

```bash
# Установка
pip install -r requirements.txt

# Запуск сценария из Excel
python tools/run.py scenarios/scenario.xlsx --url opc.tcp://192.168.1.3:4840

# Запуск готового YAML
python tools/run.py scenarios/scenario.yaml --url opc.tcp://192.168.1.3:4840

# Одной командой
run.bat scenarios/scenario.xlsx opc.tcp://192.168.1.3:4840
