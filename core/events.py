"""
Contratos de eventos entre las capas de Jarvis.

Este archivo es la costura del sistema: ears/ publica, brain/ consume, y
ninguno importa modulos del otro. Cambiarlo tiene efectos en cascada, asi
que va en su propio commit y no mezclado con una feature (PLAN.md §7.5).

Los eventos son inmutables a proposito: un evento describe algo que ya
paso, y ningun handler deberia poder alterarlo para los siguientes.
"""

import time
from dataclasses import dataclass, field
from typing import Literal


def _ahora() -> float:
    """Marca temporal del evento, en segundos desde la epoca."""
    return time.time()


@dataclass(frozen=True)
class WakeDetected:
    """Algo activo a Jarvis: una palmada doble o la wake word."""

    source: Literal["clap", "wakeword"]
    confidence: float
    timestamp: float = field(default_factory=_ahora)


@dataclass(frozen=True)
class ListeningStarted:
    """Jarvis empezo a grabar la orden del usuario."""

    timestamp: float = field(default_factory=_ahora)


@dataclass(frozen=True)
class SpeechTranscribed:
    """Lo que dijo el usuario, ya convertido a texto."""

    text: str
    language: str
    duration_s: float
    timestamp: float = field(default_factory=_ahora)


@dataclass(frozen=True)
class SpeakRequested:
    """Pedido de decir algo en voz alta.

    interruptible=False para confirmaciones cortas que no vale la pena cortar.
    """

    text: str
    interruptible: bool = True
    timestamp: float = field(default_factory=_ahora)


@dataclass(frozen=True)
class SpeakFinished:
    """Jarvis termino de hablar. Cierra el gate half-duplex (PLAN.md §5.4)."""

    timestamp: float = field(default_factory=_ahora)


@dataclass(frozen=True)
class StateChanged:
    """Transicion de la maquina de estados. Lo consume la interfaz."""

    old: str
    new: str
    timestamp: float = field(default_factory=_ahora)


@dataclass(frozen=True)
class ErrorOccurred:
    """Algo fallo. 'where' es el modulo, en formato 'paquete.modulo'."""

    where: str
    message: str
    timestamp: float = field(default_factory=_ahora)


Event = (
    WakeDetected
    | ListeningStarted
    | SpeechTranscribed
    | SpeakRequested
    | SpeakFinished
    | StateChanged
    | ErrorOccurred
)
