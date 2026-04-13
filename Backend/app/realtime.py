from __future__ import annotations

import asyncio

import socketio

from app.config import settings

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*' if settings.allow_all_cors_origins else list(settings.cors_origins),
    logger=False,
    engineio_logger=False,
)


async def emit_event(name: str, payload: dict) -> None:
    await sio.emit(name, payload)


def emit_nowait(name: str, payload: dict) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(emit_event(name, payload))


def mount(app):
    return socketio.ASGIApp(sio, other_asgi_app=app)
