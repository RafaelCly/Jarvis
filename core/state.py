"""
Maquina de estados de Jarvis (PLAN.md §5.4).

El diagrama de transiciones vive aca y en ningun otro lado: si un modulo
necesita saber "puedo escuchar ahora", pregunta, no deduce.
"""

from enum import Enum

from core.bus import EventBus
from core.events import StateChanged


class State(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    ACTING = "acting"
    SPEAKING = "speaking"


# Transiciones permitidas. Volver a IDLE siempre se permite: es el camino
# de recuperacion de errores desde cualquier punto del pipeline.
_TRANSICIONES: dict[State, set[State]] = {
    State.IDLE: {State.LISTENING},
    State.LISTENING: {State.TRANSCRIBING, State.IDLE},
    State.TRANSCRIBING: {State.THINKING, State.IDLE},
    State.THINKING: {State.ACTING, State.SPEAKING, State.IDLE},
    State.ACTING: {State.SPEAKING, State.IDLE},
    State.SPEAKING: {State.IDLE},
}


class StateMachine:
    """Estado global de Jarvis. Publica StateChanged en cada transicion."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._state = State.IDLE

    @property
    def state(self) -> State:
        return self._state

    @property
    def puede_escuchar(self) -> bool:
        """False mientras Jarvis habla — el gate half-duplex.

        Sin esto, el TTS sale por los parlantes, el microfono lo capta,
        la wake word se re-dispara y Jarvis entra en bucle consigo mismo.
        """
        return self._state is not State.SPEAKING

    async def transition_to(self, nuevo: State) -> None:
        """Cambia de estado. Lanza ValueError si la transicion no existe."""
        if nuevo is self._state:
            return

        if nuevo not in _TRANSICIONES[self._state]:
            raise ValueError(
                f"Transicion invalida: {self._state.value} -> {nuevo.value}"
            )

        viejo, self._state = self._state, nuevo
        await self._bus.publish(StateChanged(old=viejo.value, new=nuevo.value))
