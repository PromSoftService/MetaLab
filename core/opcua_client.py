# core/opcua_client.py
# -----------------------------------------------------------------------------
# ФУНКЦИОНАЛ:
#   OPC UA клиент с поддержкой:
#   - Bulk-write (пакетная запись)
#   - Subscription (подписка на изменения)
#   - Retry / auto-reconnect (автопереподключение)
# -----------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, List, Callable
import time
import threading
from collections import defaultdict

from opcua import Client, ua
from opcua.common.subscription import Subscription
from core.constants import *


@dataclass(frozen=True)
class TagMaps:
    """Маппинги 'логическое имя тега' -> OPC UA NodeId string."""
    outputs_to_read: Dict[str, str]   # что читаем из PLC (DQ_, AQ_)
    inputs_to_write: Dict[str, str]   # что пишем в PLC (DI_, AI_)


class OpcUaClient:
    """
    OPC UA client wrapper с поддержкой:
    - Bulk-write
    - Subscription
    - Auto-reconnect
    """

    def __init__(
        self,
        endpoint_url: str,
        tags_out: Dict[str, Dict],  # Что пишем в PLC (DI_, AI_)
        tags_in: Dict[str, Dict],   # Что читаем из PLC (DQ_, AQ_)
        timeout_s: float = OPC_TIMEOUT_S,
        auto_reconnect: bool = OPC_AUTO_RECONNECT,
        reconnect_attempts: int = OPC_RECONNECT_ATTEMPTS,
        reconnect_delay: float = OPC_RECONNECT_DELAY,
    ):
        self.endpoint_url = endpoint_url
        self.timeout_s = timeout_s
        self.auto_reconnect = auto_reconnect
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay

        # Извлекаем node_id из словарей с информацией о тегах
        self.inputs_to_write = {name: info[TAG_NODE_ID] for name, info in tags_out.items()}
        self.outputs_to_read = {name: info[TAG_NODE_ID] for name, info in tags_in.items()}
        
        # Сохраняем типы данных для валидации
        self.input_types = {name: info[TAG_DATA_TYPE] for name, info in tags_out.items()}
        self.output_types = {name: info[TAG_DATA_TYPE] for name, info in tags_in.items()}

        self._client: Optional[Client] = None
        self._nodes_out = {}  # name -> node (для чтения - DQ_, AQ_)
        self._nodes_in = {}   # name -> node (для записи - DI_, AI_)
        
        # Для subscription
        self._subscription: Optional[Subscription] = None
        self._subscription_handlers = {}  # node -> callback
        self._subscribed_nodes = set()
        
        # Для авто-переподключения
        self._reconnect_thread: Optional[threading.Thread] = None
        self._reconnect_event = threading.Event()
        self._connection_lock = threading.Lock()
        self._is_connected = False
        self._connection_callbacks: List[Callable] = []

    def _create_variant(self, value: Any, data_type: str) -> ua.Variant:
        """Создает Variant с правильным типом данных."""
        if data_type == OPC_TYPE_BOOL:
            return ua.Variant(bool(value), ua.VariantType.Boolean)
        elif data_type == OPC_TYPE_BYTE:
            return ua.Variant(int(value) & 0xFF, ua.VariantType.Byte)
        elif data_type == OPC_TYPE_WORD:
            return ua.Variant(int(value) & 0xFFFF, ua.VariantType.UInt16)
        elif data_type == OPC_TYPE_INT:
            val = int(value)
            if val > INT16_MAX:
                val = INT16_MAX
            elif val < INT16_MIN:
                val = INT16_MIN
            return ua.Variant(val, ua.VariantType.Int16)
        elif data_type == OPC_TYPE_DINT:
            return ua.Variant(int(value), ua.VariantType.Int32)
        elif data_type == OPC_TYPE_REAL:
            return ua.Variant(float(value), ua.VariantType.Float)
        elif data_type == OPC_TYPE_TIME:
            return ua.Variant(int(value), ua.VariantType.Int32)
        else:
            return ua.Variant(value)

    def _create_datavalue(self, value: Any, data_type: str) -> ua.DataValue:
        """Создает DataValue с правильным типом."""
        variant = self._create_variant(value, data_type)
        dv = ua.DataValue(variant)
        dv.ServerTimestamp = None
        dv.SourceTimestamp = None
        dv.StatusCode = None
        return dv

    def _reconnect_loop(self):
        """Фоновый поток для переподключения."""
        while not self._reconnect_event.is_set():
            if not self._is_connected:
                attempt = 0
                while attempt < self.reconnect_attempts and not self._reconnect_event.is_set():
                    attempt += 1
                    print(OPC_RECONNECT_ATTEMPT.format(attempt, self.reconnect_attempts))
                    if self._connect():
                        break
                    time.sleep(self.reconnect_delay)
            time.sleep(1)

    def _connect(self) -> bool:
        """Внутренний метод подключения."""
        with self._connection_lock:
            try:
                c = Client(self.endpoint_url, timeout=self.timeout_s)
                c.connect()
                self._client = c
                
                # Восстанавливаем ноды
                self._nodes_out = {k: c.get_node(v) for k, v in self.outputs_to_read.items()}
                self._nodes_in = {k: c.get_node(v) for k, v in self.inputs_to_write.items()}
                
                # Восстанавливаем подписки
                if self._subscribed_nodes:
                    self._create_subscription()
                    for node in self._subscribed_nodes:
                        handler = self._subscription_handlers.get(node)
                        if handler and self._subscription:
                            self._subscription.subscribe_data_change(node, handler=handler)
                
                self._is_connected = True
                print(OPC_CONNECTED.format(self.endpoint_url))
                print(f"   Будет ЧИТАТЬ {len(self._nodes_out)} тегов из PLC (DQ_, AQ_)")
                print(f"   Будет ПИСАТЬ {len(self._nodes_in)} тегов в PLC (DI_, AI_)")
                
                # Вызываем колбэки подключения
                for callback in self._connection_callbacks:
                    try:
                        callback(True)
                    except:
                        pass
                
                return True
                
            except Exception as e:
                print(OPC_RECONNECT_FAILED.format(e))
                self._client = None
                self._is_connected = False
                return False

    def connect(self) -> bool:
        """
        Устанавливает соединение с OPC UA сервером.
        Возвращает True при успешном подключении.
        """
        result = self._connect()
        
        if self.auto_reconnect and not self._reconnect_thread:
            self._reconnect_event.clear()
            self._reconnect_thread = threading.Thread(
                target=self._reconnect_loop,
                name="opc-reconnect",
                daemon=True
            )
            self._reconnect_thread.start()
        
        return result

    def disconnect(self) -> None:
        """Разрывает соединение с OPC UA сервером."""
        self._reconnect_event.set()
        if self._reconnect_thread:
            self._reconnect_thread.join(timeout=2.0)
            self._reconnect_thread = None
        
        with self._connection_lock:
            if self._subscription:
                try:
                    self._subscription.delete()
                except:
                    pass
                self._subscription = None
            
            if self._client is not None:
                try:
                    self._client.disconnect()
                    print(OPC_DISCONNECTED)
                except Exception as e:
                    print(f"⚠️ Ошибка при отключении: {e}")
                finally:
                    self._client = None
                    self._nodes_out.clear()
                    self._nodes_in.clear()
                    self._is_connected = False

    def is_connected(self) -> bool:
        """Проверяет состояние соединения."""
        return self._is_connected and self._client is not None

    def add_connection_callback(self, callback: Callable[[bool], None]) -> None:
        """
        Добавляет колбэк, который вызывается при изменении состояния соединения.
        callback(connected: bool) -> None
        """
        self._connection_callbacks.append(callback)

    # -------------------------------------------------------------------------
    # Bulk-write
    # -------------------------------------------------------------------------
    def write_inputs_bulk(self, values: Dict[str, Any]) -> Dict[str, bool]:
        """
        Пакетная запись значений во входы PLC (DI_, AI_).
        
        Returns:
            Dict[str, bool]: для каждого тега - успех/неудача
        """
        if not self.is_connected():
            if self.auto_reconnect:
                print(OPC_WRITE_DEFERRED)
                return {name: False for name in values.keys()}
            else:
                raise RuntimeError("OPC UA client is not connected")

        results = {}
        write_failed = []
        
        with self._connection_lock:
            for name, value in values.items():
                node = self._nodes_in.get(name)
                if node is None:
                    print(f"⚠️ Неизвестный тег: {name}")
                    results[name] = False
                    write_failed.append(name)
                    continue

                try:
                    data_type = self.input_types.get(name, "")
                    dv = self._create_datavalue(value, data_type)
                    node.set_attribute(ua.AttributeIds.Value, dv)
                    results[name] = True
                except Exception as e:
                    print(OPC_WRITE_ERROR.format(name, value, e))
                    results[name] = False
                    write_failed.append(name)

        if write_failed:
            print(OPC_WRITE_FAILED.format(len(write_failed)))
        
        return results

    def write_inputs(self, values: Dict[str, Any]) -> None:
        """
        Стандартная запись (для обратной совместимости).
        При ошибке кидает исключение.
        """
        results = self.write_inputs_bulk(values)
        failed = [name for name, success in results.items() if not success]
        if failed:
            raise RuntimeError(f"Failed to write tags: {failed}")

    def write_input_simple(self, name: str, value: Any) -> bool:
        """Упрощенный метод для записи одного тега."""
        return self.write_inputs_bulk({name: value}).get(name, False)

    # -------------------------------------------------------------------------
    # Subscription
    # -------------------------------------------------------------------------
    def _create_subscription(self) -> None:
        """Создает подписку, если её нет."""
        if self._subscription or not self._client:
            return
        
        try:
            self._subscription = self._client.create_subscription(OPC_SUBSCRIPTION_INTERVAL_MS, self)
            print(OPC_SUBSCRIPTION_CREATED)
        except Exception as e:
            print(OPC_SUBSCRIPTION_ERROR.format(e))

    def subscribe(self, tag_name: str, callback: Callable[[Any], None]) -> bool:
        """
        Подписывается на изменения тега.
        
        Args:
            tag_name: имя тега (из TAGS_IN)
            callback: функция, вызываемая при изменении значения
        
        Returns:
            bool: True если подписка создана
        """
        node = self._nodes_out.get(tag_name)
        if not node:
            print(OPC_TAG_NOT_FOUND.format(tag_name))
            return False
        
        if not self.is_connected():
            print(f"⚠️ Нет соединения, подписка отложена для {tag_name}")
            self._subscribed_nodes.add(node)
            self._subscription_handlers[node] = callback
            return False
        
        try:
            self._create_subscription()
            if self._subscription:
                self._subscription.subscribe_data_change(node, handler=callback)
                self._subscribed_nodes.add(node)
                self._subscription_handlers[node] = callback
                print(OPC_SUBSCRIBED.format(tag_name))
                return True
        except Exception as e:
            print(OPC_SUBSCRIBE_ERROR.format(tag_name, e))
        
        return False

    def unsubscribe(self, tag_name: str) -> bool:
        """
        Отписывается от изменений тега.
        """
        node = self._nodes_out.get(tag_name)
        if not node:
            return False
        
        if node in self._subscribed_nodes:
            self._subscribed_nodes.remove(node)
            self._subscription_handlers.pop(node, None)
            print(OPC_UNSUBSCRIBED.format(tag_name))
        
        return True

    # -------------------------------------------------------------------------
    # Datachange handler (для subscription)
    # -------------------------------------------------------------------------
    def datachange_notification(self, node, val, data):
        """
        Обработчик изменений данных для подписки.
        Вызывается библиотекой opcua.
        """
        # Ищем имя тега по node
        for name, n in self._nodes_out.items():
            if n == node:
                callback = self._subscription_handlers.get(node)
                if callback:
                    try:
                        callback(val)
                    except Exception as e:
                        print(f"⚠️ Ошибка в callback для {name}: {e}")
                break

    # -------------------------------------------------------------------------
    # Чтение
    # -------------------------------------------------------------------------
    def read_outputs(self) -> Dict[str, Any]:
        """Читает все выходные теги (DQ_, AQ_)."""
        if not self.is_connected():
            if self.auto_reconnect:
                return {}
            raise RuntimeError("OPC UA client is not connected")

        res: Dict[str, Any] = {}
        failed = []
        
        with self._connection_lock:
            for name, node in self._nodes_out.items():
                try:
                    res[name] = node.get_value()
                except Exception as e:
                    print(OPC_READ_ERROR.format(name, e))
                    res[name] = None
                    failed.append(name)
        
        if failed:
            print(OPC_READ_FAILED.format(len(failed)))
        
        return res

    def read_output(self, tag_name: str) -> Any:
        """Читает один выходной тег."""
        if not self.is_connected():
            if self.auto_reconnect:
                return None
            raise RuntimeError("OPC UA client is not connected")

        node = self._nodes_out.get(tag_name)
        if not node:
            raise KeyError(f"Unknown PLC output tag name: {tag_name}")
        
        try:
            return node.get_value()
        except Exception as e:
            print(OPC_READ_ERROR.format(tag_name, e))
            return None

    # -------------------------------------------------------------------------
    # Информация о тегах
    # -------------------------------------------------------------------------
    def get_tag_info(self, tag_name: str, is_input: bool = True) -> Optional[Dict]:
        """Получить информацию о теге по имени."""
        if is_input:
            if tag_name in self._nodes_in:
                return {
                    TAG_NAME: tag_name,
                    "node": self._nodes_in[tag_name],
                    "type": "input",
                    TAG_DATA_TYPE: self.input_types.get(tag_name)
                }
        else:
            if tag_name in self._nodes_out:
                return {
                    TAG_NAME: tag_name,
                    "node": self._nodes_out[tag_name],
                    "type": "output",
                    TAG_DATA_TYPE: self.output_types.get(tag_name)
                }
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику клиента."""
        return {
            "connected": self.is_connected(),
            "endpoint": self.endpoint_url,
            "inputs_count": len(self._nodes_in),
            "outputs_count": len(self._nodes_out),
            "subscribed_count": len(self._subscribed_nodes),
            "auto_reconnect": self.auto_reconnect,
        }