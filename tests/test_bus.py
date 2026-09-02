import asyncio
import threading

from core.bus import EventBus
from core.events import SpeakRequested, SpeechTranscribed, WakeDetected


async def test_el_handler_recibe_el_evento_al_que_se_suscribio():
    bus = EventBus()
    recibidos = []
    bus.subscribe(SpeechTranscribed, lambda e: recibidos.append(e))

    await bus.publish(SpeechTranscribed(text="hola", language="es", duration_s=1.0))

    assert len(recibidos) == 1
    assert recibidos[0].text == "hola"


async def test_no_recibe_eventos_de_otro_tipo():
    bus = EventBus()
    recibidos = []
    bus.subscribe(SpeechTranscribed, lambda e: recibidos.append(e))

    await bus.publish(SpeakRequested(text="hola"))

    assert recibidos == []


async def test_varios_handlers_del_mismo_evento_reciben_todos():
    bus = EventBus()
    a, b = [], []
    bus.subscribe(SpeakRequested, lambda e: a.append(e))
    bus.subscribe(SpeakRequested, lambda e: b.append(e))

    await bus.publish(SpeakRequested(text="hola"))

    assert len(a) == 1 and len(b) == 1


async def test_acepta_handlers_asincronos():
    bus = EventBus()
    recibidos = []

    async def handler(evento):
        await asyncio.sleep(0)
        recibidos.append(evento)

    bus.subscribe(SpeakRequested, handler)
    await bus.publish(SpeakRequested(text="hola"))

    assert len(recibidos) == 1


async def test_un_handler_que_revienta_no_impide_a_los_demas():
    # Si el TTS falla, la interfaz tiene que seguir recibiendo eventos.
    bus = EventBus()
    sobrevivientes = []

    def handler_roto(evento):
        raise RuntimeError("boom")

    bus.subscribe(SpeakRequested, handler_roto)
    bus.subscribe(SpeakRequested, lambda e: sobrevivientes.append(e))

    await bus.publish(SpeakRequested(text="hola"))  # no debe propagar

    assert len(sobrevivientes) == 1


async def test_publicar_sin_suscriptores_no_falla():
    await EventBus().publish(SpeakRequested(text="nadie escucha"))


async def test_publish_threadsafe_entrega_desde_otro_hilo():
    # El callback de PortAudio corre fuera del loop de asyncio: sin esto,
    # ears/ no podria publicar nada.
    bus = EventBus()
    bus.bind_loop(asyncio.get_running_loop())
    recibidos = []
    bus.subscribe(WakeDetected, lambda e: recibidos.append(e))

    def desde_otro_hilo():
        bus.publish_threadsafe(WakeDetected(source="clap", confidence=1.0))

    hilo = threading.Thread(target=desde_otro_hilo)
    hilo.start()
    hilo.join()
    await asyncio.sleep(0.05)  # dar tiempo al loop a procesarlo

    assert len(recibidos) == 1


async def test_publish_threadsafe_sin_loop_avisa_claro():
    bus = EventBus()
    try:
        bus.publish_threadsafe(WakeDetected(source="clap", confidence=1.0))
        assert False, "deberia haber lanzado RuntimeError"
    except RuntimeError as error:
        assert "bind_loop" in str(error)
