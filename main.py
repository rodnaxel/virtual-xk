import argparse
import csv
import itertools

import threading
import time
import logging

from typing import Iterator

import serial


logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(description="Virtual XK Board emulator")
    parser.add_argument("--port", type=str, required=True, help="Port to connect to")
    parser.add_argument(
        "--baudrate",
        type=int,
        default=115200,
        help="Baud rate for serial communication",
    )
    parser.add_argument(
        "--csv", type=str, required=True, help="Path to the CSV data file"
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=100,
        help="Number of rows for reading from csv data file",
    )
    return parser.parse_args()


def read_csv_data(csv_file: str, num_rows: int) -> Iterator[dict]:
    """Чтение данных из CSV файла и возврат итератора по строкам данных."""
    data = []
    with open(csv_file, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            if i >= num_rows:
                break
            data.append(row)

    if not data:
        logger.warning("No data read from CSV file.")
    logger.info(f"Read {len(data)} rows from CSV file: {csv_file}")

    return itertools.cycle(data)


class SerialListener(threading.Thread):
    """Класс для эмуляции прослушивания порта."""

    def __init__(self, port: str, baudrate: int, csv_iter: Iterator[dict]):
        super().__init__(daemon=True)
        self._port = port
        self._baudrate = baudrate
        
        self._csv_iter = csv_iter

        self._stop_event = threading.Event()

        self._serial = None

    def run(self):
        try:
            self._serial = serial.Serial(self._port, self._baudrate, timeout=0.1)
        except serial.SerialException as e:
            logger.error(f"Failed to open serial port {self._port}: {e}")
            return
        
        try:
            while not self._stop_event.is_set():
                # Чтение пакета 
                packet = self._read_packet()
                if packet is None:
                    continue
                # Валидация пакета
                # Обработка пакета
                parsed_data = self.parse_packet(packet)
                
                # Формирование ответа на основе данных из CSV
                csv_row = next(self._csv_iter)
                print(f"Using CSV row: {csv_row.get("glub")}")
                response = self.create_response(parsed_data, csv_row)
                
                # Отправка ответа обратно в последовательный порт
                self._serial.write(response)
                
                # Логирование отправленного ответа
                #logger.debug(f"Sent response: {created_response.hex()}")              
        finally:
            if self._serial and self._serial.is_open:
                self._serial.close()
                logger.info(f"Serial port {self._port} closed.")
            
    def stop(self):
        self._stop_event.set()
        
    def _read_packet(self) -> bytes | None:
        """Чтение пакета данных из последовательного порта."""
        data = self._serial.read(packet_size := 15)
        if len(data) < packet_size:
            return None
        logger.debug(f"Received packet: {len(data)} : {data.hex()}")
        return data
    
    def parse_packet(self, packet: bytes) -> dict:
        """Парсинг пакета данных и возврат словаря с данными."""
        parsed_data = {
            "SOP": packet[0],
            "ID": packet[1],
            "mode": packet[2],
            "depth_range": packet[3],
            "TGA ratio A": packet[4],
            "gain": packet[5],
            "TGA ratio B": packet[6],
            "reverb timeout": packet[7],
            "TGA table": packet[8],
            "sound speed": packet[9] << 8 | packet[10],
        }
        logger.debug(f"Parsed packet data: {parsed_data}")
        return parsed_data
    
    def create_response(self, parsed_data: dict, csv_row: dict) -> bytes:
        """Создание ответа на основе данных из CSV."""
        
        response = bytearray(134)
        response[0] = parsed_data["SOP"]  
        response[1] = parsed_data["depth_range"]  
        
        response[2] = parsed_data["gain"]  
        response[3] = 0         # число коррелированных стопов
        response[4] = 0         # число принятых стопов
        response[5] = 0x00      # резерв
        
        depth = int(csv_row.get("glub"))
        response[6] = (depth >> 8) & 0xff  # старший байт глубины
        response[7] = depth & 0xff         # младший байт глубины
        
        amplitude = int(csv_row.get("ampl"))
        response[8] = (amplitude >> 8) & 0xff  # старший байт амплитуды
        response[9] = amplitude & 0xff         # младший байт амплитуды
        
        duration = int(float(csv_row.get("lenth")))
        response[10] = (duration >> 8) & 0xff  # старший байт длительности
        response[11] = duration & 0xff         # младший байт длительности
        
        # Заполнение точек глубины и амплитуды
        for i in range(12, 132):
            response[i] = 0x00  # резервные байты
        
        response[132] = 0x0d  # резерв
        response[133] = 0x0a  # резерв
        
        logger.debug(f"Created response from CSV data: {response.hex()}")
        return bytes(response)
    
def main():
    args = parse_args()
    print(f"Connecting to port: {args.port} with baudrate: {args.baudrate}")
    print(f"Reading data from CSV file: {args.csv} with {args.rows} rows")

    data_iter = read_csv_data(args.csv, args.rows)

    serial_listener = SerialListener(args.port, args.baudrate, data_iter)
    serial_listener.start()
    
    
    try:
        while serial_listener.is_alive():
            serial_listener.join(timeout=0.5)

    except KeyboardInterrupt:
        serial_listener.stop()
        serial_listener.join()
        print("Stopping the emulator.")


if __name__ == "__main__":
    main()
