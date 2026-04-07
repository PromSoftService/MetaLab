# core/constants.py
# -----------------------------------------------------------------------------
# ОБЩИЕ КОНСТАНТЫ ДЛЯ ВСЕХ МОДУЛЕЙ
# -----------------------------------------------------------------------------

# Листы Excel
TAGS_OUT_SHEET = "Tags Out"
TAGS_IN_SHEET = "Tags In"
SENSOR_SHEET = "Sensor"
ENGINE_SHEET = "Engine"
VALVE_SHEET = "Valve"
DELAY_SHEET = "Delay"
SCENARIO_SHEET = "Scenario"

# Колонки в листах тегов
COLUMN_NAME = "Name"
COLUMN_DATA_TYPE = "Data Type"
COLUMN_VALUE = "Value"
COLUMN_COMMENT = "Comment"

# Колонки в листе датчиков
COL_SENSOR_NAME = "Name"
COL_SENSOR_TAG = "Tag"
COL_SENSOR_VALUE = "Value"
COL_SENSOR_MIN = "Min"
COL_SENSOR_MAX = "Max"
COL_SENSOR_PERIOD = "Period"
COL_SENSOR_COMMENT = "Comment"

# Колонки в листе двигателей
COL_ENGINE_NAME = "Name"
COL_START_TAG = "Start Tag"
COL_STATE_TAG = "State Tag"
COL_LOCAL_CTRL = "Local Control Tag"
COL_REMOTE_CTRL = "Remote Control Tag"
COL_RUNUP_TIME = "Runap Time"
COL_COOLDOWN_TIME = "Cooldown Time"
COL_ENGINE_COMMENT = "Comment"

# Колонки в листе клапанов
COL_VALVE_NAME = "Name"
COL_VALVE_OPENED_TAG = "Opened Tag"
COL_VALVE_CLOSED_TAG = "Closed Tag"
COL_VALVE_OPEN_TAG = "Open Tag"
COL_VALVE_CLOSE_TAG = "Close Tag"
COL_VALVE_LOCAL_CTRL = "Local Control Tag"
COL_VALVE_REMOTE_CTRL = "Remote Control Tag"
COL_VALVE_FULL_TIME = "Full Time"
COL_VALVE_COMMENT = "Comment"

# Колонки в листе задержек
COL_DELAY_NAME = "Name"
COL_DELAY_START_TAG = "Start Tag"
COL_DELAY_STATE_TAG = "State Tag"
COL_DELAY_TIME = "Delay"
COL_DELAY_COMMENT = "Comment"

# Колонки в листе сценария
COL_SCENARIO_OBJECT = "Object"
COL_SCENARIO_METHOD = "Method"
COL_SCENARIO_TAG = "Tag"
COL_SCENARIO_VALUE = "Value"
COL_SCENARIO_COMMENT = "Comment"

# Настройки OPC UA
OPC_NAMESPACE = "ns=3;s="
DEFAULT_ACCESS_LEVEL = 3

# Значения, которые считаются None
NULL_VALUES = ["Null", "null", "None", "", "nan"]

# Настройки отладки по умолчанию
DEBUG = False

# Форматы имен файлов
CONFIG_FILE_SUFFIX = "_config.yaml"
SCENARIO_FILE_SUFFIX = "_scenario.yaml"
YAML_EXTENSIONS = ('.yaml', '.yml')
EXCEL_EXTENSIONS = ('.xlsx', '.xls')

# Папки
SCENARIOS_DIR = "scenarios"
LOGS_DIR = "logs"  # Новая папка для логов
TEMP_DIR_PREFIX = "scenario_yaml_"

# Форматы логов
LOG_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILENAME_FORMAT = "scenario_log_%Y%m%d_%H%M%S.txt"
LOG_FILENAME_PREFIX = "scenario_log_"
LOG_FILENAME_EXT = ".txt"

# Режимы логирования
LOG_MODE_CONSOLE = 1      # только консоль
LOG_MODE_FILE = 2         # только файл
LOG_MODE_BOTH = 3         # и консоль, и файл
LOG_MODE_DEFAULT = LOG_MODE_BOTH

# Сообщения об ошибках
ERROR_FILE_NOT_FOUND = "❌ Файл {} не найден: {}"
ERROR_INVALID_FORMAT = "❌ Неверный формат файла. Используйте .xlsx, .yaml или .yml"
ERROR_NO_INPUT = "❌ Укажите input файл или --config и --scenario"
ERROR_CONFIG_NOT_FOUND = "❌ Файл конфигурации не найден: {}"
ERROR_SCENARIO_NOT_FOUND = "❌ Файл сценария не найден: {}"
ERROR_UNKNOWN_SIGNAL = "❌ Неизвестный тип сигнала: {}"
ERROR_SIGNAL_NOT_FOUND = "❌ Сигнал не найден: {}"
ERROR_METHOD_NOT_FOUND = "❌ Метод {} не найден у сигнала {}"
ERROR_STEP = "❌ Ошибка на шаге {}: {}"
ERROR_RUNTIME = "❌ Ошибка: {}"

# Информационные сообщения
INFO_EXCEL_CONVERT = "📖 Конвертация Excel в YAML: {}"
INFO_READING_EXCEL = "📖 Чтение Excel: {}"
INFO_YAML_TEMP = "   YAML файлы созданы во временной папке: {}"
INFO_YAML_SAVED = "   YAML файлы будут сохранены в {}"
INFO_CONFIG_SAVED = "✅ Сохранена конфигурация: {}"
INFO_SCENARIO_SAVED = "✅ Сохранен сценарий: {}"
INFO_CONFIG_LOADED = "✅ Загружена конфигурация: {} сигналов"
INFO_SCENARIO_LOADED = "✅ Загружен сценарий: {}"
INFO_STEPS_COUNT = "   Шагов: {}"
INFO_RUN_START = "\n🚀 Запуск сценария: {}"
INFO_RUN_URL = "   URL: {}"
INFO_RUN_CONFIG = "   Конфиг: {}"
INFO_RUN_SCENARIO = "   Сценарий: {}"
INFO_TAGS_INIT = "⚙️ ИНИЦИАЛИЗАЦИЯ ТЭГОВ"
INFO_SCENARIO_START = "🚀 СТАРТ СЦЕНАРИЯ"
INFO_SCENARIO_STOP = "🛑 СТОП СЦЕНАРИЯ"
INFO_SIGNALS_CREATE = "📡 СОЗДАНИЕ СИГНАЛОВ"
INFO_SIGNALS_CREATED = "✅ Создано сигналов: {}"
INFO_SCENARIO_COMPLETE = "\n✅ Сценарий завершен"
INFO_USER_INTERRUPT = "\n⚠️ Остановлено пользователем"
INFO_NO_CONFIG = "⚠️ Файл конфигурации не найден, будут использованы только теги из сценария"

# Сообщения логов
LOG_HEADER_START = "=" * 80 + "\nСЦЕНАРИЙ ЗАПУЩЕН: {}\n" + "=" * 80
LOG_HEADER_END = "=" * 80 + "\nСЦЕНАРИЙ ЗАВЕРШЕН: {}\n" + "=" * 80
LOG_CONFIRMED = "[t={:.1f}] ✓ ПОДТВЕРЖДЕНО: {}"

# Сообщения OPC клиента
OPC_CONNECTED = "✅ Подключено к {}"
OPC_DISCONNECTED = "✅ Отключено от OPC UA сервера"
OPC_RECONNECT_ATTEMPT = "🔄 Попытка переподключения {}/{}..."
OPC_RECONNECT_FAILED = "❌ Ошибка подключения: {}"
OPC_SUBSCRIPTION_CREATED = "✅ Создана подписка"
OPC_SUBSCRIPTION_ERROR = "⚠️ Ошибка создания подписки: {}"
OPC_SUBSCRIBED = "✅ Подписка на {}"
OPC_UNSUBSCRIBED = "✅ Отписка от {}"
OPC_SUBSCRIBE_ERROR = "⚠️ Ошибка подписки на {}: {}"
OPC_TAG_NOT_FOUND = "⚠️ Тег {} не найден для подписки"
OPC_READ_ERROR = "⚠️ Ошибка чтения {}: {}"
OPC_WRITE_ERROR = "⚠️ Ошибка записи {}={}: {}"
OPC_WRITE_FAILED = "⚠️ Не удалось записать {} тегов"
OPC_READ_FAILED = "⚠️ Не удалось прочитать {} тегов"
OPC_CONNECTION_LOST = "⚠️ Соединение потеряно"
OPC_WRITE_DEFERRED = "⚠️ Нет соединения, запись отложена"

# Теги в конфиге
TAG_NODE_ID = "node_id"
TAG_DATA_TYPE = "data_type"
TAG_DESCRIPTION = "description"
TAG_ACCESS_LEVEL = "access_level"
TAG_VALUE = "value"
TAG_TYPE = "type"
TAG_NAME = "name"
TAG_START_TAG = "start_tag"
TAG_STATE_TAG = "state_tag"
TAG_LOCAL_CTRL = "local_control_tag"
TAG_REMOTE_CTRL = "remote_control_tag"
TAG_RUNUP_TIME = "runup_time"
TAG_COOLDOWN_TIME = "cooldown_time"
TAG_COMMENT = "comment"
TAG_DEBUG = "debug"
TAG_OPEN_TAG = "open_tag"
TAG_CLOSE_TAG = "close_tag"
TAG_OPENED_TAG = "opened_tag"
TAG_CLOSED_TAG = "closed_tag"
TAG_FULL_TIME = "full_time"
TAG_DELAY = "delay"
TAG_MIN_VAL = "min_val"
TAG_MAX_VAL = "max_val"
TAG_PERIOD = "period"
TAG_TAG = "tag"

# Ключи в конфиге
CONFIG_TAGS_OUT = "tags_out"
CONFIG_TAGS_IN = "tags_in"
CONFIG_SIGNALS = "signals"

# Ключи в сценарии
SCENARIO_NAME = "name"
SCENARIO_STEPS = "steps"
STEP_OBJECT = "object"
STEP_METHOD = "method"
STEP_TAG = "tag"
STEP_VALUE = "value"
STEP_CONFIRM = "confirm"

# Типы сигналов
SIGNAL_TYPE_SENSOR = "SensorSignal"
SIGNAL_TYPE_ENGINE = "EngineSignal"
SIGNAL_TYPE_VALVE = "ValveSignal"
SIGNAL_TYPE_DELAY = "DelaySignal"
SIGNAL_TYPE_EXPRESSION = "ExpressionSignal"

# Типы данных OPC
OPC_TYPE_BOOL = "BOOL"
OPC_TYPE_BYTE = "BYTE"
OPC_TYPE_WORD = "WORD"
OPC_TYPE_INT = "INT"
OPC_TYPE_DINT = "DINT"
OPC_TYPE_REAL = "REAL"
OPC_TYPE_TIME = "TIME"

# Helper object
HELPER_OBJECT = "h"
OPC_OBJECT = "opc"

# Helper methods
HELPER_CONFIRM = "confirm"
HELPER_LOG = "log"
HELPER_WAIT = "wait"
HELPER_ACTION = "action"
HELPER_SUCCESS = "success"
HELPER_WARNING = "warning"
HELPER_ERROR = "error"

# OPC methods
OPC_WRITE = "write"

# Режимы отладки
DEBUG_SIGN_PREFIX = "🔍"
DEBUG_LOG_INTERVAL = 10

# =============================================================================
# Runtime constants
# =============================================================================
RT_START_DELAY = 3.0
RT_DEFAULT_DT = 0.1
RT_THREAD_JOIN_TIMEOUT = 2.0
RT_SLEEP_CORRECTION = 0.001

# =============================================================================
# OPC Client constants
# =============================================================================
# Таймауты
OPC_TIMEOUT_S = 5.0
OPC_RECONNECT_ATTEMPTS = 5
OPC_RECONNECT_DELAY = 2.0
OPC_AUTO_RECONNECT = True

# Диапазоны для числовых типов
INT16_MIN = -32768
INT16_MAX = 32767

# Параметры подписки
OPC_SUBSCRIPTION_INTERVAL_MS = 100