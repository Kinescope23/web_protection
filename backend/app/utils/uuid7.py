import time
import secrets


def get_uuid7() -> str:
    """
    Генерирует UUID версии 7 в стандартном формате с дефисами.
    Обходит ограничение Python 3.11 на version > 5 путем ручного форматирования.
    Пример: 0190a1b2-3c4d-7e5f-8a9b-0c1d2e3f4a5b
    """
    # 1. Текущий timestamp в миллисекундах (48 бит)
    timestamp_ms = int(time.time() * 1000)

    # 2. 74 случайных бита
    rand_bytes = secrets.token_bytes(10)
    rand_int = int.from_bytes(rand_bytes, "big") & ((1 << 74) - 1)

    # 3. Собираем 128-битное число
    # [48 бит timestamp][4 бит version=7][12 бит rand_a][2 бит variant=10][62 бит rand_b]
    uuid_int = (
        (timestamp_ms & 0xFFFFFFFFFFFF) << 80
        | (0x7 << 76)
        | (rand_int & 0xFFFFFFFFFFFFFFFFFFFF)
    )

    # 4. Устанавливаем variant bits (10xx в двоичной, что дает 8, 9, a или b в hex)
    uuid_int = (uuid_int & ~(0xC0 << 56)) | (0x80 << 56)

    # 5. Форматируем как 32-символьную hex-строку и расставляем дефисы (8-4-4-4-12)
    hex_str = f"{uuid_int:032x}"
    return f"{hex_str[0:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:32]}"
