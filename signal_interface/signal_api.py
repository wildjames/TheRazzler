from typing import Any, AsyncGenerator, Dict

import aiohttp
import websockets


class SignalAPI:
    def __init__(
        self,
        signal_service: str,
        phone_number: str,
    ):
        self.signal_service = signal_service
        self.phone_number = phone_number

    async def get_groups(self) -> Dict[str, Any]:
        uri = self._get_groups_uri()
        async with aiohttp.ClientSession() as session:
            resp = await session.get(uri)
            resp.raise_for_status()
            return await resp.json()

    async def receive(self) -> AsyncGenerator[Any, Any]:
        uri = self._receive_ws_uri()
        self.connection = websockets.connect(uri, ping_interval=None)
        async with self.connection as websocket:
            async for raw_message in websocket:
                yield raw_message

    async def send(
        self, receiver: str, message: str, base64_attachments: list = None
    ) -> aiohttp.ClientResponse:
        uri = self._send_rest_uri()
        if base64_attachments is None:
            base64_attachments = []
        payload = {
            "base64_attachments": base64_attachments,
            "message": message,
            "number": self.phone_number,
            "recipients": [receiver],
        }
        async with aiohttp.ClientSession() as session:
            resp = await session.post(uri, json=payload)
            resp.raise_for_status()
            return resp

    async def react(
        self, recipient: str, reaction: str, target_author: str, timestamp: int
    ) -> aiohttp.ClientResponse:
        """Arguments:
        recipient: The UUID of the recipient
        reaction: The reaction emoji
        target_author: The UUID of the author of the message
        timestamp: The timestamp of the message to react to
        """
        uri = self._react_rest_uri()
        payload = {
            "recipient": recipient,
            "reaction": reaction,
            "target_author": target_author,
            "timestamp": timestamp,
        }
        async with aiohttp.ClientSession() as session:
            resp = await session.post(uri, json=payload)
            resp.raise_for_status()
            return resp

    async def start_typing(self, receiver: str):
        uri = self._typing_indicator_uri()
        payload = {
            "recipient": receiver,
        }
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.put(uri, json=payload)
                resp.raise_for_status()
                return resp
        except (
            aiohttp.ClientError,
            aiohttp.http_exceptions.HttpProcessingError,
        ):
            raise StartTypingError

    async def stop_typing(self, receiver: str):
        uri = self._typing_indicator_uri()
        payload = {
            "recipient": receiver,
        }
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.delete(uri, json=payload)
                resp.raise_for_status()
                return resp
        except (
            aiohttp.ClientError,
            aiohttp.http_exceptions.HttpProcessingError,
        ):
            raise StopTypingError

    async def download_attachment(self, attachment_id: str) -> bytes:
        """Returns the base64 encoded attachment."""
        uri = self._download_attachment_uri(attachment_id)
        async with aiohttp.ClientSession() as session:
            async with session.get(uri) as resp:
                resp.raise_for_status()
                # The API returns the base64 encoded attachment
                return await resp.read()

    def _receive_ws_uri(self):
        return f"ws://{self.signal_service}/v1/receive/{self.phone_number}"

    def _send_rest_uri(self):
        return f"http://{self.signal_service}/v2/send"

    def _react_rest_uri(self):
        return f"http://{self.signal_service}/v1/reactions/{self.phone_number}"

    def _typing_indicator_uri(self):
        return (
            f"http://{self.signal_service}/v1/typing-indicator/"
            "{self.phone_number}"
        )

    def _download_attachment_uri(self, attachment_id: str):
        return f"http://{self.signal_service}/v1/attachments/{attachment_id}"

    def _get_groups_uri(self):
        return f"http://{self.signal_service}/v1/groups/{self.phone_number}"


class ReceiveMessagesError(Exception):
    pass


class SendMessageError(Exception):
    pass


class TypingError(Exception):
    pass


class StartTypingError(TypingError):
    pass


class StopTypingError(TypingError):
    pass


class ReactionError(Exception):
    pass
