"""Async client for the public JSON-RPC API of a Massa node."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from ..const import REQUEST_TIMEOUT
from .errors import MassaApiError


@dataclass(slots=True)
class CycleInfo:
    """Production statistics of the address for one cycle."""

    cycle: int
    is_final: bool
    ok_count: int
    nok_count: int
    active_rolls: int | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CycleInfo:
        return cls(
            cycle=int(data.get("cycle", 0)),
            is_final=bool(data.get("is_final", False)),
            ok_count=int(data.get("ok_count", 0)),
            nok_count=int(data.get("nok_count", 0)),
            active_rolls=data.get("active_rolls"),
        )


@dataclass(slots=True)
class AddressInfo:
    """Information about a wallet address."""

    address: str
    final_balance: float
    final_roll_count: int
    candidate_balance: float
    candidate_roll_count: int
    deferred_credits: float
    cycle_infos: list[CycleInfo] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AddressInfo:
        deferred = sum(
            float(credit.get("amount", 0)) for credit in data.get("deferred_credits") or []
        )
        return cls(
            address=data["address"],
            final_balance=float(data.get("final_balance", 0)),
            final_roll_count=int(data.get("final_roll_count", 0)),
            candidate_balance=float(data.get("candidate_balance", 0)),
            candidate_roll_count=int(data.get("candidate_roll_count", 0)),
            deferred_credits=deferred,
            cycle_infos=[CycleInfo.from_dict(c) for c in data.get("cycle_infos") or []],
        )


@dataclass(slots=True)
class NodeStatus:
    """Subset of the node status we care about."""

    node_id: str | None
    version: str | None
    current_cycle: int | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NodeStatus:
        cycle = data.get("current_cycle")
        return cls(
            node_id=data.get("node_id"),
            version=data.get("version"),
            current_cycle=int(cycle) if cycle is not None else None,
        )


class NodeApi:
    """Client of the Massa node public API (JSON-RPC over HTTP)."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int) -> None:
        self._session = session
        self._url = f"http://{host}:{port}/"
        self._request_id = 0

    async def _call(self, method: str, params: list[Any] | None = None) -> Any:
        self._request_id += 1
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": self._request_id, "method": method}
        if params is not None:
            payload["params"] = params
        try:
            async with self._session.post(
                self._url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                response.raise_for_status()
                body = await response.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise MassaApiError(f"Error calling {method} on {self._url}: {err}") from err

        if not isinstance(body, dict):
            raise MassaApiError(f"Unexpected response to {method}: {body!r}")
        if body.get("error"):
            raise MassaApiError(f"Node returned an error for {method}: {body['error']}")
        return body.get("result")

    async def get_status(self) -> NodeStatus:
        """Return the node status, raise MassaApiError if the node is unreachable."""
        result = await self._call("get_status")
        return NodeStatus.from_dict(result or {})

    async def get_address(self, address: str) -> AddressInfo | None:
        """Return information about a wallet address, or None if unknown."""
        result = await self._call("get_addresses", [[address]])
        if not result:
            return None
        return AddressInfo.from_dict(result[0])
