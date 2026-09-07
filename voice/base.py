"""Contrato de los motores de sintesis de voz."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSEngine(Protocol):
    """Dice un texto en voz alta.

    decir() bloquea hasta terminar de hablar: la maquina de estados necesita
    saber cuando cerrar el gate half-duplex y volver a escuchar (PLAN.md §5.4).
    """

    async def decir(self, texto: str) -> None: ...
