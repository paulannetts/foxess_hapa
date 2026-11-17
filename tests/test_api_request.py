"""
Tests for FoxessHapaApiClient._api_request against a local fake FoxESS server.

Requests go over real HTTP to an aiohttp test server, so the client's aiohttp
calls, signing headers and error mapping are exercised end to end.
"""

from __future__ import annotations

import asyncio
import hashlib
import socket
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from custom_components.foxess_hapa import api
from custom_components.foxess_hapa.api import (
    FoxessHapaApiClient,
    FoxessHapaApiClientAuthenticationError,
    FoxessHapaApiClientCommunicationError,
    FoxessHapaApiClientError,
)

DETAIL_PATH = "/op/v1/device/detail"
REAL_PATH = "/op/v1/device/real/query"

# The Home Assistant pytest plugin blocks sockets; these tests talk to a real
# local server on purpose.
pytestmark = pytest.mark.usefixtures("socket_enabled")


@dataclass
class Reply:
    """What the fake server answers with."""

    status: int = 200
    payload: Any = field(default_factory=lambda: {"errno": 0, "result": {}})
    text: str | None = None  # sent as text/html instead of the JSON payload
    delay: float = 0


@dataclass
class Seen:
    """A request as the fake server received it."""

    method: str
    path: str
    query: dict[str, str]
    headers: dict[str, str]
    body: bytes


def _request(
    reply: Reply,
    method: str,
    path: str,
    data: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[Seen]]:
    """Send one _api_request to a fake server; return the result and requests."""
    seen: list[Seen] = []

    async def handler(request: web.Request) -> web.StreamResponse:
        seen.append(
            Seen(
                request.method,
                request.path,
                dict(request.query),
                dict(request.headers),
                await request.read(),
            )
        )
        if reply.delay:
            await asyncio.sleep(reply.delay)
        if reply.text is not None:
            return web.Response(
                status=reply.status, text=reply.text, content_type="text/html"
            )
        return web.json_response(reply.payload, status=reply.status)

    async def _run() -> dict[str, Any]:
        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", handler)
        async with TestServer(app) as server, aiohttp.ClientSession() as session:
            client = FoxessHapaApiClient("SN123", "my-key", session)
            client.BASE_URL = f"http://{server.host}:{server.port}"
            return await client._api_request(method, path, data)

    return asyncio.run(_run()), seen


def _request_with_failing_session(exception: BaseException) -> None:
    """Send one _api_request through a session whose POST raises `exception`."""
    session = MagicMock()
    session.post = AsyncMock(side_effect=exception)
    client = FoxessHapaApiClient("SN123", "my-key", session)
    asyncio.run(client._api_request("POST", REAL_PATH, {}))


# --- success, GET vs POST ----------------------------------------------------


def test_get_returns_result_without_body() -> None:
    """A GET returns the parsed response, keeps its query and sends no body."""
    reply = Reply(payload={"errno": 0, "result": {"deviceSN": "SN123"}})

    result, seen = _request(reply, "GET", f"{DETAIL_PATH}?sn=SN123")

    assert result == {"errno": 0, "result": {"deviceSN": "SN123"}}
    assert len(seen) == 1
    assert seen[0].method == "GET"
    assert seen[0].path == DETAIL_PATH
    assert seen[0].query == {"sn": "SN123"}
    assert seen[0].body == b""


def test_post_sends_json_body() -> None:
    """A POST sends the data as a JSON body."""
    _, seen = _request(Reply(), "POST", REAL_PATH, {"sns": ["SN123"]})

    assert seen[0].method == "POST"
    assert seen[0].headers["Content-Type"] == "application/json"
    assert seen[0].body == b'{"sns": ["SN123"]}'


def test_signature_uses_path_without_query() -> None:
    """The signature covers the path only; the query string is left out."""
    _, seen = _request(Reply(), "GET", f"{DETAIL_PATH}?sn=SN123")

    headers = seen[0].headers
    expected = hashlib.md5(  # noqa: S324
        rf"{DETAIL_PATH}\r\nmy-key\r\n{headers['timestamp']}".encode()
    ).hexdigest()
    assert headers["signature"] == expected
    assert headers["token"] == "my-key"


# --- errors ------------------------------------------------------------------


@pytest.mark.parametrize("status", [401, 403])
def test_unauthorized_status_is_auth_error(status: int) -> None:
    """401 and 403 mean the API key is wrong."""
    with pytest.raises(FoxessHapaApiClientAuthenticationError):
        _request(Reply(status=status, payload={}), "POST", REAL_PATH, {})


def test_errno_is_api_error_with_message() -> None:
    """A non-zero errno raises a plain API error carrying the API's message."""
    reply = Reply(payload={"errno": 40257, "msg": "Params error"})

    with pytest.raises(FoxessHapaApiClientError, match="Params error") as exc:
        _request(reply, "POST", REAL_PATH, {})
    assert type(exc.value) is FoxessHapaApiClientError


@pytest.mark.parametrize("msg", ["Illegal token", "Auth failed"])
def test_errno_with_token_or_auth_is_auth_error(msg: str) -> None:
    """A non-zero errno about the token or auth is an authentication error."""
    reply = Reply(payload={"errno": 40256, "msg": msg})

    with pytest.raises(FoxessHapaApiClientAuthenticationError, match=msg):
        _request(reply, "POST", REAL_PATH, {})


def test_http_error_status_is_communication_error() -> None:
    """Other HTTP error statuses (raise_for_status) are communication errors."""
    with pytest.raises(FoxessHapaApiClientCommunicationError):
        _request(Reply(status=500), "POST", REAL_PATH, {})


def test_non_json_error_page_is_communication_error() -> None:
    """An HTML error page (not JSON) is a communication error."""
    reply = Reply(status=502, text="<html>Bad Gateway</html>")

    with pytest.raises(FoxessHapaApiClientCommunicationError):
        _request(reply, "POST", REAL_PATH, {})


def test_timeout_is_communication_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A server slower than the request timeout is a communication error."""
    real_timeout = asyncio.timeout
    monkeypatch.setattr(
        api,
        "asyncio",
        SimpleNamespace(timeout=lambda _: real_timeout(0.05), sleep=asyncio.sleep),
    )

    with pytest.raises(FoxessHapaApiClientCommunicationError, match="Timeout"):
        _request(Reply(delay=1), "POST", REAL_PATH, {})


def test_connection_refused_is_communication_error() -> None:
    """A server that refuses the connection is a communication error."""
    with socket.socket() as sock:  # find a free port, then leave it closed
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    async def _run() -> None:
        async with aiohttp.ClientSession() as session:
            client = FoxessHapaApiClient("SN123", "my-key", session)
            client.BASE_URL = f"http://127.0.0.1:{port}"
            await client._api_request("POST", REAL_PATH, {})

    with pytest.raises(FoxessHapaApiClientCommunicationError):
        asyncio.run(_run())


@pytest.mark.parametrize(
    "exception",
    [
        aiohttp.ClientConnectionError("connection reset"),
        socket.gaierror("name resolution failed"),
    ],
    ids=["client-error", "gaierror"],
)
def test_transport_failures_are_communication_errors(
    exception: Exception,
) -> None:
    """Aiohttp client errors and DNS failures are communication errors."""
    with pytest.raises(FoxessHapaApiClientCommunicationError):
        _request_with_failing_session(exception)


# --- rate limiting -----------------------------------------------------------


def _rate_limit(
    monkeypatch: pytest.MonkeyPatch, last_call: float, times: list[float]
) -> tuple[AsyncMock, FoxessHapaApiClient]:
    """Run _rate_limit with time.time returning `times` in turn."""
    sleep = AsyncMock()
    clock = iter(times)
    monkeypatch.setattr(api, "time", SimpleNamespace(time=lambda: next(clock)))
    monkeypatch.setattr(api, "asyncio", SimpleNamespace(sleep=sleep))
    client = FoxessHapaApiClient("SN123", "my-key", session=None)  # type: ignore[arg-type]
    client._last_api_call = last_call
    asyncio.run(client._rate_limit())
    return sleep, client


def test_rate_limit_waits_when_calls_are_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A call 0.3 s after the last one waits out the second, plus 0.2 s."""
    sleep, client = _rate_limit(monkeypatch, 100.0, [100.3, 101.2])

    sleep.assert_awaited_once()
    assert sleep.await_args is not None
    assert sleep.await_args.args[0] == pytest.approx(0.9)
    assert client._last_api_call == 101.2


@pytest.mark.parametrize("last_call", [0, 98.5], ids=["first-call", "1.5s-later"])
def test_rate_limit_does_not_wait(
    monkeypatch: pytest.MonkeyPatch, last_call: float
) -> None:
    """The first call, or one at least a second after the last, goes at once."""
    sleep, client = _rate_limit(monkeypatch, last_call, [100.0, 100.0])

    sleep.assert_not_awaited()
    assert client._last_api_call == 100.0
