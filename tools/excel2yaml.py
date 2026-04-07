#!/usr/bin/env python3
# tools/excel2yaml.py
# -----------------------------------------------------------------------------
# КОНВЕРТЕР EXCEL В YAML
# -----------------------------------------------------------------------------
# Использование:
#   python excel2yaml.py scenario.xlsx [config.yaml] [scenario.yaml]
# -----------------------------------------------------------------------------

import pandas as pd
import yaml
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импорта констант
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.constants import *


def excel_to_yaml(excel_file, config_file=None, scenario_file=None):
    """
    Конвертирует Excel файл в YAML конфигурацию и сценарий.
    
    Args:
        excel_file: путь к Excel файлу
        config_file: путь для сохранения config.yaml (если None, генерируется автоматически)
        scenario_file: путь для сохранения scenario.yaml (если None, генерируется автоматически)
    """
    if not os.path.exists(excel_file):
        raise FileNotFoundError(ERROR_FILE_NOT_FOUND.format("Excel", excel_file))
    
    base = Path(excel_file).stem
    
    if config_file is None:
        config_file = f"{base}{CONFIG_FILE_SUFFIX}"
    if scenario_file is None:
        scenario_file = f"{base}{SCENARIO_FILE_SUFFIX}"
    
    print(INFO_READING_EXCEL.format(excel_file))
    xl = pd.ExcelFile(excel_file)
    
    # Результаты
    config = {
        CONFIG_TAGS_OUT: {},
        CONFIG_TAGS_IN: {},
        CONFIG_SIGNALS: []
    }
    scenario = {
        SCENARIO_NAME: base,
        SCENARIO_STEPS: []
    }
    
    # -------------------------------------------------------------------------
    # 1. Tags Out
    # -------------------------------------------------------------------------
    if TAGS_OUT_SHEET in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=TAGS_OUT_SHEET)
        for _, row in df.iterrows():
            name = str(row[COLUMN_NAME]).strip()
            data_type = str(row[COLUMN_DATA_TYPE]).strip().upper()
            comment = str(row[COLUMN_COMMENT]).strip() if not pd.isna(row[COLUMN_COMMENT]) else ""
        
            tag_info = {
                TAG_NODE_ID: f'{OPC_NAMESPACE}"{name}"',
                TAG_DATA_TYPE: data_type,
                TAG_DESCRIPTION: comment,
                TAG_ACCESS_LEVEL: DEFAULT_ACCESS_LEVEL
            }
        
            # Добавляем значение по умолчанию, если есть
            if COLUMN_VALUE in df.columns and not pd.isna(row[COLUMN_VALUE]):
                value = row[COLUMN_VALUE]
                # Преобразуем в нужный тип
                if data_type == OPC_TYPE_BOOL:
                    tag_info[TAG_VALUE] = bool(value)
                elif data_type == OPC_TYPE_INT:
                    tag_info[TAG_VALUE] = int(value)
                else:
                    tag_info[TAG_VALUE] = value
        
            config[CONFIG_TAGS_OUT][name] = tag_info
        print(f"   Загружено TAGS_OUT: {len(config[CONFIG_TAGS_OUT])}")
    
    # -------------------------------------------------------------------------
    # 2. Tags In
    # -------------------------------------------------------------------------
    if TAGS_IN_SHEET in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=TAGS_IN_SHEET)
        for _, row in df.iterrows():
            name = str(row[COLUMN_NAME]).strip()
            data_type = str(row[COLUMN_DATA_TYPE]).strip().upper()
            comment = str(row[COLUMN_COMMENT]).strip() if not pd.isna(row[COLUMN_COMMENT]) else ""
            
            config[CONFIG_TAGS_IN][name] = {
                TAG_NODE_ID: f'{OPC_NAMESPACE}"{name}"',
                TAG_DATA_TYPE: data_type,
                TAG_DESCRIPTION: comment,
                TAG_ACCESS_LEVEL: DEFAULT_ACCESS_LEVEL
            }
        print(f"   Загружено TAGS_IN: {len(config[CONFIG_TAGS_IN])}")
    
    # -------------------------------------------------------------------------
    # 3. Sensor
    # -------------------------------------------------------------------------
    if SENSOR_SHEET in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=SENSOR_SHEET)
        for _, row in df.iterrows():
            signal = {
                TAG_TYPE: SIGNAL_TYPE_SENSOR,
                TAG_NAME: str(row[COL_SENSOR_NAME]).strip(),
                TAG_TAG: str(row[COL_SENSOR_TAG]).strip(),
                TAG_VALUE: float(row[COL_SENSOR_VALUE]) if not pd.isna(row[COL_SENSOR_VALUE]) else 0.0,
                TAG_MIN_VAL: float(row[COL_SENSOR_MIN]) if not pd.isna(row[COL_SENSOR_MIN]) else None,
                TAG_MAX_VAL: float(row[COL_SENSOR_MAX]) if not pd.isna(row[COL_SENSOR_MAX]) else None,
                TAG_PERIOD: float(row[COL_SENSOR_PERIOD]) if not pd.isna(row[COL_SENSOR_PERIOD]) else 10.0,
                TAG_COMMENT: str(row[COL_SENSOR_COMMENT]).strip() if not pd.isna(row[COL_SENSOR_COMMENT]) else "",
                TAG_DEBUG: DEBUG
            }
            # Убираем None значения
            signal = {k: v for k, v in signal.items() if v is not None}
            config[CONFIG_SIGNALS].append(signal)
        print(f"   Загружено Sensor: {len(df)}")
    
    # -------------------------------------------------------------------------
    # 4. Engine
    # -------------------------------------------------------------------------
    if ENGINE_SHEET in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=ENGINE_SHEET)
        for _, row in df.iterrows():
            state_tag = str(row[COL_STATE_TAG]).strip()
            local_ctrl = str(row[COL_LOCAL_CTRL]).strip()
            remote_ctrl = str(row[COL_REMOTE_CTRL]).strip()
            
            signal = {
                TAG_TYPE: SIGNAL_TYPE_ENGINE,
                TAG_NAME: str(row[COL_ENGINE_NAME]).strip(),
                TAG_START_TAG: str(row[COL_START_TAG]).strip(),
                TAG_STATE_TAG: None if state_tag in NULL_VALUES else state_tag,
                TAG_LOCAL_CTRL: None if local_ctrl in NULL_VALUES else local_ctrl,
                TAG_REMOTE_CTRL: None if remote_ctrl in NULL_VALUES else remote_ctrl,
                TAG_RUNUP_TIME: float(row[COL_RUNUP_TIME]),
                TAG_COOLDOWN_TIME: float(row[COL_COOLDOWN_TIME]),
                TAG_COMMENT: str(row[COL_ENGINE_COMMENT]).strip() if not pd.isna(row[COL_ENGINE_COMMENT]) else "",
                TAG_DEBUG: DEBUG
            }
            # Убираем None значения
            signal = {k: v for k, v in signal.items() if v is not None}
            config[CONFIG_SIGNALS].append(signal)
        print(f"   Загружено Engine: {len(df)}")
    
    # -------------------------------------------------------------------------
    # 5. Valve
    # -------------------------------------------------------------------------
    if VALVE_SHEET in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=VALVE_SHEET)
        for _, row in df.iterrows():
            opened_tag = str(row[COL_VALVE_OPENED_TAG]).strip()
            closed_tag = str(row[COL_VALVE_CLOSED_TAG]).strip()
            local_ctrl = str(row[COL_VALVE_LOCAL_CTRL]).strip()
            remote_ctrl = str(row[COL_VALVE_REMOTE_CTRL]).strip()
            
            signal = {
                TAG_TYPE: SIGNAL_TYPE_VALVE,
                TAG_NAME: str(row[COL_VALVE_NAME]).strip(),
                TAG_OPEN_TAG: str(row[COL_VALVE_OPEN_TAG]).strip(),
                TAG_CLOSE_TAG: str(row[COL_VALVE_CLOSE_TAG]).strip(),
                TAG_OPENED_TAG: None if opened_tag in NULL_VALUES else opened_tag,
                TAG_CLOSED_TAG: None if closed_tag in NULL_VALUES else closed_tag,
                TAG_LOCAL_CTRL: None if local_ctrl in NULL_VALUES else local_ctrl,
                TAG_REMOTE_CTRL: None if remote_ctrl in NULL_VALUES else remote_ctrl,
                TAG_FULL_TIME: float(row[COL_VALVE_FULL_TIME]) if not pd.isna(row[COL_VALVE_FULL_TIME]) else 10.0,
                TAG_COMMENT: str(row[COL_VALVE_COMMENT]).strip() if not pd.isna(row[COL_VALVE_COMMENT]) else "",
                TAG_DEBUG: DEBUG
            }
            # Убираем None значения
            signal = {k: v for k, v in signal.items() if v is not None}
            config[CONFIG_SIGNALS].append(signal)
        print(f"   Загружено Valve: {len(df)}")
    
    # -------------------------------------------------------------------------
    # 6. Delay
    # -------------------------------------------------------------------------
    if DELAY_SHEET in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=DELAY_SHEET)
        for _, row in df.iterrows():
            start_tag = str(row[COL_DELAY_START_TAG]).strip()
            state_tag = str(row[COL_DELAY_STATE_TAG]).strip()
        
            signal = {
                TAG_TYPE: SIGNAL_TYPE_DELAY,
                TAG_NAME: str(row[COL_DELAY_NAME]).strip(),
                TAG_START_TAG: start_tag,
                TAG_STATE_TAG: None if state_tag in NULL_VALUES else state_tag,
                TAG_DELAY: float(row[COL_DELAY_TIME]) if not pd.isna(row[COL_DELAY_TIME]) else 0.0,
                TAG_COMMENT: str(row[COL_DELAY_COMMENT]).strip() if not pd.isna(row[COL_DELAY_COMMENT]) else "",
                TAG_DEBUG: DEBUG
            }
            # Убираем None значения, но оставляем start_tag всегда
            signal = {k: v for k, v in signal.items() if v is not None or k == TAG_START_TAG}
            config[CONFIG_SIGNALS].append(signal)
        print(f"   Загружено Delay: {len(df)}")
    
    # -------------------------------------------------------------------------
    # 7. Scenario
    # -------------------------------------------------------------------------
    if SCENARIO_SHEET in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=SCENARIO_SHEET)
        for _, row in df.iterrows():
            obj = str(row.get(COL_SCENARIO_OBJECT, "")).strip()
        
            # Пропускаем пустые строки и комментарии
            if not obj or obj.startswith("//") or obj == "//":
                continue
            
            # Пропускаем "nan" (пустые ячейки)
            if obj.lower() == 'nan':
                continue
        
            step = {
                STEP_OBJECT: obj,
                STEP_METHOD: str(row.get(COL_SCENARIO_METHOD, "")).strip(),
                STEP_TAG: str(row.get(COL_SCENARIO_TAG, "")).strip(),
                STEP_VALUE: str(row.get(COL_SCENARIO_VALUE, "")).strip(),
                STEP_CONFIRM: str(row.get(COL_SCENARIO_COMMENT, "")).strip()
            }
            # Убираем пустые поля
            step = {k: v for k, v in step.items() if v and v.lower() != 'nan'}
            scenario[SCENARIO_STEPS].append(step)
        print(f"   Загружено Scenario: {len(df)}")
    
    # -------------------------------------------------------------------------
    # Сохраняем YAML файлы
    # -------------------------------------------------------------------------
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False, indent=2)
    print(INFO_CONFIG_SAVED.format(config_file))
    
    with open(scenario_file, 'w', encoding='utf-8') as f:
        yaml.dump(scenario, f, allow_unicode=True, sort_keys=False, indent=2)
    print(INFO_SCENARIO_SAVED.format(scenario_file))
    
    return config_file, scenario_file


def main():
    if len(sys.argv) < 2:
        print("Использование: python excel2yaml.py scenario.xlsx [config.yaml] [scenario.yaml]")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    config_file = sys.argv[2] if len(sys.argv) > 2 else None
    scenario_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        excel_to_yaml(excel_file, config_file, scenario_file)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()