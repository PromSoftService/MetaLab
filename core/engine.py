#!/usr/bin/env python3
# core/engine.py
# -----------------------------------------------------------------------------
# ДВИЖОК ИНТЕРПРЕТАЦИИ СЦЕНАРИЕВ
# -----------------------------------------------------------------------------

import yaml
import time
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from core.core_runtime import Context, Runtime
from core.signals import (
    SensorSignal, EngineSignal, ValveSignal, DelaySignal, ExpressionSignal
)
from core.constants import *


class ScenarioHelper:
    """Хелпер для сценария - вывод сообщений с временем и подтверждения"""
    
    def __init__(self, ctx, scenario_name="scenario", log_mode=LOG_MODE_DEFAULT, log_file=None):
        self.ctx = ctx
        self.scenario_name = scenario_name
        self.log_mode = log_mode
        self.log_file = log_file
        self.start_time = time.time()
        self.session_id = datetime.now().strftime(LOG_DATETIME_FORMAT)
        
        # Создаем папку для логов, если нужно
        if self.log_mode in [LOG_MODE_FILE, LOG_MODE_BOTH]:
            logs_dir = os.path.join(Path(__file__).parent.parent, LOGS_DIR)
            os.makedirs(logs_dir, exist_ok=True)
            
            # Автоматически создаем имя лог-файла, если не указано
            if not self.log_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Используем имя сценария в имени файла
                safe_name = "".join(c for c in self.scenario_name if c.isalnum() or c in ('-', '_')).rstrip()
                self.log_file = os.path.join(logs_dir, f"{safe_name}_log_{timestamp}{LOG_FILENAME_EXT}")
            elif not os.path.isabs(self.log_file):
                self.log_file = os.path.join(logs_dir, self.log_file)
        
        # Открываем файл для записи
        if self.log_file and self.log_mode in [LOG_MODE_FILE, LOG_MODE_BOTH]:
            self._file = open(self.log_file, 'w', encoding='utf-8')
            self._write_header()
        else:
            self._file = None
    
    def _write_header(self):
        """Записывает заголовок лог-файла."""
        self._file.write(LOG_HEADER_START.format(self.session_id) + "\n\n")
        self._file.flush()
    
    def _write(self, msg: str):
        """Внутренний метод записи в лог."""
        # В консоль
        if self.log_mode in [LOG_MODE_CONSOLE, LOG_MODE_BOTH]:
            print(msg)
        
        # В файл
        if self._file and self.log_mode in [LOG_MODE_FILE, LOG_MODE_BOTH]:
            # Убираем ANSI-коды цветов для файла
            clean_msg = re.sub(r'\033\[[0-9;]*m', '', msg)
            self._file.write(clean_msg + '\n')
            self._file.flush()
    
    def log(self, msg: str) -> None:
        """Информационное сообщение"""
        self._write(f"\n[t={self.ctx.t:.1f}] 📢 {msg}")
    
    def action(self, msg: str) -> None:
        """Действие без подтверждения"""
        self._write(f"\n[t={self.ctx.t:.1f}] ⚙️ {msg}")
    
    def confirm(self, msg: str) -> None:
        """Действие с подтверждением пользователя"""
        prompt = f"\n[t={self.ctx.t:.1f}] 👆 ПОДТВЕРДИТЕ: {msg}"
        self._write(prompt)
        input()  # ждем нажатия Enter без вывода
        self._write(LOG_CONFIRMED.format(self.ctx.t, msg))
    
    def success(self, msg: str) -> None:
        """Успешное завершение этапа"""
        self._write(f"\n[t={self.ctx.t:.1f}] ✅ {msg}")
    
    def warning(self, msg: str) -> None:
        """Предупреждение"""
        self._write(f"\n[t={self.ctx.t:.1f}] ⚠️ {msg}")
    
    def error(self, msg: str) -> None:
        """Ошибка"""
        self._write(f"\n[t={self.ctx.t:.1f}] ❌ {msg}")
    
    def wait(self, seconds: float) -> None:
        """Ожидание с сообщением"""
        self._write(f"\n[t={self.ctx.t:.1f}] ⏳ Ожидание {seconds} сек...")
        time.sleep(seconds)
    
    def assert_eq(self, actual, expected, msg: str) -> None:
        """Проверка равенства (для автоматических тестов)"""
        if actual != expected:
            self.error(f"{msg}: ожидалось {expected}, получено {actual}")
            raise AssertionError(f"{msg}: {actual} != {expected}")
        self.success(f"{msg}: {actual} == {expected}")
    
    def close(self):
        """Закрывает лог-файл."""
        if self._file:
            end_time = datetime.now().strftime(LOG_DATETIME_FORMAT)
            self._file.write("\n" + LOG_HEADER_END.format(end_time) + "\n")
            self._file.close()


class ScenarioEngine:
    """
    Движок интерпретации сценариев.
    
    Загружает конфигурацию (теги и сигналы) из YAML,
    затем выполняет шаги сценария.
    """
    
    # Маппинг типов сигналов на классы
    SIGNAL_CLASSES = {
        SIGNAL_TYPE_SENSOR: SensorSignal,
        SIGNAL_TYPE_ENGINE: EngineSignal,
        SIGNAL_TYPE_VALVE: ValveSignal,
        SIGNAL_TYPE_DELAY: DelaySignal,
        SIGNAL_TYPE_EXPRESSION: ExpressionSignal,
    }
    
    def __init__(self, ctx: Context, runtime: Runtime, scenario_name="scenario", log_mode=LOG_MODE_DEFAULT, log_file=None):
        self.ctx = ctx
        self.runtime = runtime
        self.signals: Dict[str, Any] = {}  # имя сигнала -> объект
        self.signal_configs: List[Dict] = []  # конфиги сигналов для отложенного создания
        self.h = ScenarioHelper(ctx, scenario_name, log_mode, log_file)
        self.tags_out = {}
        self.tags_in = {}
        self.initial_values = {}  # начальные значения тегов
        self.scenario = None
    
    def initialize_tags(self):
        """Записывает начальные значения из конфигурации."""
        if not self.initial_values:
            return
        
        writes = {}
        for tag_name, value in self.initial_values.items():
            writes[tag_name] = value
        
        if writes:
            self.h.action(INFO_TAGS_INIT)
            self.runtime.opc.write_inputs(writes)
    
    def load_config(self, config_file: str):
        """
        Загружает конфигурацию из YAML файла.
        
        Returns:
            tuple: (tags_out, tags_in) - словари тегов для OPC клиента
        """
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Загружаем теги
        self.tags_out = config.get(CONFIG_TAGS_OUT, {})
        self.tags_in = config.get(CONFIG_TAGS_IN, {})
        
        # Сохраняем начальные значения
        self.initial_values = {}
        for tag_name, tag_info in self.tags_out.items():
            if TAG_VALUE in tag_info:
                self.initial_values[tag_name] = tag_info[TAG_VALUE]
        
        # Сохраняем конфиги сигналов для последующего создания
        self.signal_configs = config.get(CONFIG_SIGNALS, [])
        
        self.h.log(INFO_CONFIG_LOADED.format(len(self.signal_configs)))
        return self.tags_out, self.tags_in
    
    def create_signals(self):
        """Создает сигналы после инициализации тегов."""
        for signal_config in self.signal_configs:
            self._create_signal(signal_config.copy())  # копируем, чтобы не менять оригинал
        self.h.log(INFO_SIGNALS_CREATED.format(len(self.signals)))
    
    def _create_signal(self, config: dict):
        """Создает сигнал по конфигурации."""
        signal_type = config.pop(TAG_TYPE)
        signal_class = self.SIGNAL_CLASSES.get(signal_type)
        
        if not signal_class:
            raise ValueError(ERROR_UNKNOWN_SIGNAL.format(signal_type))
        
        # Все сигналы получают ctx и runtime
        signal = signal_class(ctx=self.ctx, runtime=self.runtime, **config)
        
        # Сохраняем по имени
        name = config.get(TAG_NAME)
        if name:
            self.signals[name] = signal
        
        return signal
    
    def load_scenario(self, scenario_file: str):
        """Загружает сценарий из YAML файла."""
        with open(scenario_file, 'r', encoding='utf-8') as f:
            self.scenario = yaml.safe_load(f)
        
        scenario_name = self.scenario.get(SCENARIO_NAME, 'unknown')
        # Обновляем имя в helper (на случай, если оно изменилось)
        self.h.scenario_name = scenario_name
        
        self.h.log(INFO_SCENARIO_LOADED.format(scenario_name))
        self.h.log(INFO_STEPS_COUNT.format(len(self.scenario.get(SCENARIO_STEPS, []))))
    
    def run(self):
        """Выполняет загруженный сценарий."""
        if not self.scenario:
            raise RuntimeError("Сценарий не загружен. Вызовите load_scenario()")
        
        self.h.log(INFO_RUN_START.format(self.scenario.get(SCENARIO_NAME, 'unknown')))
        
        # 1. ИНИЦИАЛИЗАЦИЯ ТЭГОВ
        self.initialize_tags()
        
        # 2. СТАРТ СЦЕНАРИЯ
        self.h.confirm(INFO_SCENARIO_START)
        
        # 3. СОЗДАНИЕ СИГНАЛОВ
        self.h.log(INFO_SIGNALS_CREATE)
        self.create_signals()
        
        # 4. ТЕЛО СЦЕНАРИЯ
        for i, step in enumerate(self.scenario.get(SCENARIO_STEPS, []), 1):
            try:
                self._execute_step(step)
            except Exception as e:
                self.h.error(ERROR_STEP.format(i, e))
                raise
        
        # 5. СТОП СЦЕНАРИЯ
        self.h.confirm(INFO_SCENARIO_STOP)
        self.h.log(INFO_SCENARIO_COMPLETE)
        self.h.close()
    
    def _execute_step(self, step: dict):
        """Выполняет один шаг сценария."""
        obj = step.get(STEP_OBJECT)
        method = step.get(STEP_METHOD)
        tag = step.get(STEP_TAG, '')
        value = step.get(STEP_VALUE, '')
        confirm = step.get(STEP_CONFIRM, '')
        
        # Helper functions
        if obj == HELPER_OBJECT:
            if method == HELPER_CONFIRM and confirm:
                self.h.confirm(confirm)
            elif method == HELPER_LOG and confirm:
                self.h.log(confirm)
            elif method == HELPER_WAIT and value:
                try:
                    self.h.wait(float(value))
                except ValueError:
                    pass
            elif method == HELPER_ACTION and confirm:
                self.h.action(confirm)
            elif method == HELPER_SUCCESS and confirm:
                self.h.success(confirm)
            elif method == HELPER_WARNING and confirm:
                self.h.warning(confirm)
            elif method == HELPER_ERROR and confirm:
                self.h.error(confirm)
            return
        
        # OPC write
        if obj == OPC_OBJECT:
            if method == OPC_WRITE and tag and value:
                try:
                    # Пробуем преобразовать в число
                    val = float(value)
                except ValueError:
                    val = value
                self.runtime.opc.write_inputs({tag: val})
                if confirm:
                    self.h.confirm(confirm)
            return
        
        # Вызов метода сигнала
        if obj and method:
            signal = self.signals.get(obj)
            if not signal:
                raise ValueError(ERROR_SIGNAL_NOT_FOUND.format(obj))
            
            # Получаем метод
            func = getattr(signal, method, None)
            if not func:
                raise ValueError(ERROR_METHOD_NOT_FOUND.format(method, obj))
            
            # Определяем аргумент: сначала tag, потом value
            arg = None
            if tag:
                arg = tag
            elif value:
                arg = value
            
            # Вызываем с аргументом или без
            if arg is not None:
                try:
                    # Пробуем преобразовать в число
                    val = float(arg)
                    func(val)
                except ValueError:
                    func(arg)
            else:
                func()
            
            # Подтверждение, если есть
            if confirm:
                self.h.confirm(confirm)