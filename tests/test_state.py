import pytest

from core.bus import EventBus
from core.events import StateChanged
from core.state import State, StateMachine


async def test_arranca_en_idle():
    assert StateMachine(EventBus()).state is State.IDLE


async def test_transicion_valida_cambia_el_estado():
    maquina = StateMachine(EventBus())
    await maquina.transition_to(State.LISTENING)
    assert maquina.state is State.LISTENING


async def test_transicion_invalida_lanza_error():
    # IDLE -> SPEAKING no existe: hay que pasar por el pipeline.
    maquina = StateMachine(EventBus())
    with pytest.raises(ValueError, match="idle"):
        await maquina.transition_to(State.SPEAKING)


async def test_publica_state_changed_al_transicionar():
    bus = EventBus()
    cambios = []
    bus.subscribe(StateChanged, lambda e: cambios.append(e))

    await StateMachine(bus).transition_to(State.LISTENING)

    assert len(cambios) == 1
    assert (cambios[0].old, cambios[0].new) == ("idle", "listening")


async def test_no_puede_escuchar_mientras_habla():
    # El gate half-duplex: sin esto Jarvis se oye a si mismo y entra en bucle.
    maquina = StateMachine(EventBus())
    for estado in (
        State.LISTENING,
        State.TRANSCRIBING,
        State.THINKING,
        State.ACTING,
        State.SPEAKING,
    ):
        await maquina.transition_to(estado)

    assert maquina.state is State.SPEAKING
    assert maquina.puede_escuchar is False


async def test_puede_escuchar_al_volver_a_idle():
    maquina = StateMachine(EventBus())
    assert maquina.puede_escuchar is True


async def test_desde_cualquier_estado_se_puede_volver_a_idle():
    # La recuperacion de errores siempre aterriza en IDLE.
    maquina = StateMachine(EventBus())
    await maquina.transition_to(State.LISTENING)
    await maquina.transition_to(State.IDLE)
    assert maquina.state is State.IDLE


async def test_thinking_puede_saltar_acting_y_hablar_directo():
    # Una respuesta que no ejecuta ninguna skill (un "no entendi") va
    # directo a SPEAKING sin pasar por ACTING.
    maquina = StateMachine(EventBus())
    await maquina.transition_to(State.LISTENING)
    await maquina.transition_to(State.TRANSCRIBING)
    await maquina.transition_to(State.THINKING)
    await maquina.transition_to(State.SPEAKING)

    assert maquina.state is State.SPEAKING


async def test_transicionar_al_mismo_estado_no_publica_nada():
    bus = EventBus()
    cambios = []
    bus.subscribe(StateChanged, lambda e: cambios.append(e))
    maquina = StateMachine(bus)

    await maquina.transition_to(State.IDLE)

    assert cambios == []
