#!/usr/bin/env python3
# tools/run.py
# -----------------------------------------------------------------------------
# УНИВЕРСАЛЬНЫЙ ЗАПУСКАЛЬЩИК СЦЕНАРИЕВ
# -----------------------------------------------------------------------------
# Использование:
#   python run.py scenario.xlsx --url opc.tcp://192.168.1.3:4840
#   python run.py scenario.yaml --url opc.tcp://192.168.1.3:4840
#   python run.py --config config.yaml --scenario scenario.yaml --url ...
#   python run.py --log-mode 2 --log-file test.log ... (лог только в файл)
# -----------------------------------------------------------------------------

import os
import sys
import argparse
import tempfile
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.engine import ScenarioEngine
from core.core_runtime import Context, Runtime
from core.opcua_client import OpcUaClient
from core.constants import *

# Импортируем конвертер
from tools.excel2yaml import excel_to_yaml


def main():
    parser = argparse.ArgumentParser(description='Запуск сценария симуляции PLC')
    parser.add_argument('input', nargs='?', help='Excel или YAML файл со сценарием')
    parser.add_argument('--config', help='YAML файл конфигурации (теги и сигналы)')
    parser.add_argument('--scenario', help='YAML файл сценария')
    parser.add_argument('--url', required=True, help='OPC UA URL')
    parser.add_argument('--dt', type=float, default=RT_DEFAULT_DT, help='Шаг дискретизации (сек)')
    parser.add_argument('--keep-yaml', action='store_true', help='Сохранить YAML файлы в папку scenarios')
    
    # Параметры логирования
    parser.add_argument('--log-mode', type=int, default=LOG_MODE_DEFAULT,
                       choices=[LOG_MODE_CONSOLE, LOG_MODE_FILE, LOG_MODE_BOTH],
                       help='Режим логирования: 1-консоль, 2-файл, 3-оба')
    parser.add_argument('--log-file', help='Имя файла для лога (в папке logs/)')
    
    args = parser.parse_args()
    
    config_file = None
    scenario_file = None
    
    # Определяем режим работы
    if args.config and args.scenario:
        # Режим 2: раздельная конфигурация и сценарий
        config_file = args.config
        scenario_file = args.scenario
    elif args.input:
        if args.input.lower().endswith(YAML_EXTENSIONS):
            # Режим 3: готовый YAML
            scenario_file = args.input
            # Ищем config.yaml рядом
            config_file = str(Path(args.input).parent / f"config{CONFIG_FILE_SUFFIX}")
            if not os.path.exists(config_file):
                config_file = None
                print(INFO_NO_CONFIG)
        elif args.input.lower().endswith(EXCEL_EXTENSIONS):
            # Режим 1: Excel -> конвертация + запуск
            print(INFO_EXCEL_CONVERT.format(args.input))
            base = Path(args.input).stem
            
            if args.keep_yaml:
                # Сохраняем в папку scenarios
                scenarios_dir = os.path.join(Path(__file__).parent.parent, SCENARIOS_DIR)
                os.makedirs(scenarios_dir, exist_ok=True)
                config_file = os.path.join(scenarios_dir, f"{base}{CONFIG_FILE_SUFFIX}")
                scenario_file = os.path.join(scenarios_dir, f"{base}{SCENARIO_FILE_SUFFIX}")
                print(INFO_YAML_SAVED.format(scenarios_dir))
            else:
                # Временная папка
                temp_dir = tempfile.mkdtemp(prefix=TEMP_DIR_PREFIX)
                config_file = os.path.join(temp_dir, f"{base}{CONFIG_FILE_SUFFIX}")
                scenario_file = os.path.join(temp_dir, f"{base}{SCENARIO_FILE_SUFFIX}")
                print(INFO_YAML_TEMP.format(temp_dir))
            
            excel_to_yaml(args.input, config_file, scenario_file)
        else:
            parser.error(ERROR_INVALID_FORMAT)
    else:
        parser.error(ERROR_NO_INPUT)
    
    # Проверяем существование файлов
    if config_file and not os.path.exists(config_file):
        print(ERROR_CONFIG_NOT_FOUND.format(config_file))
        sys.exit(1)
    
    if not os.path.exists(scenario_file):
        print(ERROR_SCENARIO_NOT_FOUND.format(scenario_file))
        sys.exit(1)
    
    # Запускаем сценарий
    print(f"\n🚀 Запуск сценария...")
    print(INFO_RUN_URL.format(args.url))
    if config_file:
        print(INFO_RUN_CONFIG.format(config_file))
    print(INFO_RUN_SCENARIO.format(scenario_file))
    
    # Информация о логе
    log_mode_str = {1: "консоль", 2: "файл", 3: "консоль+файл"}.get(args.log_mode, "неизвестно")
    print(f"   Лог: {log_mode_str}")
    
    # Получаем имя сценария из файла
    scenario_name = Path(scenario_file).stem
    if scenario_name.endswith("_scenario"):
        scenario_name = scenario_name[:-9]  # убираем "_scenario"
    
    ctx = Context()
    opc = OpcUaClient(args.url, {}, {})  # временные словари, будут заполнены в engine
    rt = Runtime(ctx, opc, dt=args.dt)
    
    engine = ScenarioEngine(
        ctx, rt, 
        scenario_name=scenario_name,
        log_mode=args.log_mode, 
        log_file=args.log_file
    )
    
    # Загружаем конфигурацию
    if config_file:
        tags_out, tags_in = engine.load_config(config_file)
        # Обновляем словари в OPC клиенте
        opc.inputs_to_write = {name: info[TAG_NODE_ID] for name, info in tags_out.items()}
        opc.outputs_to_read = {name: info[TAG_NODE_ID] for name, info in tags_in.items()}
        opc.input_types = {name: info[TAG_DATA_TYPE] for name, info in tags_out.items()}
        opc.output_types = {name: info[TAG_DATA_TYPE] for name, info in tags_in.items()}
    
    # Загружаем сценарий
    engine.load_scenario(scenario_file)
    
    # Запускаем
    try:
        rt.start()
        engine.run()
    except KeyboardInterrupt:
        print(INFO_USER_INTERRUPT)
        engine.h.close()  # закрываем лог при прерывании
    except Exception as e:
        print(ERROR_RUNTIME.format(e))
        import traceback
        traceback.print_exc()
        engine.h.close()
    finally:
        rt.stop()


if __name__ == "__main__":
    main()