from core.bus import EventBus
from core.events import SpeakRequested, SpeechTranscribed
from core.state import State
from main import JarvisApp


async def test_ping_devuelve_pong():
    app = JarvisApp(bus=EventBus())
    assert await app.procesar_texto("ping") == "pong"


async def test_un_comando_desconocido_no_revienta():
    app = JarvisApp(bus=EventBus())
    respuesta = await app.procesar_texto("hacete un café")
    assert isinstance(respuesta, str) and respuesta


async def test_publica_speech_transcribed_al_procesar():
    # text-mode tiene que recorrer el mismo camino que el audio real,
    # o dejaria de servir para depurar el pipeline.
    bus = EventBus()
    transcritos = []
    bus.subscribe(SpeechTranscribed, lambda e: transcritos.append(e))

    await JarvisApp(bus=bus).procesar_texto("ping")

    assert len(transcritos) == 1
    assert transcritos[0].text == "ping"


async def test_publica_speak_requested_con_la_respuesta():
    bus = EventBus()
    hablados = []
    bus.subscribe(SpeakRequested, lambda e: hablados.append(e))

    await JarvisApp(bus=bus).procesar_texto("ping")

    assert len(hablados) == 1
    assert hablados[0].text == "pong"


async def test_vuelve_a_idle_despues_de_responder():
    app = JarvisApp(bus=EventBus())
    await app.procesar_texto("ping")
    assert app.maquina.state is State.IDLE


async def test_procesar_dos_veces_seguidas_funciona():
    # Si la maquina de estados quedara colgada, la segunda orden reventaria.
    app = JarvisApp(bus=EventBus())
    assert await app.procesar_texto("ping") == "pong"
    assert await app.procesar_texto("ping") == "pong"
