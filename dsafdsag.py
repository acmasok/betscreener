from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

import websockets


class BetBoomWebSocket:
    """WebSocket client for BetBoom sports data.

    Attributes:
        _WS_URL: WebSocket endpoint URL
        _HEADERS: Required connection headers
    """

    _WS_URL = "wss://ru-ws.sporthub.bet:444/api/tree_ws/v1"
    _HEADERS = {
        "Origin": "https://betboom.ru",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        ),
        "Sec-WebSocket-Protocol": "protobuf",
        "Sec-WebSocket-Version": "13",
        "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
    }

    def __init__(self) -> None:
        """Initialize WebSocket client."""
        self._ws = None
        self._last_message: Optional[Dict[str, Any]] = None

    async def connect(self) -> None:
        """Establish WebSocket connection.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            self._ws = await websockets.connect(
                self._WS_URL,
                extra_headers=self._HEADERS,  # Используем extra_headers вместо headers
                ping_interval=30,
                ping_timeout=10,
            )
            await self._subscribe()
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}") from e

    # Остальной код остается без изменений
    async def _subscribe(self) -> None:
        """Subscribe to sports data updates."""
        if not self._ws:
            return

        subscribe_msg = {
            "type": "subscribe",
            "data": {"sport_id": 1}  # 1 = football
        }
        await self._ws.send(str(subscribe_msg))

    async def receive_data(self) -> Dict[str, Any]:
        """Receive and parse data from WebSocket.

        Returns:
            Parsed message data

        Raises:
            ConnectionError: If connection is lost
        """
        if not self._ws:
            raise ConnectionError("Not connected")

        try:
            message = await self._ws.recv()
            self._last_message = self._parse_message(message)
            return self._last_message
        except Exception as e:
            raise ConnectionError(f"Failed to receive data: {e}") from e

    def _parse_message(self, message: str | bytes) -> Dict[str, Any]:
        """Parse received message.

        Args:
            message: Raw message from WebSocket

        Returns:
            Parsed message data
        """
        if isinstance(message, bytes):
            return {"type": "binary", "size": len(message)}
        return {"type": "text", "data": message}


async def main() -> None:
    """Example usage of BetBoom WebSocket client."""
    client = BetBoomWebSocket()
    try:
        await client.connect()
        while True:
            data = await client.receive_data()
            print(f"[{datetime.utcnow().isoformat()}] Received: {data}")
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if client._ws:
            await client._ws.close()


if __name__ == "__main__":
    asyncio.run(main())