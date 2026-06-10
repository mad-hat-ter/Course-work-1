from __future__ import annotations
from collections.abc import AsyncGenerator
from typing import Any, cast
import httpx
from aiogram.__meta__ import __version__
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods.base import TelegramType
from aiogram.types import InputFile
from typing_extensions import Self
from aiogram.client.bot import Bot
from aiogram.methods import TelegramMethod


class HttpxSession(BaseSession):
    def __init__(self, proxy: str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._proxy = proxy
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(self.timeout, connect=min(15.0, self.timeout))
            self._client = httpx.AsyncClient(
                proxy=self._proxy,
                timeout=timeout,
                follow_redirects=True,
                headers={"User-Agent": f"aiogram/{__version__}"},
            )
        return self._client

    async def _read_input_file(self, bot: Bot, input_file: InputFile) -> bytes:
        chunks: list[bytes] = []
        async for chunk in input_file.read(bot):
            chunks.append(chunk)
        return b"".join(chunks)

    async def _build_multipart(self, bot: Bot, method: TelegramMethod[TelegramType]) -> tuple[dict[str, Any], dict[str, tuple[str, bytes]] | None]:
        data: dict[str, Any] = {}
        input_files: dict[str, InputFile] = {}
        for key, value in method.model_dump(warnings=False).items():
            prepared = self.prepare_value(value, bot=bot, files=input_files)
            if not prepared:
                continue
            data[key] = prepared

        if not input_files:
            return data, None

        files: dict[str, tuple[str, bytes]] = {}
        for key, input_file in input_files.items():
            content = await self._read_input_file(bot, input_file)
            files[key] = (input_file.filename or key, content)
        return data, files

    async def make_request(self, bot: Bot, method: TelegramMethod[TelegramType], timeout: int | None = None) -> TelegramType:
        client = await self._get_client()
        url = self.api.api_url(token=bot.token, method=method.__api_method__)
        data, files = await self._build_multipart(bot, method)
        request_timeout = self.timeout if timeout is None else timeout
        try:
            response = await client.post(url, data=data, files=files, timeout=request_timeout)
        except httpx.TimeoutException as exc:
            raise TelegramNetworkError(method=method, message="Request timeout error") from exc
        except httpx.RequestError as exc:
            raise TelegramNetworkError(method=method, message=f"{type(exc).__name__}: {exc}") from exc

        parsed = self.check_response(bot=bot, method=method, status_code=response.status_code, content=response.text)
        return cast(TelegramType, parsed.result)

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:
        client = await self._get_client()
        request_headers = headers or {}
        try:
            async with client.stream("GET", url, headers=request_headers, timeout=timeout) as response:
                if raise_for_status:
                    response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size):
                    yield chunk
        except httpx.TimeoutException as exc:
            raise TelegramNetworkError(method=None, message="Request timeout error") from exc
        except httpx.RequestError as exc:
            raise TelegramNetworkError(method=None, message=f"{type(exc).__name__}: {exc}") from exc

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> Self:
        await self._get_client()
        return self
