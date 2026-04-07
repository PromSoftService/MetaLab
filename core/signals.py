# signals.py
# -----------------------------------------------------------------------------
# ФУНКЦИОНАЛ:
#   Набор "сигналов" (генераторов) как классов с поддержкой множественных выходов
# -----------------------------------------------------------------------------

from __future__ import annotations

from typing import Any, Optional, List, Dict
import re, math

from core.core_runtime import Context, Signal, Runtime


class ExpressionSignal(Signal):
    """
    Сигнал с поддержкой логических выражений.
    """
    
    def __init__(self,
                 ctx: Context,
                 runtime: Runtime,
                 output_tag: str,
                 expression: str,
                 name: str = "Expression",
                 debug: bool = False):
        super().__init__(ctx, debug)
        
        self.runtime = runtime
        self.output_tag = output_tag
        self.expression = expression
        self.name = name
        
        # Парсим выражение
        self.tokens = self._tokenize(expression)
        self.ast = self._parse_expression(self.tokens)
        
        # Регистрируемся в runtime
        self.runtime.add_signal(self)
        self.log(f"✅ Создан Expression {name} -> {output_tag}")
    
    def _tokenize(self, expr: str) -> List[str]:
        expr = re.sub(r'([&|!()])', r' \1 ', expr)
        return [t for t in expr.split() if t]
    
    def _parse_expression(self, tokens: List[str], start: int = 0) -> Dict:
        pos = start
        left = None
        op = None
        
        while pos < len(tokens):
            token = tokens[pos]
            
            if token == '(':
                sub_result = self._parse_expression(tokens, pos + 1)
                node = sub_result['ast']
                pos = sub_result['pos']
            elif token == ')':
                break
            elif token == '!':
                pos += 1
                if pos < len(tokens):
                    if tokens[pos] == '(':
                        sub_result = self._parse_expression(tokens, pos + 1)
                        node = {'type': 'not', 'value': sub_result['ast']}
                        pos = sub_result['pos']
                    else:
                        node = {'type': 'not', 'value': tokens[pos]}
                        pos += 1
                else:
                    raise ValueError("Invalid NOT expression")
            elif token in ('&', '|'):
                op = token
                pos += 1
                continue
            else:
                node = {'type': 'tag', 'value': token}
                pos += 1
            
            if left is None:
                left = node
            elif op is not None:
                left = {
                    'type': 'binary',
                    'operator': op,
                    'left': left,
                    'right': node
                }
                op = None
        
        return {'ast': left, 'pos': pos}
    
    def _evaluate(self, node: Optional[Dict]) -> bool:
        if node is None:
            return False
        
        if node['type'] == 'tag':
            return bool(self.ctx.get(node['value'], False))
        elif node['type'] == 'not':
            return not self._evaluate(node['value'])
        elif node['type'] == 'binary':
            left_val = self._evaluate(node['left'])
            right_val = self._evaluate(node['right'])
            if node['operator'] == '&':
                return left_val and right_val
            elif node['operator'] == '|':
                return left_val or right_val
        return False
    
    def get_values(self) -> Dict[str, bool]:
        """Возвращает значение для выходного тега."""
        self.call_count += 1
        result = self._evaluate(self.ast)
        
        if self.call_count % 10 == 0:
            self.log(f"📊 {self.name}: {self.expression} = {result}")
        
        return {self.output_tag: result}


class EngineSignal(Signal):
    """
    Симулятор двигателя.
    Может управлять несколькими выходными тегами.
    """
    
    def __init__(self, 
                 ctx: Context,
                 runtime: Runtime,
                 start_tag: str,
                 state_tag: Optional[str] = None,
                 local_control_tag: Optional[str] = None,
                 remote_control_tag: Optional[str] = None,
                 runup_time: float = 2.0,
                 cooldown_time: float = 1.0,
                 name: str = "Motor",
                 comment: str = "",
                 debug: bool = False):
        super().__init__(ctx, debug)
        
        self.runtime = runtime
        self.name = name
        self.comment = comment
        self._start_tag = start_tag
        self._state_tag = state_tag
        self._local_control_tag = local_control_tag
        self._remote_control_tag = remote_control_tag
        self._runup_time = runup_time
        self._cooldown_time = cooldown_time
        
        # Внутреннее состояние
        self._state = False
        self._last_cmd = False
        self._transition_start = 0.0
        self._fail_current_start = False
        self._first_call = True
        
        # Для режимов управления (храним текущие значения)
        self._local_value = False
        self._remote_value = False
        
        # Парсер для выражений в start_tag
        self._start_parser = None
        if any(op in start_tag for op in ['|', '&', '!', '(', ')']):
            self._start_parser = ExpressionSignal(ctx, runtime, "_expr", start_tag, f"{name}_expr", False)
        
        # Регистрируемся в runtime
        self.runtime.add_signal(self)
        self.log(f"✅ Создан EngineSignal {name}")
    
    def _get_cmd(self) -> bool:
        """Вычисляет команду пуска."""
        if self._start_parser:
            return list(self._start_parser.get_values().values())[0]
        return bool(self.ctx.get(self._start_tag, False))
    
    def mode_local(self) -> None:
        """Местный режим: local=1, remote=0"""
        self._local_value = True
        self._remote_value = False
        self.log("mode_local")
    
    def mode_remote(self) -> None:
        """Удаленный режим: local=0, remote=1"""
        self._local_value = False
        self._remote_value = True
        self.log("mode_remote")
    
    def mode_off(self) -> None:
        """Режимы выключены: local=0, remote=0"""
        self._local_value = False
        self._remote_value = False
        self.log("mode_off")
    
    def start_normal(self) -> None:
        """Нормальный пуск."""
        self._fail_current_start = False
        self.log("start_normal")
    
    def start_fail(self) -> None:
        """Отказ при пуске."""
        self._fail_current_start = True
        self.log("start_fail")
    
    def set_start_tag(self, tag: str) -> None:
        self._start_tag = tag
        if any(op in tag for op in ['|', '&', '!', '(', ')']):
            self._start_parser = ExpressionSignal(self.ctx, self.runtime, "_expr", tag, f"{self.name}_expr", False)
        else:
            self._start_parser = None
        self.log(f"start_tag -> {tag}")
    
    def set_runup_time(self, time: float) -> None:
        self._runup_time = time
        self.log(f"runup_time -> {time}")
    
    def set_cooldown_time(self, time: float) -> None:
        self._cooldown_time = time
        self.log(f"cooldown_time -> {time}")
    
    def get_values(self) -> Dict[str, Any]:
        """Возвращает значения для всех выходных тегов."""
        self.call_count += 1
        
        # Вычисляем состояние двигателя
        cmd = self._get_cmd()
        t = self.ctx.t
        
        if self._first_call:
            self._transition_start = t
            self._last_cmd = cmd
            self._first_call = False
            self._state = False
        else:
            if cmd != self._last_cmd:
                self._transition_start = t
                self._last_cmd = cmd
            
            if cmd:
                if self._fail_current_start:
                    self._state = False
                else:
                    elapsed = t - self._transition_start
                    self._state = (elapsed >= self._runup_time)
            else:
                self._state = False
        
        # Формируем результат
        result = {}
        if self._state_tag:
            result[self._state_tag] = self._state
        if self._local_control_tag:
            result[self._local_control_tag] = self._local_value
        if self._remote_control_tag:
            result[self._remote_control_tag] = self._remote_value
        
        # Логирование
        if self.call_count % 10 == 0:
            self.log(f"📊 {self.name}: state={self._state}, local={self._local_value}, remote={self._remote_value}")
        
        return result


class DelaySignal(Signal):
    """
    Сигнал задержки.
    """
    
    def __init__(self,
                 ctx: Context,
                 runtime: Runtime,
                 start_tag: str,
                 state_tag: Optional[str] = None,
                 delay: Optional[float] = None,
                 name: str = "Delay",
                 comment: str = "",
                 debug: bool = False):
        super().__init__(ctx, debug)
        
        self.runtime = runtime
        self.name = name
        self.comment = comment
        self._start_tag = start_tag
        self._state_tag = state_tag
        self._delay = delay if delay is not None else 0.0
        
        self._state = False
        self._last_cmd = False
        self._transition_start = 0.0
        self._first_call = True
        self._mode = "on"  # "on", "off", "forced_off"
        
        # Парсер для выражений
        self._start_parser = None
        if any(op in start_tag for op in ['|', '&', '!', '(', ')']):
            self._start_parser = ExpressionSignal(ctx, runtime, "_expr", start_tag, f"{name}_expr", False)
        
        # Регистрируемся в runtime
        self.runtime.add_signal(self)
        self.log(f"✅ Создан DelaySignal {name}")
    
    def _get_cmd(self) -> bool:
        if self._start_parser:
            return list(self._start_parser.get_values().values())[0]
        return bool(self.ctx.get(self._start_tag, False))
    
    def delay_on(self) -> None:
        self._mode = "on"
        self.log("delay_on")
    
    def delay_off(self) -> None:
        self._mode = "off"
        self.log("delay_off")
    
    def off(self) -> None:
        self._mode = "forced_off"
        self.log("forced_off")
    
    def set_start_tag(self, tag: str) -> None:
        self._start_tag = tag
        if any(op in tag for op in ['|', '&', '!', '(', ')']):
            self._start_parser = ExpressionSignal(self.ctx, self.runtime, "_expr", tag, f"{self.name}_expr", False)
        else:
            self._start_parser = None
        self.log(f"start_tag -> {tag}")
    
    def set_delay(self, delay: float) -> None:
        self._delay = delay
        self.log(f"delay -> {delay}")
    
    def get_values(self) -> Dict[str, bool]:
        self.call_count += 1
        
        if not self._state_tag or self._mode == "forced_off":
            return {self._state_tag: False} if self._state_tag else {}
        
        cmd = self._get_cmd()
        t = self.ctx.t
        
        if self._first_call:
            self._transition_start = t
            self._last_cmd = cmd
            self._first_call = False
            self._state = False
        else:
            if cmd != self._last_cmd:
                self._transition_start = t
                self._last_cmd = cmd
            
            elapsed = t - self._transition_start
            
            if self._mode == "on":
                if cmd:
                    self._state = (elapsed >= self._delay)
                else:
                    self._state = False
            else:  # off
                if cmd:
                    self._state = True
                else:
                    self._state = (elapsed < self._delay)
        
        if self.call_count % 10 == 0:
            self.log(f"📊 {self.name}: state={self._state}")
        
        return {self._state_tag: self._state}


class SensorSignal(Signal):
    """
    Сигнал датчика.
    """
    
    def __init__(self,
                 ctx: Context,
                 runtime: Runtime,
                 name: str,
                 tag: str,
                 value: Optional[float] = None,
                 min_val: Optional[float] = None,
                 max_val: Optional[float] = None,
                 period: Optional[float] = None,
                 comment: str = "",
                 debug: bool = False):
        super().__init__(ctx, debug)
        
        self.runtime = runtime
        self.name = name
        self._tag = tag
        self._value = value if value is not None else 0.0
        self._min = min_val if min_val is not None else 0.0
        self._max = max_val if max_val is not None else 100.0
        self._period = period if period is not None else 10.0
        self.comment = comment
        
        self._mode = "const"
        self._current = self._value
        self._start_value = self._value
        self._start_time = 0.0
        self._target = self._value
        self._first_call = True
        
        # Регистрируемся в runtime
        self.runtime.add_signal(self)
        self.log(f"✅ Создан SensorSignal {name} -> {tag}")
    
    def const(self, value: Optional[float] = None) -> None:
        if value is not None:
            self._value = value
        self._mode = "const"
        self._current = self._value
        self.log(f"const: {self._value}")
    
    def ramp(self, target: Optional[float] = None) -> None:
        if target is not None:
            self._target = target
        self._mode = "ramp"
        self._start_value = self._current
        self._start_time = self.ctx.t
        self.log(f"ramp: to {self._target}")
    
    def sin(self) -> None:
        self._mode = "sin"
        self._start_time = self.ctx.t
        self.log(f"sin: min={self._min}, max={self._max}")
    
    def set_value(self, value: float) -> None:
        self._value = value
        if self._mode == "const":
            self._current = value
    
    def set_target(self, target: float) -> None:
        self._target = target
    
    def set_min(self, min_val: float) -> None:
        self._min = min_val
    
    def set_max(self, max_val: float) -> None:
        self._max = max_val
    
    def set_period(self, period: float) -> None:
        self._period = period
    
    def get_values(self) -> Dict[str, float]:
        self.call_count += 1
        t = self.ctx.t
        
        if self._first_call:
            self._start_time = t
            self._first_call = False
            return {self._tag: self._current}
        
        if self._mode == "const":
            self._current = self._value
        elif self._mode == "ramp":
            elapsed = t - self._start_time
            if elapsed >= self._period:
                self._current = self._target
                self._mode = "const"
                self._value = self._target
            else:
                progress = elapsed / self._period
                self._current = self._start_value + (self._target - self._start_value) * progress
        elif self._mode == "sin":
            elapsed = t - self._start_time
            if self._period > 0:
                norm_time = (elapsed % self._period) / self._period * 2 * 3.14159
                sin_val = math.sin(norm_time)
                amplitude = (self._max - self._min) / 2
                offset = (self._max + self._min) / 2
                self._current = offset + sin_val * amplitude
        
        if self.call_count % 10 == 0:
            self.log(f"📊 {self.name}: {self._current:.2f}")
        
        return {self._tag: self._current}

class ValveSignal(Signal):
    """
    Симулятор клапана с плавным изменением положения.
    
    Читает команды из PLC (open_tag, close_tag - TAGS_IN) и возвращает:
    - opened_tag: True если положение >= 100%
    - closed_tag: True если положение <= 0%
    
    Положение изменяется плавно в зависимости от времени полного хода.
    """
    
    # Приватные константы для ограничений
    __MIN_POSITION = 0.0
    __MAX_POSITION = 100.0
    
    def __init__(self,
                 ctx: Context,
                 runtime: Runtime,
                 name: str,
                 open_tag: str,           # команда на открытие
                 close_tag: str,          # команда на закрытие
                 opened_tag: Optional[str] = None,   # концевик открыто
                 closed_tag: Optional[str] = None,   # концевик закрыто
                 local_control_tag: Optional[str] = None,
                 remote_control_tag: Optional[str] = None,
                 full_time: float = 10.0,  # время полного хода (сек)
                 comment: str = "",
                 debug: bool = False):
        super().__init__(ctx, debug)
        
        self.runtime = runtime
        self.name = name
        self.comment = comment
        
        # Входные теги (читаем из PLC)
        self._open_tag = open_tag
        self._close_tag = close_tag
        
        # Выходные теги (пишем в PLC)
        self._opened_tag = opened_tag
        self._closed_tag = closed_tag
        self._local_control_tag = local_control_tag
        self._remote_control_tag = remote_control_tag
        
        # Параметры
        self._full_time = full_time
        self._speed = 100.0 / full_time if full_time > 0 else 0  # % в секунду
        
        # Внутреннее состояние
        self._position = self.__MIN_POSITION
        self._opened = False
        self._closed = True
        self._last_open = False
        self._last_close = False
        self._last_update_time = 0.0
        self._fail_mode = False  # режим аварии
        self._first_call = True
        
        # Для режимов управления
        self._local_value = False
        self._remote_value = False
        
        # Парсеры для выражений
        self._open_parser = self._create_parser(open_tag, f"{name}_open")
        self._close_parser = self._create_parser(close_tag, f"{name}_close")
        
        # Регистрируемся в runtime
        self.runtime.add_signal(self)
        self.log(f"✅ Создан ValveSignal {name}")
    
    def _create_parser(self, tag: str, name: str) -> Optional[ExpressionSignal]:
        """Создает парсер для выражения, если нужно."""
        if any(op in tag for op in ['|', '&', '!', '(', ')']):
            parser = ExpressionSignal(self.ctx, self.runtime, "_expr", tag, name, False)
            return parser
        return None
    
    def _get_open_cmd(self) -> bool:
        """Вычисляет команду открытия."""
        if self._open_parser:
            return list(self._open_parser.get_values().values())[0]
        return bool(self.ctx.get(self._open_tag, False))
    
    def _get_close_cmd(self) -> bool:
        """Вычисляет команду закрытия."""
        if self._close_parser:
            return list(self._close_parser.get_values().values())[0]
        return bool(self.ctx.get(self._close_tag, False))
    
    def _clamp_position(self, position: float) -> float:
        """Ограничивает положение в пределах [MIN, MAX]."""
        return max(self.__MIN_POSITION, min(self.__MAX_POSITION, position))
    
    # Режимы управления
    def mode_local(self) -> None:
        """Местный режим: local=1, remote=0"""
        self._local_value = True
        self._remote_value = False
        self.log("mode_local")
    
    def mode_remote(self) -> None:
        """Удаленный режим: local=0, remote=1"""
        self._local_value = False
        self._remote_value = True
        self.log("mode_remote")
    
    def mode_off(self) -> None:
        """Режимы выключены: local=0, remote=0"""
        self._local_value = False
        self._remote_value = False
        self.log("mode_off")
    
    # Режимы работы
    def normal(self) -> None:
        """Нормальный режим - концевики работают."""
        self._fail_mode = False
        self.log("normal")
    
    def fail(self) -> None:
        """Режим аварии - концевики не срабатывают."""
        self._fail_mode = True
        self.log("fail")
    
    # Методы для изменения параметров
    def set_open_tag(self, tag: str) -> None:
        self._open_tag = tag
        self._open_parser = self._create_parser(tag, f"{self.name}_open")
        self.log(f"open_tag -> {tag}")
    
    def set_close_tag(self, tag: str) -> None:
        self._close_tag = tag
        self._close_parser = self._create_parser(tag, f"{self.name}_close")
        self.log(f"close_tag -> {tag}")
    
    def set_opened_tag(self, tag: Optional[str]) -> None:
        self._opened_tag = tag
        self.log(f"opened_tag -> {tag}")
    
    def set_closed_tag(self, tag: Optional[str]) -> None:
        self._closed_tag = tag
        self.log(f"closed_tag -> {tag}")
    
    def set_local_control_tag(self, tag: Optional[str]) -> None:
        self._local_control_tag = tag
        self.log(f"local_control_tag -> {tag}")
    
    def set_remote_control_tag(self, tag: Optional[str]) -> None:
        self._remote_control_tag = tag
        self.log(f"remote_control_tag -> {tag}")
    
    def set_full_time(self, time: float) -> None:
        self._full_time = time
        self._speed = 100.0 / time if time > 0 else 0
        self.log(f"full_time -> {time}")
    
    def get_values(self) -> Dict[str, Any]:
        """Возвращает значения для всех выходных тегов."""
        self.call_count += 1
        
        open_cmd = self._get_open_cmd()
        close_cmd = self._get_close_cmd()
        t = self.ctx.t
        
        # Первый вызов - инициализация
        if self._first_call:
            self._last_update_time = t
            self._last_open = open_cmd
            self._last_close = close_cmd
            self._first_call = False
        else:
            # Вычисляем прошедшее время
            dt = t - self._last_update_time
            self._last_update_time = t
            
            # Отслеживаем изменение команд
            if open_cmd != self._last_open or close_cmd != self._last_close:
                self._last_open = open_cmd
                self._last_close = close_cmd
                self.log(f"🔄 команды: open={open_cmd}, close={close_cmd}")
            
            # Обновляем положение, если не в режиме аварии
            if not self._fail_mode:
                # Определяем направление движения
                if self._last_open and not self._last_close:
                    # Движение к открытию
                    delta = self._speed * dt
                    self._position = self._clamp_position(self._position + delta)
                    self.log(f"▶️ открытие: +{delta:.2f}% -> {self._position:.2f}%")
                elif self._last_close and not self._last_open:
                    # Движение к закрытию
                    delta = self._speed * dt
                    self._position = self._clamp_position(self._position - delta)
                    self.log(f"◀️ закрытие: -{delta:.2f}% -> {self._position:.2f}%")
                
                # Определяем состояние концевиков
                self._opened = (self._position >= self.__MAX_POSITION)
                self._closed = (self._position <= self.__MIN_POSITION)
            else:
                # Режим аварии - все концевики ложь
                self._opened = False
                self._closed = False
                # Положение не меняется
                self.log(f"⚠️ авария: положение заморожено на {self._position:.2f}%")
        
        # Формируем результат
        result = {}
        if self._opened_tag:
            result[self._opened_tag] = self._opened
        if self._closed_tag:
            result[self._closed_tag] = self._closed
        if self._local_control_tag:
            result[self._local_control_tag] = self._local_value
        if self._remote_control_tag:
            result[self._remote_control_tag] = self._remote_value
        
        # Логирование
        if self.call_count % 10 == 0:
            self.log(f"📊 {self.name}: pos={self._position:.1f}%, opened={self._opened}, closed={self._closed}")
        
        return result
    
    def get_position(self) -> float:
        """Получить текущее положение клапана (0-100%)."""
        return self._position
    
    def set_position(self, position: float) -> None:
        """Принудительно установить положение клапана."""
        self._position = self._clamp_position(position)
        self.log(f"⚡ принудительная установка положения: {self._position:.2f}%")


