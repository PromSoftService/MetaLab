# core/core_runtime.py
# -----------------------------------------------------------------------------
# ФУНКЦИОНАЛ:
#   - Context: общий "мир" (время + последние PLC outputs)
#   - Runtime: фоновый тикер (loop) с шагом dt:
#       1) читает PLC outputs (DQ_, AQ_) через opc.read_outputs()
#       2) обновляет context
#       3) вычисляет PLC inputs (DI_, AI_) через сигналы
#       4) пишет PLC inputs через opc.write_inputs()
# -----------------------------------------------------------------------------

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List

from core.opcua_client import OpcUaClient
from core.constants import RT_START_DELAY, RT_DEFAULT_DT, RT_THREAD_JOIN_TIMEOUT, RT_SLEEP_CORRECTION


@dataclass
class Context:
    """Общий контекст. Runtime обновляет его каждый тик."""
    t: float = 0.0
    dt: float = RT_DEFAULT_DT
    tags: Dict[str, Any] = field(default_factory=dict)  # последние PLC outputs (DQ_, AQ_)

    def get(self, tag: str, default: Any = 0) -> Any:
        """Получить значение PLC output (DQ_, AQ_)"""
        v = self.tags.get(tag, default)
        return default if v is None else v


class Signal:
    """Базовый класс для всех сигналов."""
    
    def __init__(self, ctx: Context, debug: bool = False):
        self.ctx = ctx
        self.debug = debug
        self.call_count = 0

    def get_values(self) -> Dict[str, Any]:
        """
        Возвращает словарь {выходной_тег: значение} для всех тегов,
        которые этот сигнал должен обновлять.
        """
        raise NotImplementedError
    
    def log(self, msg: str) -> None:
        """Метод отладки."""
        if self.debug:
            print(f"{DEBUG_SIGN_PREFIX} [{self.__class__.__name__}] {msg}")


class Runtime:
    """
    Фоновый runtime.
    Сигналы сами регистрируются в нем через add_signal.
    """

    def __init__(self, ctx: Context, opc: OpcUaClient, dt: float = RT_DEFAULT_DT):
        self.ctx = ctx
        self.opc = opc
        self.dt = float(dt)

        self.signals: List[Signal] = []  # список всех сигналов
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

        self._t0: Optional[float] = None

    def add_signal(self, signal: Signal) -> None:
        """Добавить сигнал в runtime."""
        with self._lock:
            self.signals.append(signal)

    def remove_signal(self, signal: Signal) -> None:
        """Удалить сигнал из runtime."""
        with self._lock:
            if signal in self.signals:
                self.signals.remove(signal)

    def start(self) -> None:
        """Запустить runtime в фоне."""
        if self._thread and self._thread.is_alive():
            return

        self._stop.clear()
        self.opc.connect()
        self._t0 = time.monotonic()

        self._thread = threading.Thread(target=self._loop, name="plant-runtime", daemon=True)
        self._thread.start()
        time.sleep(RT_START_DELAY)
        print("Runtime started")

    def stop(self) -> None:
        """Остановить runtime."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=RT_THREAD_JOIN_TIMEOUT)
        self.opc.disconnect()
        print("Runtime stopped")

    def _loop(self) -> None:
        next_tick = time.monotonic()

        while not self._stop.is_set():
            now = time.monotonic()

            if now < next_tick:
                sleep_time = max(0.0, next_tick - now - RT_SLEEP_CORRECTION)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                continue

            # Обновляем время
            t = now - (self._t0 or now)
            self.ctx.t = t
            self.ctx.dt = self.dt

            # Читаем PLC outputs
            plc_out = self.opc.read_outputs()
            self.ctx.tags = plc_out

            # Собираем все значения от всех сигналов
            with self._lock:
                signals = list(self.signals)

            plc_in: Dict[str, Any] = {}
            for signal in signals:
                try:
                    values = signal.get_values()
                    plc_in.update(values)
                except Exception as e:
                    print(f"Error computing signal {signal.__class__.__name__}: {e}")

            # Пишем в PLC
            if plc_in:
                try:
                    self.opc.write_inputs(plc_in)
                except Exception as e:
                    print(f"Error writing to PLC: {e}")

            next_tick += self.dt

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()