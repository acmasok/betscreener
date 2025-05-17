import asyncio
import websockets
import json
from datetime import datetime, UTC


async def connect_to_websocket():
    uri = "wss://ru-ws.sporthub.bet:444/api/tree_ws/v1"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"[{datetime.now(UTC)}] Connected to WebSocket")

            # Слушаем сообщения в бесконечном цикле
            while True:
                try:
                    # Получаем сообщение
                    message = await websocket.recv()
                    print(f"Raw type: {type(message)}")
                    print(f"Raw bytes: {message[:50]!r}")

                    # Пытаемся распарсить JSON
                    try:
                        data = json.loads(message)
                        print(f"[{datetime.now(UTC)}] Received data:", data)
                    except json.JSONDecodeError:
                        print(f"[{datetime.now(UTC)}] Received raw message:", message)

                except websockets.ConnectionClosed:
                    print(f"[{datetime.now(UTC)}] Connection closed")
                    break
                except Exception as e:
                    print(f"[{datetime.now(UTC)}] Error:", str(e))
                    break

    except Exception as e:
        print(f"[{datetime.now(UTC)}] Connection error:", str(e))


# Функция для отправки сообщений
async def send_message(websocket, message):
    try:
        await websocket.send(json.dumps(message))
        print(f"[{datetime.now(UTC)}] Sent message:", message)
    except Exception as e:
        print(f"[{datetime.now(UTC)}] Error sending message:", str(e))


# Запуск клиента
if __name__ == "__main__":
    print(f"[{datetime.now(UTC)}] Starting WebSocket client...")

    # Установка event loop
    asyncio.get_event_loop().run_until_complete(connect_to_websocket())