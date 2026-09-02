"""
Bus de eventos en proceso.

Desacopla las capas: quien detecta la wake word no sabe quien transcribe,
y quien transcribe no sabe quien decide. Eso es lo que permite testear
cada pieza sola y que --text-mode inyecte texto a mitad del pipeline.
"""

import asyncio
import inspect
import logging
from collections import defaultdict
from typing import Any, Callable

log = logging.getLogger(__name__)

Handler = Callable[[Any], Any]


class EventBus:
    """Pub/sub por tipo de evento. Los handlers pueden ser sync o async."""

    def __init__(self) -> None:
        self._handlers: dict[type, list[Handler]] = defaultdict(list)
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Guarda el loop principal, necesario para publish_threadsafe()."""
        self._loop = loop

    def subscribe(self, event_type: type, handler: Handler) -> None:
        """Registra un handler para un tipo exacto de evento."""
        self._handlers[event_type].append(handler)

    async def publish(self, event: Any) -> None:
        """Entrega el evento a sus suscriptores, en orden de registro.

        Un handler que lanza excepcion se registra y se sigue con el resto:
        una falla en el TTS no debe dejar sin eventos a la interfaz.
        """
        for handler in self._handlers[type(event)]:
            try:
                resultado = handler(event)
                if inspect.isawaitable(resultado):
                    await resultado
            except Exception:
                log.exception(
                    "Handler %r falló procesando %s",
                    getattr(handler, "__name__", handler),
                    type(event).__name__,
                )

    def publish_threadsafe(self, event: Any) -> None:
        """Publica desde un hilo ajeno al loop de asyncio.

        El callback de PortAudio corre en su propio hilo, asi que ears/
        tiene que usar este metodo y no publish().
        """
        if self._loop is None:
            raise RuntimeError(
                "EventBus.bind_loop() no fue llamado; "
                "publish_threadsafe() necesita el loop principal"
            )
        asyncio.run_coroutine_threadsafe(self.publish(event), self._loop)
