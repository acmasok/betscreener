import asyncio

import websockets
import asyncio
import logging
from typing import Optional
from forkscan.parsers.betboomtest.market_betstats_ws_pb2 import (
    MainRequest,
    MainResponse,
    SubscribeRequest,
    PingRequest,
)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def subscribe_match_market(
    url: str, match_id: int, uid: str, token: Optional[str] = None
) -> None:
    """Подключается по WebSocket и подписывается на обновления рынка.

    Args:
        url (str): URL WebSocket-сервера.
        match_id (int): Идентификатор матча.
        uid (str): Уникальный идентификатор подписки.
        token (str, optional): Если сервер требует токен — можно расширить
            MainRequest.SubscribeRequest, добавив поле token.
    """
    # Обязательно указываем протокол, который «ждёт» сервер
    headers = {
        "Origin": "https://betboom.ru",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    async with websockets.connect(
        url,
        additional_headers=headers,
        subprotocols=["protobuf"],  # <-- ключевая правка!
    ) as ws:
        logger.info("Connected to %s, negotiated subprotocol=%r", url, ws.subprotocol)

        # 1) Сформируем protobuf-запрос на подписку
        req = MainRequest(
            subscribe_match_market=SubscribeRequest(
                match_id=match_id,
                uid=uid,
            )
        )
        raw = req.SerializeToString()
        logger.debug("Sending %d-byte SubscribeRequest", len(raw))
        await ws.send(raw)

        # 2) Запускаем приём и разбор
        async for frame in ws:
            # Сервер шлёт только бинарные фреймы
            if not isinstance(frame, (bytes, bytearray)):
                logger.warning("Unexpected text frame: %r", frame)
                continue

            logger.debug("Received %d-byte frame", len(frame))
            resp = MainResponse()
            try:
                resp.ParseFromString(frame)
            except Exception as error:
                logger.error("Failed to parse MainResponse: %s", error, exc_info=True)
                continue

            message_type = resp.WhichOneof("type")
            if message_type is None:
                logger.warning("Response without type: %r", resp)
                continue

            # Обработка
            if message_type == "subscribe_match_market":
                info = resp.subscribe_match_market
                logger.info(
                    "Subscribed: code=%d, status=%r", info.code, info.status
                )
            elif message_type == "betstats_changed":
                stats = resp.betstats_changed
                logger.info("Betstats changed: %r", stats)
            elif message_type == "betstats_outcome_changed":
                outcome = resp.betstats_outcome_changed
                logger.info("Outcome changed: %r", outcome)
            elif message_type == "ping":
                ping = resp.ping
                logger.debug("PING (server heartbeat): uuid=%r", ping.uuid)
            else:
                payload = getattr(resp, message_type)
                logger.info("Other message (%s): %r", message_type, payload)


def main() -> None:
    """Точка входа: URL, match_id, uid."""
    url = "wss://ru-ws.sporthub.bet:444/api/tree_ws/v1"
    match_id = 1981261
    uid = "IFqWW-829cff75"

    asyncio.run(subscribe_match_market(url, match_id, uid))


if __name__ == "__main__":
    main()
