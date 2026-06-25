## Virtual XK

Программа эмулирующая работы платы ХК



## Требование

- python 3.14+
- pyserial
- uv 


## Быстрый старт

```
# 1. Клонирование репозитория
git clone https://github.com/rodnaxel/virtual-xk.git
cd virtual-xk

# 2. Устанавливаем uv (https://github.com/astral-sh/uv)

# 3. Установка зависимостей
uv sync --frozen

# 4. Запуск программы
uv run main.py --port /dev/ttyV1 --csv data/M1_2.csv --rows 600
```

## Параметры

| Параметр | По умолчанию | Описание |
|---|---|---|
| `port` | — | COM-порт (`COM3`, `/dev/ttyUSB0`) |
| `--baudreate` | `9600` | Скорость соединения |
| `--csv` | — | Путь к CSV-файлу c данными |
| `--rows` | — | Количество строк для считывания с файла данных |
