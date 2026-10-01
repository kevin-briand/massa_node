"""Async client for the Bitget public market API (MAS price)."""

from __future__ import annotations

import asyncio

import aiohttp

from ..const import REQUEST_TIMEOUT
from .errors import MassaApiError


class BitgetApi:
    """Fetch the MAS/USDT price from bitget.com."""

    _URL = "https://api.bitget.com/api/v2/spot/market/tickers"

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def get_massa_price(self) -> float:
        """Return the last MAS/USDT price, raise MassaApiError on failure."""
        try:
            async with self._session.get(
                self._URL,
                params={"symbol": "MASUSDT"},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                response.raise_for_status()
                body = await response.json(content_type=None)
            return float(body["data"][0]["lastPr"])
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise MassaApiError(f"Cannot fetch MAS price: {err}") from err
        except (KeyError, IndexError, TypeError) as err:
            raise MassaApiError(f"Unexpected Bitget response: {err}") from err
