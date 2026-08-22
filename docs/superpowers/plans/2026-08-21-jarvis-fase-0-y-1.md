# Jarvis — Plan de Implementación: Fase 0 y Fase 1

> **Para agentes:** SUB-SKILL REQUERIDA: usar `superpowers:subagent-driven-development`
> (recomendado) o `superpowers:executing-plans` para implementar tarea por tarea.
> Los pasos usan checkbox (`- [ ]`) para seguimiento.

**Objetivo:** Que decir *"oye Jarvis, qué hora es"* haga que Jarvis responda en voz alta.

**Arquitectura:** Un bus de eventos asíncrono conecta dos mitades que se desarrollan en
paralelo. Hemsy convierte audio del micrófono en un evento `SpeechTranscribed`; Rafael
convierte ese evento en una acción y un evento `SpeakRequested`. Ninguna mitad importa
módulos de la otra: solo conocen `core/`.

**Stack:** Python 3.11 · `sounddevice` · `openWakeWord` · `faster-whisper` · Piper TTS ·
`pydantic` · `pytest`

**Spec:** [PLAN.md](../../../PLAN.md) — leerlo antes de empezar. Este plan implementa
las fases 0 y 1 de la §8.

---

## Restricciones globales

Aplican a **todas** las tareas de este plan.

- **Python 3.11 exactamente.** No 3.13 ni 3.14 (wheels incompletos de `onnxruntime` y
  `faster-whisper`). Crear el venv con `py -3.11 -m venv .venv`.
- **Audio siempre a 16 kHz, mono, `int16`.** Es lo que esperan openWakeWord, silero-vad y
  Whisper. Ninguna conversión implícita en ningún módulo.
- **El dispositivo de micrófono se fija por índice explícito en `config.yaml`.** Nunca el
  dispositivo por defecto del sistema. Nunca unos auriculares Bluetooth (PLAN.md §2).
- **Idioma:** español en comentarios, docstrings, mensajes de commit y texto hablado.
  Inglés en nombres de variables, funciones y clases.
- **Nada de `exec`, `eval` ni `os.system` con strings que provengan del LLM** (PLAN.md §1).
- **Nunca commitear `.env`**, claves, ni rutas absolutas de una máquina concreta.
- **Una rama por tarea**, nombrada `<nombre>/<área>-<qué>`. Nunca commitear a `main`.
- **Toda dependencia nueva va a `requirements.txt`** en el mismo commit que la usa.
- Cada tarea termina con un commit. Los tests de una tarea deben pasar antes de commitear.

---

## Mapa de archivos

Qué crea cada tarea y de quién es la responsabilidad.

| Archivo | Responsabilidad | Tarea | Dueño |
|---|---|---|---|
| `core/events.py` | Definición de los eventos. **El contrato.** | 0.2 | Ambos |
| `core/bus.py` | Pub/sub asíncrono, seguro entre hilos | 0.3 | Ambos |
| `core/state.py` | Máquina de estados y gate half-duplex | 0.4 | Ambos |
| `skills/base.py` | Interfaz `Skill` y `SkillResult`. **El contrato.** | 0.5 | Ambos |
| `core/config.py` | Carga de `config.yaml` y `.env` | 0.6 | Ambos |
| `main.py` | Arranque, cableado, `--text-mode` | 0.7 | Ambos |
| `skills/system.py` | Hora, fecha, saludo | 1.R3 | Rafael |
| `brain/registry.py` | Registro y despacho de skills | 1.R1 | Rafael |
| `brain/router.py` | Reglas rápidas sin LLM | 1.R2 | Rafael |
| `ears/capture.py` | Captura de micrófono y buffer circular | 1.H1 | Hemsy |
| `ears/wakeword.py` | Detección de "hey jarvis" | 1.H2 | Hemsy |
| `ears/stt.py` | Transcripción con faster-whisper | 1.H3 | Hemsy |
| `voice/base.py` | Interfaz `TTSEngine` | 1.H4 | Hemsy |
| `voice/piper_tts.py` | Síntesis local con Piper | 1.H4 | Hemsy |
| `ui/console.py` | Estados y latencias en consola | 1.H5 | Hemsy |

---

## Orden de ejecución

```
FASE 0  (secuencial, la hace Rafael, la revisa Hemsy con atención)
  0.1 -> 0.2 -> 0.3 -> 0.4 -> 0.5 -> 0.6 -> 0.7
                          |
                    [ MERGE A MAIN ]
                          |
        +-----------------+-----------------+
        |                                   |
FASE 1 HEMSY                          FASE 1 RAFAEL
  1.H1 capture                          1.R1 registry
  1.H2 wakeword                         1.R2 router
  1.H3 stt                              1.R3 system
  1.H4 tts                              1.R4 cableado final
  1.H5 console                                |
        |                                     |
        +-----------------+-------------------+
                          |
                 [ DEMO: "qué hora es" ]
```

**Nada de la Fase 1 puede empezar antes de que la Fase 0 esté en `main`.** Los contratos
son lo que permite el paralelismo; sin ellos ambos programarían contra aire.

---

# TAREA 0.0 — Preparación (los dos, en paralelo, desde ya)

**No depende de nada.** Se puede hacer hoy, antes de que exista una línea de código, y
conviene: las descargas de modelos son lentas y no tiene sentido esperarlas después.

Esta tarea **no genera commits de código**. Es puesta a punto de la máquina de cada uno.

### Para los dos

- [ ] **Verificar Python 3.11**

```bash
py -0p
```

Tiene que aparecer `3.11`. Si no está, bajarlo de python.org. **No sirve 3.13 ni 3.14:**
`onnxruntime` y `faster-whisper` todavía no tienen wheels completos para esas versiones.

- [ ] **Clonar y crear el entorno**

```bash
git clone https://github.com/RafaelCly/Jarvis.git
cd Jarvis
py -3.11 -m venv .venv
.venv\Scripts\activate
```

- [ ] **Configurar la identidad de git**

Tiene que coincidir con el usuario de GitHub, porque `CLAUDE.md` lo usa para saber
qué track te toca.

```bash
git config user.name        # debe decir RafaelCly o HemsyCA
```

Si no coincide: `git config --global user.name "TuUsuario"`

- [ ] **Leer PLAN.md** — al menos §1 (qué construimos), §6 (quién hace qué) y §7 (cómo
  trabajamos juntos). Son diez minutos y evitan la mitad de las preguntas.

### Solo Hemsy

> **Tu máquina es una incógnita del proyecto.** El hardware documentado en PLAN.md §2 es
> el de Rafael. Vos construís la parte que más exige GPU —Whisper—, así que hay que saber
> con qué contás antes de llegar a la tarea 1.H3.

- [ ] **Diagnosticar tu máquina y pasarle el resultado a Rafael**

```bash
python -c "
import platform, shutil, subprocess
print('CPU:', platform.processor())
if shutil.which('nvidia-smi'):
    print(subprocess.run(['nvidia-smi','--query-gpu=name,memory.total',
                          '--format=csv,noheader'], capture_output=True, text=True).stdout.strip())
else:
    print('GPU NVIDIA: no detectada -> Whisper correra en CPU')
"
```

| Resultado | Qué significa para tu track |
|---|---|
| GPU NVIDIA con 4 GB+ | Todo normal. `stt.model_size: small`, `device: cuda`. |
| GPU NVIDIA con menos de 4 GB | Usar `model_size: base`. |
| Sin GPU NVIDIA | Poné `device: cpu` y `model_size: base` en **tu** `config.yaml`. Vas a transcribir en 1-3 s en vez de 300 ms: molesto para desarrollar, pero funciona. `config.yaml` es local de cada uno, así que no afecta a Rafael. |

- [ ] **Descargar los modelos de wake word** (unos 100 MB, tarda)

```bash
pip install openwakeword onnxruntime
python -c "import openwakeword.utils; openwakeword.utils.download_models()"
```

- [ ] **Descargar la voz de Piper**

De `https://huggingface.co/rhasspy/piper-voices`, los **dos** archivos de
`es_MX-claude-high` (`.onnx` y `.onnx.json`), a `models/piper/`.
La carpeta `models/` ya está en `.gitignore`: son archivos pesados y cada uno tiene los suyos.

- [ ] **Identificar tu micrófono**

```bash
pip install sounddevice
python -m sounddevice
```

Anotar el índice del **array interno del laptop**. Si usás auriculares Bluetooth, no los
elijas: al abrir el micrófono, Windows conmuta a modo Hands-Free y degrada toda la salida
de audio a mono 8 kHz (PLAN.md §2).

### Solo Rafael

- [ ] **Instalar [Everything](https://www.voidtools.com/)** y habilitar la CLI `es.exe`
  en el PATH. Es para la skill de archivos de la Fase 3, pero instalarlo ahora deja que
  el índice se construya tranquilo.
- [ ] **Cargar los $5 en OpenAI** y generar la API key. Copiar `.env.example` a `.env`
  y rellenarla. **`.env` nunca se commitea** — ya está en `.gitignore`.
- [ ] **Crear la app en el [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)**
  y guardar Client ID y Secret en `.env`.

### ✅ Tarea 0.0 terminada cuando

- Los dos tienen `.venv` con Python 3.11 y el repo clonado
- Hemsy sabe qué dice su GPU y ya le pasó el dato a Rafael
- Los modelos están descargados
- `git config user.name` coincide con el usuario de GitHub de cada uno

**A partir de acá, Rafael arranca la Fase 0 y Hemsy espera a que se fusione.** Es el único
momento del proyecto en que uno espera al otro.

---

# FASE 0 — Contratos y esqueleto

**Quién:** Rafael escribe, Hemsy revisa. Antes de la tarea 0.2, una llamada de 20 minutos
entre los dos para acordar los eventos: es el contrato con el que Hemsy va a vivir.

**Rama:** `rafael/core-contratos-y-esqueleto` (una sola rama para toda la Fase 0)

---

### Tarea 0.1: Esqueleto del proyecto y entorno

**Archivos:**
- Crear: `requirements.txt`, `config.yaml`, `pytest.ini`
- Crear: `core/__init__.py`, `ears/__init__.py`, `voice/__init__.py`, `ui/__init__.py`,
  `brain/__init__.py`, `skills/__init__.py`, `tests/__init__.py`

**Interfaces:**
- Consume: nada
- Produce: el árbol de paquetes que todas las demás tareas importan

- [ ] **Paso 1: Crear la rama**

```bash
git checkout main && git pull origin main
git checkout -b rafael/core-contratos-y-esqueleto
```

- [ ] **Paso 2: Crear el entorno virtual**

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
python --version
```

Esperado: `Python 3.11.x`. Si sale otra versión, parar — el resto del plan asume 3.11.

- [ ] **Paso 3: Crear `requirements.txt`**

Solo lo que la Fase 0 necesita. Las dependencias de audio y LLM se añaden en la Fase 1,
en el commit de la tarea que las usa.

```
pydantic>=2.7
pydantic-settings>=2.3
pyyaml>=6.0
rich>=13.7
pytest>=8.0
pytest-asyncio>=0.23
```

- [ ] **Paso 4: Instalar**

```bash
pip install -r requirements.txt
```

- [ ] **Paso 5: Crear los paquetes**

```bash
mkdir core ears voice ui brain skills tests
for d in core ears voice ui brain skills tests; do
  echo '"""Paquete de Jarvis."""' > $d/__init__.py
done
```

- [ ] **Paso 6: Crear `pytest.ini`**

`asyncio_mode = auto` evita tener que decorar cada test asíncrono con
`@pytest.mark.asyncio`.

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
filterwarnings =
    ignore::DeprecationWarning
```

- [ ] **Paso 7: Crear `config.yaml`**

El índice de dispositivo `null` significa "todavía sin configurar". La tarea 1.H1 añade
un comando para averiguarlo.

```yaml
# Configuración de Jarvis. Los secretos van en .env, no acá.

audio:
  # Índice del micrófono. Averigualo con:  python -m sounddevice
  # DEBE ser el array interno del laptop, NUNCA auriculares Bluetooth (PLAN.md §2).
  input_device_index: null
  sample_rate: 16000
  channels: 1
  block_size: 1280        # 80 ms a 16 kHz, lo que espera openWakeWord

wakeword:
  model: hey_jarvis
  threshold: 0.5

stt:
  model_size: small
  device: cuda            # "cuda" o "cpu"; hay fallback automático a cpu
  compute_type: float16
  language: es

tts:
  engine: piper
  voice: es_MX-claude-high

llm:
  model: gpt-4o-mini
  max_tool_iterations: 2
```

- [ ] **Paso 8: Verificar que pytest arranca**

```bash
pytest
```

Esperado: `no tests ran`, sin errores de colección.

- [ ] **Paso 9: Commit**

```bash
git add -A
git commit -m "feat(core): esqueleto de paquetes, config y entorno de tests"
```

---

### Tarea 0.2: `core/events.py` — el contrato de eventos

**Archivos:**
- Crear: `core/events.py`
- Test: `tests/test_events.py`

**Interfaces:**
- Consume: nada
- Produce: `WakeDetected`, `SpeechTranscribed`, `SpeakRequested`, `SpeakFinished`,
  `StateChanged`, `ErrorOccurred`, y el alias `Event`. Todo el resto del sistema importa
  desde acá.

> **Este es el archivo más importante del proyecto.** Hemsy tiene que estar de acuerdo con
> él antes de que se fusione. Cambiarlo después obliga a los dos a hacer `git pull` y
> puede romper código en silencio.

Decisión de diseño: los eventos son `frozen=True` (inmutables). Un evento es un hecho que
ya ocurrió; si un handler pudiera modificarlo, el siguiente handler recibiría algo
distinto y la causa sería imposible de rastrear.

- [ ] **Paso 1: Escribir el test que falla**

`tests/test_events.py`:

```python
"""Los eventos son el contrato entre tracks: se testean como tal."""
import dataclasses

import pytest

from core.events import (
    ErrorOccurred,
    SpeakFinished,
    SpeakRequested,
    SpeechTranscribed,
    StateChanged,
    WakeDetected,
)


def test_wake_detected_lleva_origen_y_confianza():
    evento = WakeDetected(source="clap", confidence=0.92)
    assert evento.source == "clap"
    assert evento.confidence == 0.92
    assert evento.timestamp > 0


def test_speech_transcribed_lleva_texto_y_duracion():
    evento = SpeechTranscribed(text="qué hora es", language="es", duration_s=1.4)
    assert evento.text == "qué hora es"
    assert evento.language == "es"
    assert evento.duration_s == 1.4


def test_speak_requested_es_interrumpible_por_defecto():
    assert SpeakRequested(text="hola").interruptible is True


def test_los_eventos_son_inmutables():
    # Un evento es un hecho ocurrido. Si un handler pudiera mutarlo, el
    # siguiente handler veria algo distinto y el bug seria irrastreable.
    evento = SpeechTranscribed(text="hola", language="es", duration_s=1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        evento.text = "otra cosa"


def test_el_timestamp_se_rellena_solo():
    assert WakeDetected(source="wakeword", confidence=0.7).timestamp > 0


def test_state_changed_lleva_estado_viejo_y_nuevo():
    evento = StateChanged(old="idle", new="listening")
    assert (evento.old, evento.new) == ("idle", "listening")


def test_error_occurred_lleva_donde_y_que():
    evento = ErrorOccurred(where="ears.stt", message="modelo no encontrado")
    assert evento.where == "ears.stt"
    assert "modelo" in evento.message


def test_speak_finished_existe_para_cerrar_el_gate():
    # ui/ y ears/ dependen de este evento para saber cuando volver a escuchar.
    assert SpeakFinished().timestamp > 0
```

- [ ] **Paso 2: Correr el test y verificar que falla**

```bash
pytest tests/test_events.py -v
```

Esperado: `ModuleNotFoundError: No module named 'core.events'`

- [ ] **Paso 3: Escribir `core/events.py`**

```python
"""
Contratos de eventos entre las capas de Jarvis.

CUIDADO: este archivo es el contrato entre los dos tracks de trabajo.
Cambiarlo va en su propio PR, pequeño y avisado (PLAN.md §7.5).

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
```

- [ ] **Paso 4: Correr el test y verificar que pasa**

```bash
pytest tests/test_events.py -v
```

Esperado: 8 passed

- [ ] **Paso 5: Commit**

```bash
git add core/events.py tests/test_events.py
git commit -m "feat(core): definir el contrato de eventos entre tracks"
```

---

### Tarea 0.3: `core/bus.py` — el bus de eventos

**Archivos:**
- Crear: `core/bus.py`
- Test: `tests/test_bus.py`

**Interfaces:**
- Consume: `core.events`
- Produce: `EventBus` con `subscribe(event_type, handler)`, `async publish(event)`,
  `publish_threadsafe(event)` y `bind_loop(loop)`

Dos decisiones que hay que respetar:

1. **Un handler que revienta no puede tumbar el bus.** Se registra el error y se sigue con
   los demás. Si el TTS falla, el icono de bandeja tiene que seguir actualizándose.
2. **`publish_threadsafe` existe porque el callback de PortAudio corre en su propio hilo**,
   fuera del loop de asyncio. Llamar `publish()` desde ahí no funciona.

- [ ] **Paso 1: Escribir el test que falla**

`tests/test_bus.py`:

```python
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
```

- [ ] **Paso 2: Correr el test y verificar que falla**

```bash
pytest tests/test_bus.py -v
```

Esperado: `ModuleNotFoundError: No module named 'core.bus'`

- [ ] **Paso 3: Escribir `core/bus.py`**

```python
"""
Bus de eventos en proceso.

Es la costura entre los dos tracks: Hemsy publica eventos de audio, Rafael
los consume, y ninguno importa modulos del otro.
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
                    "Handler %r fallo procesando %s",
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
```

- [ ] **Paso 4: Correr el test y verificar que pasa**

```bash
pytest tests/test_bus.py -v
```

Esperado: 7 passed

- [ ] **Paso 5: Commit**

```bash
git add core/bus.py tests/test_bus.py
git commit -m "feat(core): bus de eventos asincrono y seguro entre hilos"
```

---

### Tarea 0.4: `core/state.py` — máquina de estados y gate half-duplex

**Archivos:**
- Crear: `core/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consume: `core.bus.EventBus`, `core.events.StateChanged`
- Produce: `State` (enum), `StateMachine` con `state`, `async transition_to(nuevo)`,
  `puede_escuchar` (bool)

`puede_escuchar` es el gate half-duplex de PLAN.md §5.4: devuelve `False` mientras Jarvis
habla. Sin esto, Jarvis se oye por los parlantes, se re-dispara y entra en bucle.

- [ ] **Paso 1: Escribir el test que falla**

`tests/test_state.py`:

```python
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
```

- [ ] **Paso 2: Correr el test y verificar que falla**

```bash
pytest tests/test_state.py -v
```

Esperado: `ModuleNotFoundError: No module named 'core.state'`

- [ ] **Paso 3: Escribir `core/state.py`**

```python
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
```

- [ ] **Paso 4: Correr el test y verificar que pasa**

```bash
pytest tests/test_state.py -v
```

Esperado: 8 passed

- [ ] **Paso 5: Commit**

```bash
git add core/state.py tests/test_state.py
git commit -m "feat(core): maquina de estados con gate half-duplex"
```

---

### Tarea 0.5: `skills/base.py` — el contrato de skills

**Archivos:**
- Crear: `skills/base.py`
- Test: `tests/test_skills_base.py`

**Interfaces:**
- Consume: `pydantic.BaseModel`
- Produce: `SkillResult`, `Skill` (Protocol), `tool_schema(skill)`

`tool_schema()` es la pieza que hace que añadir una skill sea escribir una clase y nada
más: genera el JSON que espera OpenAI a partir del `params_model` de pydantic, sin que
nadie tenga que escribirlo a mano ni tocar el prompt.

- [ ] **Paso 1: Escribir el test que falla**

`tests/test_skills_base.py`:

```python
from pydantic import BaseModel, Field

from skills.base import Skill, SkillResult, tool_schema


class ParamsDePrueba(BaseModel):
    query: str = Field(description="Lo que hay que buscar")
    limite: int = 5


class SkillDePrueba:
    name = "buscar_algo"
    description = "Busca algo en algun lado"
    params_model = ParamsDePrueba

    async def execute(self, params: ParamsDePrueba) -> SkillResult:
        return SkillResult(ok=True, speech=f"busque {params.query}")


def test_skill_result_guarda_lo_que_se_dice():
    resultado = SkillResult(ok=True, speech="son las tres")
    assert resultado.ok is True
    assert resultado.speech == "son las tres"
    assert resultado.data is None


def test_una_clase_bien_formada_cumple_el_protocolo():
    assert isinstance(SkillDePrueba(), Skill)


def test_una_clase_incompleta_no_cumple_el_protocolo():
    class SkillRota:
        name = "rota"

    assert not isinstance(SkillRota(), Skill)


def test_tool_schema_arma_el_json_que_espera_openai():
    esquema = tool_schema(SkillDePrueba())

    assert esquema["type"] == "function"
    assert esquema["function"]["name"] == "buscar_algo"
    assert esquema["function"]["description"] == "Busca algo en algun lado"
    assert "query" in esquema["function"]["parameters"]["properties"]


def test_tool_schema_marca_como_requeridos_los_campos_sin_default():
    esquema = tool_schema(SkillDePrueba())
    requeridos = esquema["function"]["parameters"].get("required", [])

    assert "query" in requeridos
    assert "limite" not in requeridos


async def test_execute_devuelve_un_skill_result():
    resultado = await SkillDePrueba().execute(ParamsDePrueba(query="pdfs"))
    assert isinstance(resultado, SkillResult)
    assert "pdfs" in resultado.speech
```

- [ ] **Paso 2: Correr el test y verificar que falla**

```bash
pytest tests/test_skills_base.py -v
```

Esperado: `ModuleNotFoundError: No module named 'skills.base'`

- [ ] **Paso 3: Escribir `skills/base.py`**

```python
"""
Contrato de las skills (PLAN.md §5.6).

CUIDADO: contrato compartido entre tracks. Cambiarlo va en su propio PR.

Anadir una capacidad nueva a Jarvis es escribir una clase que cumpla el
Protocol Skill y registrarla. No hay que tocar el prompt ni el orquestador:
tool_schema() deriva el JSON de OpenAI del modelo pydantic.
"""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


@dataclass
class SkillResult:
    """Lo que devuelve una skill al ejecutarse.

    speech es lo que Jarvis dice en voz alta; data es informacion
    estructurada para la interfaz, que no se pronuncia.
    """

    ok: bool
    speech: str
    data: dict[str, Any] | None = None


@runtime_checkable
class Skill(Protocol):
    """Una capacidad de Jarvis.

    name debe ser un identificador valido de funcion: el LLM lo devuelve
    literalmente cuando elige esta skill.

    description es lo unico que el LLM lee para decidir si usarla. Escribirla
    pensando en el modelo, no en un humano.
    """

    name: str
    description: str
    params_model: type[BaseModel]

    async def execute(self, params: BaseModel) -> SkillResult: ...


def tool_schema(skill: Skill) -> dict[str, Any]:
    """Convierte una skill al formato de herramienta de OpenAI.

    Deriva los parametros del JSON Schema que genera pydantic, asi que el
    esquema nunca se desincroniza del modelo real.
    """
    parametros = skill.params_model.model_json_schema()
    parametros.pop("title", None)

    return {
        "type": "function",
        "function": {
            "name": skill.name,
            "description": skill.description,
            "parameters": parametros,
        },
    }
```

- [ ] **Paso 4: Correr el test y verificar que pasa**

```bash
pytest tests/test_skills_base.py -v
```

Esperado: 6 passed

- [ ] **Paso 5: Commit**

```bash
git add skills/base.py tests/test_skills_base.py
git commit -m "feat(skills): contrato de skills y generacion de tool schema"
```

---

### Tarea 0.6: `core/config.py` — configuración

**Archivos:**
- Crear: `core/config.py`, `.env.example` (ya existe, verificar)
- Test: `tests/test_config.py`

**Interfaces:**
- Consume: `config.yaml`, `.env`
- Produce: `Config` con `.audio`, `.wakeword`, `.stt`, `.tts`, `.llm`, y `cargar_config(ruta)`

- [ ] **Paso 1: Escribir el test que falla**

`tests/test_config.py`:

```python
import pytest

from core.config import Config, cargar_config

YAML_MINIMO = """
audio:
  input_device_index: 3
  sample_rate: 16000
  channels: 1
  block_size: 1280
wakeword:
  model: hey_jarvis
  threshold: 0.6
stt:
  model_size: small
  device: cuda
  compute_type: float16
  language: es
tts:
  engine: piper
  voice: es_MX-claude-high
llm:
  model: gpt-4o-mini
  max_tool_iterations: 2
"""


def test_carga_el_yaml_completo(tmp_path):
    ruta = tmp_path / "config.yaml"
    ruta.write_text(YAML_MINIMO, encoding="utf-8")

    config = cargar_config(ruta)

    assert config.audio.input_device_index == 3
    assert config.wakeword.threshold == 0.6
    assert config.stt.language == "es"
    assert config.llm.model == "gpt-4o-mini"


def test_el_sample_rate_debe_ser_16000(tmp_path):
    # openWakeWord, silero-vad y Whisper esperan 16 kHz. Fallar temprano
    # es mucho mejor que depurar por que la transcripcion sale en chino.
    ruta = tmp_path / "config.yaml"
    ruta.write_text(YAML_MINIMO.replace("sample_rate: 16000", "sample_rate: 44100"))

    with pytest.raises(ValueError, match="16000"):
        cargar_config(ruta)


def test_falla_claro_si_el_archivo_no_existe(tmp_path):
    with pytest.raises(FileNotFoundError, match="config.yaml"):
        cargar_config(tmp_path / "no-existe.yaml")


def test_input_device_index_puede_ser_none(tmp_path):
    # null significa "todavia sin configurar"; capture.py da un error util.
    ruta = tmp_path / "config.yaml"
    ruta.write_text(YAML_MINIMO.replace("input_device_index: 3", "input_device_index: null"))

    assert cargar_config(ruta).audio.input_device_index is None


def test_es_un_config(tmp_path):
    ruta = tmp_path / "config.yaml"
    ruta.write_text(YAML_MINIMO, encoding="utf-8")
    assert isinstance(cargar_config(ruta), Config)
```

- [ ] **Paso 2: Correr el test y verificar que falla**

```bash
pytest tests/test_config.py -v
```

Esperado: `ModuleNotFoundError: No module named 'core.config'`

- [ ] **Paso 3: Escribir `core/config.py`**

```python
"""
Configuracion de Jarvis: config.yaml para ajustes, .env para secretos.

Los secretos nunca van al YAML porque el YAML se commitea.
"""

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class AudioConfig(BaseModel):
    input_device_index: int | None = None
    sample_rate: int = 16000
    channels: int = 1
    block_size: int = 1280

    @field_validator("sample_rate")
    @classmethod
    def _debe_ser_16k(cls, v: int) -> int:
        # openWakeWord, silero-vad y Whisper asumen 16 kHz. Si alguien lo
        # cambia, falla aca y no tres capas mas abajo con audio corrupto.
        if v != 16000:
            raise ValueError("sample_rate debe ser 16000 para todo el pipeline")
        return v


class WakewordConfig(BaseModel):
    model: str = "hey_jarvis"
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class STTConfig(BaseModel):
    model_size: str = "small"
    device: Literal["cuda", "cpu"] = "cuda"
    compute_type: str = "float16"
    language: str = "es"


class TTSConfig(BaseModel):
    engine: Literal["piper", "edge"] = "piper"
    voice: str = "es_MX-claude-high"


class LLMConfig(BaseModel):
    model: str = "gpt-4o-mini"
    max_tool_iterations: int = 2


class Config(BaseModel):
    audio: AudioConfig = AudioConfig()
    wakeword: WakewordConfig = WakewordConfig()
    stt: STTConfig = STTConfig()
    tts: TTSConfig = TTSConfig()
    llm: LLMConfig = LLMConfig()

    @property
    def openai_api_key(self) -> str | None:
        """Se lee del entorno, nunca del YAML."""
        return os.environ.get("OPENAI_API_KEY")


def cargar_config(ruta: Path | str = "config.yaml") -> Config:
    """Carga y valida config.yaml. Lanza FileNotFoundError si no existe."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(
            f"No encuentro {ruta}. Copiá config.yaml del repo a la raíz del proyecto."
        )

    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    return Config(**datos)
```

- [ ] **Paso 4: Correr el test y verificar que pasa**

```bash
pytest tests/test_config.py -v
```

Esperado: 5 passed

- [ ] **Paso 5: Commit**

```bash
git add core/config.py tests/test_config.py
git commit -m "feat(core): carga y validacion de configuracion"
```

---

### Tarea 0.7: `main.py --text-mode` y la skill `ping`

**Archivos:**
- Crear: `main.py`, `skills/ping.py`
- Test: `tests/test_text_mode.py`

**Interfaces:**
- Consume: todo lo anterior
- Produce: `JarvisApp` con `async procesar_texto(texto) -> str`, y el punto de entrada CLI

> **Esta es la tarea de mayor retorno de todo el plan.** `--text-mode` salta el pipeline
> de audio y lee órdenes por teclado. Permite a Rafael desarrollar y depurar el cerebro
> entero sin micrófono, sin GPU y sin hablarle a la computadora, y hace que los tests
> end-to-end sean triviales.

- [ ] **Paso 1: Escribir la skill `ping`**

`skills/ping.py`:

```python
"""Skill de humo: confirma que el pipeline completo esta cableado."""

from pydantic import BaseModel

from skills.base import SkillResult


class PingParams(BaseModel):
    """No necesita parametros."""


class PingSkill:
    name = "ping"
    description = "Responde 'pong'. Sirve para verificar que Jarvis esta vivo."
    params_model = PingParams

    async def execute(self, params: PingParams) -> SkillResult:
        return SkillResult(ok=True, speech="pong")
```

- [ ] **Paso 2: Escribir el test que falla**

`tests/test_text_mode.py`:

```python
from core.bus import EventBus
from core.events import SpeakRequested, SpeechTranscribed
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
    from core.state import State

    app = JarvisApp(bus=EventBus())
    await app.procesar_texto("ping")
    assert app.maquina.state is State.IDLE
```

- [ ] **Paso 3: Correr el test y verificar que falla**

```bash
pytest tests/test_text_mode.py -v
```

Esperado: `ModuleNotFoundError: No module named 'main'`

- [ ] **Paso 4: Escribir `main.py`**

El despacho por ahora es un `dict` de nombre a skill. La tarea 1.R1 lo reemplaza por el
`Registry` y la 1.R2 mete el router de reglas delante.

```python
"""
Punto de entrada de Jarvis.

    python main.py              pipeline completo con microfono
    python main.py --text-mode  ordenes por teclado, sin audio

--text-mode recorre exactamente el mismo camino que el audio real, salvo
la captura y la transcripcion. Es la forma de trabajar en brain/ y skills/
sin microfono ni GPU.
"""

import argparse
import asyncio

from rich.console import Console

from core.bus import EventBus
from core.events import SpeakRequested, SpeechTranscribed
from core.state import State, StateMachine
from skills.base import Skill, SkillResult
from skills.ping import PingSkill

console = Console()


class JarvisApp:
    """Cablea el bus, la maquina de estados y las skills."""

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.maquina = StateMachine(bus)
        self.skills: dict[str, Skill] = {}
        self._registrar(PingSkill())

    def _registrar(self, skill: Skill) -> None:
        self.skills[skill.name] = skill

    async def procesar_texto(self, texto: str) -> str:
        """Recorre el pipeline desde texto ya transcrito hasta la respuesta."""
        await self.maquina.transition_to(State.LISTENING)
        await self.bus.publish(
            SpeechTranscribed(text=texto, language="es", duration_s=0.0)
        )

        await self.maquina.transition_to(State.TRANSCRIBING)
        await self.maquina.transition_to(State.THINKING)

        skill = self.skills.get(texto.strip().lower())
        if skill is None:
            resultado = SkillResult(ok=False, speech="No sé hacer eso todavía.")
        else:
            await self.maquina.transition_to(State.ACTING)
            resultado = await skill.execute(skill.params_model())

        await self.maquina.transition_to(State.SPEAKING)
        await self.bus.publish(SpeakRequested(text=resultado.speech))
        await self.maquina.transition_to(State.IDLE)

        return resultado.speech


async def bucle_texto(app: JarvisApp) -> None:
    """Lee ordenes de stdin hasta Ctrl-C o 'salir'."""
    console.print("[bold cyan]Jarvis en modo texto.[/] Escribí 'salir' para terminar.\n")

    while True:
        try:
            texto = await asyncio.to_thread(input, "> ")
        except (EOFError, KeyboardInterrupt):
            break

        if texto.strip().lower() in {"salir", "exit", "quit"}:
            break
        if not texto.strip():
            continue

        respuesta = await app.procesar_texto(texto)
        console.print(f"[bold green]Jarvis:[/] {respuesta}")

    console.print("\n[dim]Hasta luego.[/]")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis, asistente de voz local")
    parser.add_argument(
        "--text-mode",
        action="store_true",
        help="Leer ordenes por teclado en vez de por microfono",
    )
    args = parser.parse_args()

    bus = EventBus()
    bus.bind_loop(asyncio.get_running_loop())
    app = JarvisApp(bus=bus)

    if args.text_mode:
        await bucle_texto(app)
    else:
        console.print(
            "[yellow]El pipeline de audio llega en la Fase 1.[/] "
            "Mientras tanto: [bold]python main.py --text-mode[/]"
        )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Paso 5: Correr el test y verificar que pasa**

```bash
pytest tests/test_text_mode.py -v
```

Esperado: 5 passed

- [ ] **Paso 6: Verificación manual — el criterio de la Fase 0**

```bash
python main.py --text-mode
```

Escribir `ping`. Esperado: `Jarvis: pong`. Después escribir `salir`.

- [ ] **Paso 7: Correr la suite completa**

```bash
pytest -v
```

Esperado: 39 passed

- [ ] **Paso 8: Commit y abrir el PR**

```bash
git add main.py skills/ping.py tests/test_text_mode.py
git commit -m "feat(core): modo texto end-to-end con skill ping"
git push -u origin rafael/core-contratos-y-esqueleto
gh pr create --fill
```

> **Hemsy revisa este PR con atención.** No es un PR normal: está aprobando el contrato
> contra el que va a programar toda la Fase 1. Si algo de `events.py` no le cierra, este
> es el momento barato de cambiarlo.

---

## ✅ Fase 0 terminada cuando

- `python main.py --text-mode` responde `pong` a `ping`
- `pytest` pasa entero
- El PR está fusionado en `main` y **ambos hicieron `git pull`**

---

# FASE 1 — Escucha y responde

**A partir de acá los dos trabajan en paralelo.** Cada uno en su rama, sin bloquear al otro.

Antes de empezar, ambos: `git checkout main && git pull origin main`.

---

## Track de Hemsy — `ears/`, `voice/`, `ui/`

---

### Tarea 1.H1: `ears/capture.py` — captura de micrófono

**Rama:** `hemsy/ears-captura`

**Archivos:**
- Crear: `ears/capture.py`, `tools_listar_dispositivos.py`
- Modificar: `requirements.txt`
- Test: `tests/test_capture.py`

**Interfaces:**
- Consume: `core.config.AudioConfig`
- Produce: `AudioCapture(config, on_block)` con `start()`, `stop()`, `ultimo_segundo()`;
  `on_block` recibe `numpy.ndarray` de 1280 muestras `int16`

- [ ] **Paso 1: Añadir dependencias**

Agregar a `requirements.txt` y `pip install -r requirements.txt`:

```
sounddevice>=0.4.6
numpy>=1.26
```

- [ ] **Paso 2: Escribir la herramienta para encontrar el micrófono**

`tools_listar_dispositivos.py`:

```python
"""Lista los dispositivos de audio para llenar config.yaml.

    py -3.11 tools_listar_dispositivos.py

Elegir el ARRAY INTERNO del laptop, nunca auriculares Bluetooth: al abrir
el microfono, Bluetooth conmuta a modo Hands-Free y degrada toda la salida
de audio a mono 8 kHz (PLAN.md §2).
"""

import sounddevice as sd

for indice, dispositivo in enumerate(sd.query_devices()):
    if dispositivo["max_input_channels"] > 0:
        aviso = ""
        nombre = dispositivo["name"]
        if any(p in nombre.lower() for p in ("bluetooth", "hands-free", "headset")):
            aviso = "  <-- EVITAR: Bluetooth degrada el audio"
        print(f"[{indice:>2}] {nombre}{aviso}")
```

- [ ] **Paso 3: Correrla y anotar el índice**

```bash
py -3.11 tools_listar_dispositivos.py
```

Poner el índice del array interno en `config.yaml` → `audio.input_device_index`.

- [ ] **Paso 4: Escribir el test que falla**

Los tests no abren el micrófono: inyectan bloques a mano.

`tests/test_capture.py`:

```python
import numpy as np
import pytest

from core.config import AudioConfig
from ears.capture import AudioCapture


def test_falla_claro_si_no_hay_dispositivo_configurado():
    config = AudioConfig(input_device_index=None)
    with pytest.raises(ValueError, match="input_device_index"):
        AudioCapture(config, on_block=lambda b: None)


def test_el_callback_recibe_los_bloques():
    recibidos = []
    captura = AudioCapture(
        AudioConfig(input_device_index=0), on_block=recibidos.append
    )
    bloque = np.zeros(1280, dtype=np.int16)

    captura._procesar_bloque(bloque)

    assert len(recibidos) == 1
    assert recibidos[0].shape == (1280,)


def test_el_buffer_circular_guarda_el_ultimo_segundo():
    captura = AudioCapture(AudioConfig(input_device_index=0), on_block=lambda b: None)

    # 16000 Hz / 1280 muestras = 12.5 bloques por segundo. 20 bloques > 1 s.
    for i in range(20):
        captura._procesar_bloque(np.full(1280, i, dtype=np.int16))

    audio = captura.ultimo_segundo()
    assert len(audio) == 16000
    assert audio.dtype == np.int16
    # Debe conservar el final, no el principio.
    assert audio[-1] == 19


def test_el_buffer_no_falla_si_hay_menos_de_un_segundo():
    captura = AudioCapture(AudioConfig(input_device_index=0), on_block=lambda b: None)
    captura._procesar_bloque(np.zeros(1280, dtype=np.int16))

    assert len(captura.ultimo_segundo()) == 1280
```

- [ ] **Paso 5: Correr el test y verificar que falla**

```bash
pytest tests/test_capture.py -v
```

Esperado: `ModuleNotFoundError: No module named 'ears.capture'`

- [ ] **Paso 6: Escribir `ears/capture.py`**

```python
"""
Captura de microfono y buffer circular.

El callback de PortAudio corre en su propio hilo y tiene un presupuesto de
tiempo estricto: si tarda mas que la duracion del bloque, el audio se corta.
Por eso aca no se hace nada pesado — solo copiar y delegar.
"""

import logging
from collections import deque

import numpy as np
import sounddevice as sd

from core.config import AudioConfig

log = logging.getLogger(__name__)

# 5 segundos de pre-roll a 12.5 bloques/s.
_BLOQUES_EN_BUFFER = 63


class AudioCapture:
    """Abre el microfono y entrega bloques de 1280 muestras int16."""

    def __init__(self, config: AudioConfig, on_block) -> None:
        if config.input_device_index is None:
            raise ValueError(
                "audio.input_device_index no está configurado en config.yaml. "
                "Corré:  py -3.11 tools_listar_dispositivos.py"
            )

        self._config = config
        self._on_block = on_block
        self._buffer: deque[np.ndarray] = deque(maxlen=_BLOQUES_EN_BUFFER)
        self._stream: sd.InputStream | None = None

    def _procesar_bloque(self, bloque: np.ndarray) -> None:
        """Guarda en el buffer y avisa al consumidor. Separado del callback
        de PortAudio para poder testearlo sin abrir el microfono."""
        self._buffer.append(bloque)
        try:
            self._on_block(bloque)
        except Exception:
            log.exception("El consumidor de audio falló")

    def _callback(self, indata, frames, time_info, status) -> None:
        if status:
            log.warning("Estado de PortAudio: %s", status)
        # copy() porque PortAudio reutiliza el buffer en el proximo callback.
        self._procesar_bloque(indata[:, 0].copy())

    def ultimo_segundo(self) -> np.ndarray:
        """El ultimo segundo de audio, o todo lo que haya si es menos."""
        if not self._buffer:
            return np.zeros(0, dtype=np.int16)

        audio = np.concatenate(list(self._buffer))
        return audio[-self._config.sample_rate :]

    def start(self) -> None:
        self._stream = sd.InputStream(
            samplerate=self._config.sample_rate,
            channels=self._config.channels,
            dtype="int16",
            blocksize=self._config.block_size,
            device=self._config.input_device_index,
            callback=self._callback,
        )
        self._stream.start()
        log.info("Micrófono abierto en el dispositivo %s", self._config.input_device_index)

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
```

- [ ] **Paso 7: Correr el test y verificar que pasa**

```bash
pytest tests/test_capture.py -v
```

Esperado: 4 passed

- [ ] **Paso 8: Verificación manual con micrófono real**

```bash
python -c "
import time, numpy as np
from core.config import cargar_config
from ears.capture import AudioCapture
cfg = cargar_config().audio
niveles = []
c = AudioCapture(cfg, on_block=lambda b: niveles.append(np.abs(b).mean()))
c.start(); print('Hablá 3 segundos...'); time.sleep(3); c.stop()
print(f'Bloques: {len(niveles)}  Nivel medio: {np.mean(niveles):.0f}')
"
```

Esperado: ~37 bloques en 3 s, y el nivel medio claramente mayor en silencio que hablando.
Si el nivel es 0, el índice de dispositivo está mal.

- [ ] **Paso 9: Commit y PR**

```bash
git add ears/capture.py tools_listar_dispositivos.py tests/test_capture.py requirements.txt
git commit -m "feat(ears): captura de microfono con buffer circular"
git push -u origin hemsy/ears-captura
gh pr create --fill
```

---

### Tarea 1.H2: `ears/wakeword.py` — detección de "hey jarvis"

**Rama:** `hemsy/ears-wakeword`

**Archivos:**
- Crear: `ears/wakeword.py`
- Modificar: `requirements.txt`
- Test: `tests/test_wakeword.py`

**Interfaces:**
- Consume: `core.config.WakewordConfig`, bloques de `AudioCapture`
- Produce: `WakeWordDetector(config)` con `procesar(bloque) -> float | None` (devuelve la
  confianza si superó el umbral, `None` si no)

> **Riesgo R2 de PLAN.md.** El modelo `hey_jarvis` está entrenado con voces en inglés.
> **Probarlo con voz real es el paso 5, y es lo primero que hay que hacer de esta tarea.**
> Si no reconoce el acento, la salida está documentada abajo.

- [ ] **Paso 1: Añadir dependencias y descargar modelos**

```
openwakeword>=0.6.0
onnxruntime>=1.17
```

```bash
pip install -r requirements.txt
python -c "import openwakeword.utils; openwakeword.utils.download_models()"
```

- [ ] **Paso 2: Escribir el test que falla**

`tests/test_wakeword.py`:

```python
import numpy as np

from core.config import WakewordConfig
from ears.wakeword import WakeWordDetector


def test_el_silencio_no_dispara():
    detector = WakeWordDetector(WakewordConfig(threshold=0.5))
    silencio = np.zeros(1280, dtype=np.int16)

    for _ in range(20):
        assert detector.procesar(silencio) is None


def test_el_ruido_blanco_no_dispara():
    # Si esto falla, el umbral esta demasiado bajo y va a haber falsos
    # positivos con cualquier ruido de la habitacion.
    rng = np.random.default_rng(42)
    detector = WakeWordDetector(WakewordConfig(threshold=0.5))

    for _ in range(20):
        ruido = rng.integers(-3000, 3000, 1280, dtype=np.int16)
        assert detector.procesar(ruido) is None


def test_un_umbral_de_cero_dispara_con_cualquier_cosa():
    # Verifica que el cableado con openWakeWord funciona de verdad.
    detector = WakeWordDetector(WakewordConfig(threshold=0.0))
    resultado = detector.procesar(np.zeros(1280, dtype=np.int16))

    assert resultado is not None
    assert 0.0 <= resultado <= 1.0


def test_el_periodo_refractario_evita_disparos_encadenados():
    detector = WakeWordDetector(WakewordConfig(threshold=0.0))
    silencio = np.zeros(1280, dtype=np.int16)

    primero = detector.procesar(silencio)
    segundo = detector.procesar(silencio)

    assert primero is not None
    assert segundo is None  # dentro del periodo refractario
```

- [ ] **Paso 3: Correr el test y verificar que falla**

```bash
pytest tests/test_wakeword.py -v
```

Esperado: `ModuleNotFoundError: No module named 'ears.wakeword'`

- [ ] **Paso 4: Escribir `ears/wakeword.py`**

```python
"""
Deteccion de wake word con openWakeWord.

Corre en ONNX sobre CPU en unos 4 ms por bloque, asi que puede estar
escuchando todo el tiempo sin costo perceptible.
"""

import logging
import time

import numpy as np
from openwakeword.model import Model

from core.config import WakewordConfig

log = logging.getLogger(__name__)

# Tras un disparo, ignorar deteciones un rato: el modelo suele dar varios
# frames por encima del umbral para una sola pronunciacion.
_REFRACTARIO_S = 2.0


class WakeWordDetector:
    """Devuelve la confianza cuando oye la wake word, o None."""

    def __init__(self, config: WakewordConfig) -> None:
        self._umbral = config.threshold
        self._nombre = config.model
        self._modelo = Model(
            wakeword_models=[config.model], inference_framework="onnx"
        )
        self._ultimo_disparo = 0.0

    def procesar(self, bloque: np.ndarray) -> float | None:
        """Procesa 1280 muestras int16. Devuelve la confianza o None."""
        if time.monotonic() - self._ultimo_disparo < _REFRACTARIO_S:
            return None

        predicciones = self._modelo.predict(bloque)
        confianza = float(predicciones.get(self._nombre, 0.0))

        if confianza < self._umbral:
            return None

        self._ultimo_disparo = time.monotonic()
        log.info("Wake word detectada (confianza %.2f)", confianza)
        return confianza
```

- [ ] **Paso 5: Correr el test y verificar que pasa**

```bash
pytest tests/test_wakeword.py -v
```

Esperado: 4 passed

- [ ] **Paso 6: LA PRUEBA QUE IMPORTA — decirle "hey jarvis" de verdad**

```bash
python -c "
import time
from core.config import cargar_config
from ears.capture import AudioCapture
from ears.wakeword import WakeWordDetector
cfg = cargar_config()
det = WakeWordDetector(cfg.wakeword)
def on_block(b):
    c = det.procesar(b)
    if c: print(f'  DETECTADA  confianza={c:.2f}')
cap = AudioCapture(cfg.audio, on_block=on_block)
cap.start(); print('Decí \'hey jarvis\' varias veces. 30 segundos.'); time.sleep(30); cap.stop()
"
```

Decirlo 10 veces con tono normal. **Contar cuántas detecta.**

| Detecciones | Veredicto |
|---|---|
| 8-10 de 10 | Funciona. Seguir. |
| 4-7 de 10 | Bajar `wakeword.threshold` a 0.35 y repetir. |
| 0-3 de 10 | El modelo en inglés no sirve para tu acento. Ir al paso 7. |

- [ ] **Paso 7: SOLO SI FALLÓ — entrenar un modelo propio en español**

openWakeWord trae un notebook de entrenamiento que genera miles de muestras sintéticas
con Piper. Permite entrenar **"oye Jarvis"** en español, gratis, en Colab. El notebook
está en el repo de openWakeWord (`notebooks/automatic_model_training.ipynb`).

El modelo `.onnx` resultante va en `models/` (ya está en `.gitignore` por tamaño) y se
apunta desde `config.yaml` → `wakeword.model`.

**Si esto también falla:** activación solo por palmada (Fase 2). No bloquea el proyecto.

- [ ] **Paso 8: Commit y PR**

```bash
git add ears/wakeword.py tests/test_wakeword.py requirements.txt
git commit -m "feat(ears): deteccion de wake word con openWakeWord"
git push -u origin hemsy/ears-wakeword
gh pr create --fill
```

Anotar en la descripción del PR **cuántas de 10 detectó**. Es el dato que decide si hay
que entrenar un modelo propio, y Rafael necesita saberlo.

---

### Tarea 1.H3: `ears/stt.py` — transcripción con faster-whisper

**Rama:** `hemsy/ears-stt`

**Archivos:**
- Crear: `ears/stt.py`
- Modificar: `requirements.txt`
- Test: `tests/test_stt.py`, `tests/fixtures/audio/hola_jarvis.wav`

**Interfaces:**
- Consume: `core.config.STTConfig`
- Produce: `Transcriber(config)` con `transcribir(audio: np.ndarray) -> tuple[str, float]`
  (texto y duración en segundos)

> **Riesgo R1 de PLAN.md — el problema clásico de este stack en Windows.**
> `faster-whisper` en GPU necesita DLLs de cuBLAS y cuDNN que pip no pone en el PATH.
> El módulo las registra al importarse y cae a CPU si algo falla.

- [ ] **Paso 1: Añadir dependencias**

```
faster-whisper>=1.0
nvidia-cublas-cu12
nvidia-cudnn-cu12
```

```bash
pip install -r requirements.txt
```

- [ ] **Paso 2: Grabar el fixture de audio**

```bash
python -c "
import sounddevice as sd, soundfile as sf
from core.config import cargar_config
cfg = cargar_config().audio
print('Decí: hola jarvis qué hora es')
a = sd.rec(int(3*16000), samplerate=16000, channels=1, dtype='int16', device=cfg.input_device_index)
sd.wait()
sf.write('tests/fixtures/audio/hola_jarvis.wav', a, 16000)
print('Guardado.')
"
```

Requiere `soundfile>=0.12` en `requirements.txt`.

- [ ] **Paso 3: Escribir el test que falla**

`tests/test_stt.py`:

```python
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from core.config import STTConfig
from ears.stt import Transcriber

FIXTURE = Path("tests/fixtures/audio/hola_jarvis.wav")


@pytest.fixture(scope="module")
def transcriber():
    return Transcriber(STTConfig(model_size="small", language="es"))


def test_el_silencio_devuelve_texto_vacio(transcriber):
    silencio = np.zeros(16000, dtype=np.int16)
    texto, _ = transcriber.transcribir(silencio)
    assert texto.strip() == ""


@pytest.mark.skipif(not FIXTURE.exists(), reason="falta el fixture de audio")
def test_transcribe_el_fixture_en_espanol(transcriber):
    audio, _ = sf.read(FIXTURE, dtype="int16")
    texto, duracion = transcriber.transcribir(audio)

    assert "jarvis" in texto.lower()
    assert "hora" in texto.lower()
    assert duracion > 0


def test_cae_a_cpu_si_cuda_no_esta_disponible():
    # No debe reventar en una maquina sin GPU: el proyecto tiene que
    # poder desarrollarse tambien sin tarjeta.
    t = Transcriber(STTConfig(model_size="tiny", device="cuda"))
    assert t.device in ("cuda", "cpu")
```

- [ ] **Paso 4: Correr el test y verificar que falla**

```bash
pytest tests/test_stt.py -v
```

Esperado: `ModuleNotFoundError: No module named 'ears.stt'`

- [ ] **Paso 5: Escribir `ears/stt.py`**

```python
"""
Transcripcion con faster-whisper.

En Windows, faster-whisper necesita cublas64_12.dll y cudnn_ops64_9.dll,
que pip instala dentro de site-packages/nvidia/ pero no agrega al PATH.
_registrar_dlls_cuda() lo arregla; si aun asi falla, se cae a CPU.
"""

import logging
import os
import site
import sys
from pathlib import Path

import numpy as np

from core.config import STTConfig

log = logging.getLogger(__name__)


def _registrar_dlls_cuda() -> None:
    """Anade las DLLs de cuBLAS y cuDNN al buscador de DLLs de Windows."""
    if sys.platform != "win32":
        return

    for paquete in ("nvidia/cublas/bin", "nvidia/cudnn/bin"):
        for base in site.getsitepackages():
            ruta = Path(base) / paquete
            if ruta.is_dir():
                os.add_dll_directory(str(ruta))
                log.debug("DLLs registradas: %s", ruta)


_registrar_dlls_cuda()

from faster_whisper import WhisperModel  # noqa: E402  (despues de las DLLs)


class Transcriber:
    """Convierte audio int16 a 16 kHz en texto."""

    def __init__(self, config: STTConfig) -> None:
        self._config = config
        self.device = config.device

        try:
            self._modelo = WhisperModel(
                config.model_size,
                device=config.device,
                compute_type=config.compute_type,
            )
        except Exception as error:
            log.warning(
                "No pude cargar Whisper en %s (%s). Cayendo a CPU con int8.",
                config.device,
                error,
            )
            self.device = "cpu"
            self._modelo = WhisperModel(
                config.model_size, device="cpu", compute_type="int8"
            )

        log.info("Whisper '%s' cargado en %s", config.model_size, self.device)

    def transcribir(self, audio: np.ndarray) -> tuple[str, float]:
        """Devuelve (texto, duracion_en_segundos).

        Whisper espera float32 en [-1, 1]; la captura entrega int16.
        """
        muestras = audio.astype(np.float32) / 32768.0
        duracion = len(muestras) / 16000.0

        segmentos, _ = self._modelo.transcribe(
            muestras,
            language=self._config.language,  # fijarlo es mas rapido y preciso
            vad_filter=True,                 # descarta silencios de los bordes
            beam_size=5,
        )

        texto = " ".join(s.text.strip() for s in segmentos).strip()
        return texto, duracion
```

- [ ] **Paso 6: Correr el test y verificar que pasa**

```bash
pytest tests/test_stt.py -v
```

Esperado: 3 passed. **Anotar en qué dispositivo cargó** — lo dice el log.
Si dice `cpu` habiendo GPU, revisar que `nvidia-cublas-cu12` esté instalado.

- [ ] **Paso 7: Medir la latencia**

```bash
python -c "
import time, numpy as np, soundfile as sf
from core.config import cargar_config
from ears.stt import Transcriber
t = Transcriber(cargar_config().stt)
a, _ = sf.read('tests/fixtures/audio/hola_jarvis.wav', dtype='int16')
t.transcribir(a)  # calentar
inicio = time.perf_counter()
texto, _ = t.transcribir(a)
print(f'{(time.perf_counter()-inicio)*1000:.0f} ms  ->  {texto!r}')
"
```

Esperado en la RTX 4050 con `small`: **200-400 ms**. Si supera 2 s, está en CPU.

- [ ] **Paso 8: Commit y PR**

```bash
git add ears/stt.py tests/test_stt.py tests/fixtures/audio/ requirements.txt
git commit -m "feat(ears): transcripcion con faster-whisper y fallback a CPU"
git push -u origin hemsy/ears-stt
gh pr create --fill
```

---

### Tarea 1.H4: `voice/` — síntesis de voz con Piper

**Rama:** `hemsy/voice-piper`

**Archivos:**
- Crear: `voice/base.py`, `voice/piper_tts.py`
- Modificar: `requirements.txt`
- Test: `tests/test_tts.py`

**Interfaces:**
- Consume: `core.config.TTSConfig`
- Produce: `TTSEngine` (Protocol) con `async decir(texto)`; `PiperTTS(config)`

- [ ] **Paso 1: Añadir dependencia y descargar la voz**

```
piper-tts>=1.2
soundfile>=0.12
```

Descargar de `https://huggingface.co/rhasspy/piper-voices` los dos archivos de
`es_MX-claude-high` (`.onnx` y `.onnx.json`) a `models/piper/`.

- [ ] **Paso 2: Escribir el test que falla**

`tests/test_tts.py`:

```python
from pathlib import Path

import pytest

from core.config import TTSConfig
from voice.base import TTSEngine
from voice.piper_tts import PiperTTS

MODELO = Path("models/piper/es_MX-claude-high.onnx")


def test_piper_cumple_el_protocolo():
    assert issubclass(PiperTTS, TTSEngine) or hasattr(PiperTTS, "decir")


@pytest.mark.skipif(not MODELO.exists(), reason="falta el modelo de Piper")
async def test_sintetiza_a_un_wav(tmp_path):
    tts = PiperTTS(TTSConfig(voice="es_MX-claude-high"))
    salida = tmp_path / "salida.wav"

    tts.sintetizar_a_archivo("Son las tres de la tarde.", salida)

    assert salida.exists()
    assert salida.stat().st_size > 1000  # no es un wav vacio


@pytest.mark.skipif(not MODELO.exists(), reason="falta el modelo de Piper")
async def test_texto_vacio_no_revienta():
    await PiperTTS(TTSConfig(voice="es_MX-claude-high")).decir("")
```

- [ ] **Paso 3: Correr el test y verificar que falla**

```bash
pytest tests/test_tts.py -v
```

Esperado: `ModuleNotFoundError: No module named 'voice.base'`

- [ ] **Paso 4: Escribir `voice/base.py`**

```python
"""Contrato de los motores de sintesis de voz."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSEngine(Protocol):
    """Dice un texto en voz alta. Bloquea hasta terminar de hablar."""

    async def decir(self, texto: str) -> None: ...
```

- [ ] **Paso 5: Escribir `voice/piper_tts.py`**

```python
"""
Sintesis local con Piper.

Corre en ONNX sobre CPU en menos de 100 ms, asi que no compite por la GPU
con Whisper. La sintesis es bloqueante, asi que va a un hilo aparte para no
congelar el loop de asyncio mientras Jarvis habla.
"""

import asyncio
import logging
import wave
from pathlib import Path

import sounddevice as sd
import soundfile as sf
from piper.voice import PiperVoice

from core.config import TTSConfig

log = logging.getLogger(__name__)

_DIRECTORIO_VOCES = Path("models/piper")


class PiperTTS:
    """Motor de voz local."""

    def __init__(self, config: TTSConfig) -> None:
        modelo = _DIRECTORIO_VOCES / f"{config.voice}.onnx"
        if not modelo.is_file():
            raise FileNotFoundError(
                f"No encuentro la voz {modelo}. Descargala de "
                "https://huggingface.co/rhasspy/piper-voices"
            )
        self._voz = PiperVoice.load(str(modelo))

    def sintetizar_a_archivo(self, texto: str, destino: Path) -> None:
        """Escribe el WAV. Sincrono: se usa desde tests y desde decir()."""
        with wave.open(str(destino), "wb") as wav:
            self._voz.synthesize(texto, wav)

    def _decir_bloqueante(self, texto: str) -> None:
        temporal = Path("_tts_temp.wav")
        try:
            self.sintetizar_a_archivo(texto, temporal)
            audio, frecuencia = sf.read(temporal, dtype="int16")
            sd.play(audio, frecuencia)
            sd.wait()
        finally:
            temporal.unlink(missing_ok=True)

    async def decir(self, texto: str) -> None:
        """Dice el texto y espera a que termine."""
        if not texto.strip():
            return
        await asyncio.to_thread(self._decir_bloqueante, texto)
```

- [ ] **Paso 6: Correr el test y verificar que pasa**

```bash
pytest tests/test_tts.py -v
```

Esperado: 3 passed

- [ ] **Paso 7: Escuchar cómo suena**

```bash
python -c "
import asyncio
from core.config import cargar_config
from voice.piper_tts import PiperTTS
asyncio.run(PiperTTS(cargar_config().tts).decir('Hola Rafael, soy Jarvis. Son las tres de la tarde.'))
"
```

Si la voz no convence, `edge-tts` suena mejor a cambio de necesitar internet y ~500 ms más.
Se implementa como `voice/edge_tts.py` detrás del mismo Protocol, sin tocar nada más.

- [ ] **Paso 8: Commit y PR**

```bash
git add voice/ tests/test_tts.py requirements.txt
git commit -m "feat(voice): sintesis local con Piper"
git push -u origin hemsy/voice-piper
gh pr create --fill
```

---

### Tarea 1.H5: `ui/console.py` — estados y latencias en consola

**Rama:** `hemsy/ui-console`

**Archivos:**
- Crear: `ui/console.py`
- Test: `tests/test_ui_console.py`

**Interfaces:**
- Consume: `core.bus.EventBus`, todos los eventos
- Produce: `ConsoleUI(bus)` — se suscribe sola al construirse

- [ ] **Paso 1: Escribir el test que falla**

`tests/test_ui_console.py`:

```python
from core.bus import EventBus
from core.events import SpeechTranscribed, StateChanged, WakeDetected
from ui.console import ConsoleUI


async def test_muestra_los_cambios_de_estado(capsys):
    bus = EventBus()
    ConsoleUI(bus)

    await bus.publish(StateChanged(old="idle", new="listening"))

    assert "listening" in capsys.readouterr().out.lower()


async def test_muestra_la_transcripcion(capsys):
    bus = EventBus()
    ConsoleUI(bus)

    await bus.publish(SpeechTranscribed(text="qué hora es", language="es", duration_s=1.2))

    assert "qué hora es" in capsys.readouterr().out


async def test_muestra_el_origen_de_la_activacion(capsys):
    bus = EventBus()
    ConsoleUI(bus)

    await bus.publish(WakeDetected(source="clap", confidence=0.9))

    assert "clap" in capsys.readouterr().out.lower()
```

- [ ] **Paso 2: Correr el test y verificar que falla**

```bash
pytest tests/test_ui_console.py -v
```

Esperado: `ModuleNotFoundError: No module named 'ui.console'`

- [ ] **Paso 3: Escribir `ui/console.py`**

```python
"""
Interfaz de consola (peldano 1 de PLAN.md §10).

Muestra el estado y las latencias, que es lo que mas se depura mientras se
construye el pipeline. La bandeja del sistema llega en la Fase 2.
"""

import time

from rich.console import Console

from core.bus import EventBus
from core.events import (
    ErrorOccurred,
    SpeakRequested,
    SpeechTranscribed,
    StateChanged,
    WakeDetected,
)

_COLOR_POR_ESTADO = {
    "idle": "dim",
    "listening": "bold cyan",
    "transcribing": "cyan",
    "thinking": "yellow",
    "acting": "magenta",
    "speaking": "bold green",
}


class ConsoleUI:
    """Pinta los eventos del bus en la consola."""

    def __init__(self, bus: EventBus, console: Console | None = None) -> None:
        self._console = console or Console()
        self._inicio_ciclo: float | None = None

        bus.subscribe(WakeDetected, self._al_activarse)
        bus.subscribe(StateChanged, self._al_cambiar_estado)
        bus.subscribe(SpeechTranscribed, self._al_transcribir)
        bus.subscribe(SpeakRequested, self._al_hablar)
        bus.subscribe(ErrorOccurred, self._al_fallar)

    def _al_activarse(self, evento: WakeDetected) -> None:
        self._inicio_ciclo = time.monotonic()
        self._console.print(
            f"[bold cyan]●[/] activado por [bold]{evento.source}[/] "
            f"([dim]{evento.confidence:.2f}[/])"
        )

    def _al_cambiar_estado(self, evento: StateChanged) -> None:
        color = _COLOR_POR_ESTADO.get(evento.new, "white")
        self._console.print(f"  [{color}]{evento.new}[/]")

    def _al_transcribir(self, evento: SpeechTranscribed) -> None:
        self._console.print(f'  [white]"{evento.text}"[/] [dim]({evento.duration_s:.1f}s)[/]')

    def _al_hablar(self, evento: SpeakRequested) -> None:
        latencia = ""
        if self._inicio_ciclo is not None:
            latencia = f" [dim]({(time.monotonic() - self._inicio_ciclo) * 1000:.0f} ms)[/]"
            self._inicio_ciclo = None
        self._console.print(f"  [bold green]Jarvis:[/] {evento.text}{latencia}")

    def _al_fallar(self, evento: ErrorOccurred) -> None:
        self._console.print(f"  [bold red]✗ {evento.where}:[/] {evento.message}")
```

- [ ] **Paso 4: Correr el test y verificar que pasa**

```bash
pytest tests/test_ui_console.py -v
```

Esperado: 3 passed

- [ ] **Paso 5: Commit y PR**

```bash
git add ui/console.py tests/test_ui_console.py
git commit -m "feat(ui): salida de consola con estados y latencias"
git push -u origin hemsy/ui-console
gh pr create --fill
```

---

## Track de Rafael — `brain/`, `skills/`

Todo este track se desarrolla con `python main.py --text-mode`. **No hace falta micrófono
ni esperar a que Hemsy termine nada.**

---

### Tarea 1.R1: `brain/registry.py` — registro de skills

**Rama:** `rafael/brain-registry`

**Archivos:**
- Crear: `brain/registry.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consume: `skills.base.Skill`, `skills.base.tool_schema`
- Produce: `SkillRegistry` con `registrar(skill)`, `obtener(nombre)`, `tools_para_openai()`,
  `async ejecutar(nombre, argumentos: dict) -> SkillResult`

`ejecutar()` es la frontera de seguridad: valida los argumentos que vengan del LLM contra
el modelo pydantic **antes** de ejecutar nada (PLAN.md §1).

- [ ] **Paso 1: Escribir el test que falla**

`tests/test_registry.py`:

```python
import pytest
from pydantic import BaseModel

from brain.registry import SkillRegistry
from skills.base import SkillResult
from skills.ping import PingSkill


class SumaParams(BaseModel):
    a: int
    b: int


class SumaSkill:
    name = "sumar"
    description = "Suma dos numeros"
    params_model = SumaParams

    async def execute(self, params: SumaParams) -> SkillResult:
        return SkillResult(ok=True, speech=f"{params.a + params.b}")


def test_registrar_y_obtener():
    registro = SkillRegistry()
    registro.registrar(PingSkill())
    assert registro.obtener("ping") is not None


def test_obtener_una_skill_inexistente_devuelve_none():
    assert SkillRegistry().obtener("no_existe") is None


def test_no_deja_registrar_dos_skills_con_el_mismo_nombre():
    # Dos skills con el mismo nombre haria que el LLM eligiera una al azar.
    registro = SkillRegistry()
    registro.registrar(PingSkill())
    with pytest.raises(ValueError, match="ping"):
        registro.registrar(PingSkill())


def test_tools_para_openai_incluye_todas_las_skills():
    registro = SkillRegistry()
    registro.registrar(PingSkill())
    registro.registrar(SumaSkill())

    nombres = {t["function"]["name"] for t in registro.tools_para_openai()}
    assert nombres == {"ping", "sumar"}


async def test_ejecutar_valida_y_corre_la_skill():
    registro = SkillRegistry()
    registro.registrar(SumaSkill())

    resultado = await registro.ejecutar("sumar", {"a": 2, "b": 3})

    assert resultado.ok is True
    assert resultado.speech == "5"


async def test_ejecutar_rechaza_argumentos_invalidos_sin_correr_la_skill():
    # Esta es la barrera de seguridad: lo que devuelve el LLM se valida
    # ANTES de ejecutar nada (PLAN.md §1).
    registro = SkillRegistry()
    registro.registrar(SumaSkill())

    resultado = await registro.ejecutar("sumar", {"a": "no soy un numero"})

    assert resultado.ok is False
    assert "parámetros" in resultado.speech.lower()


async def test_ejecutar_una_skill_inexistente_devuelve_error():
    resultado = await SkillRegistry().ejecutar("inventada", {})
    assert resultado.ok is False


async def test_una_skill_que_revienta_no_tumba_a_jarvis():
    class SkillRota:
        name = "rota"
        description = "Falla siempre"
        params_model = SumaParams

        async def execute(self, params):
            raise RuntimeError("boom")

    registro = SkillRegistry()
    registro.registrar(SkillRota())

    resultado = await registro.ejecutar("rota", {"a": 1, "b": 2})

    assert resultado.ok is False
```

- [ ] **Paso 2: Correr el test y verificar que falla**

```bash
pytest tests/test_registry.py -v
```

Esperado: `ModuleNotFoundError: No module named 'brain.registry'`

- [ ] **Paso 3: Escribir `brain/registry.py`**

```python
"""
Registro y despacho de skills.

ejecutar() es la frontera de seguridad del proyecto: los argumentos que
propone el LLM se validan contra el modelo pydantic ANTES de que se ejecute
una sola linea de la skill (PLAN.md §1).
"""

import logging
from typing import Any

from pydantic import ValidationError

from skills.base import Skill, SkillResult, tool_schema

log = logging.getLogger(__name__)


class SkillRegistry:
    """Catalogo de lo que Jarvis sabe hacer."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def registrar(self, skill: Skill) -> None:
        """Anade una skill. Falla si el nombre ya existe."""
        if skill.name in self._skills:
            raise ValueError(f"Ya hay una skill registrada con el nombre '{skill.name}'")
        self._skills[skill.name] = skill
        log.debug("Skill registrada: %s", skill.name)

    def obtener(self, nombre: str) -> Skill | None:
        return self._skills.get(nombre)

    def tools_para_openai(self) -> list[dict[str, Any]]:
        """El array 'tools' que se le manda al LLM, derivado de las skills."""
        return [tool_schema(s) for s in self._skills.values()]

    async def ejecutar(self, nombre: str, argumentos: dict[str, Any]) -> SkillResult:
        """Valida los argumentos y ejecuta. Nunca lanza excepcion."""
        skill = self._skills.get(nombre)
        if skill is None:
            log.warning("El LLM pidió una skill inexistente: %s", nombre)
            return SkillResult(ok=False, speech="No sé hacer eso.")

        try:
            params = skill.params_model(**argumentos)
        except ValidationError as error:
            log.warning("Parámetros inválidos para %s: %s", nombre, error)
            return SkillResult(
                ok=False, speech="No entendí bien los parámetros de esa orden."
            )

        try:
            return await skill.execute(params)
        except Exception:
            log.exception("La skill %s falló", nombre)
            return SkillResult(ok=False, speech="Algo falló al hacer eso.")
```

- [ ] **Paso 4: Correr el test y verificar que pasa**

```bash
pytest tests/test_registry.py -v
```

Esperado: 8 passed

- [ ] **Paso 5: Commit y PR**

```bash
git add brain/registry.py tests/test_registry.py
git commit -m "feat(brain): registro de skills con validacion de parametros"
git push -u origin rafael/brain-registry
gh pr create --fill
```

---

### Tarea 1.R2: `brain/router.py` — reglas rápidas

**Rama:** `rafael/brain-router`

**Archivos:**
- Crear: `brain/router.py`
- Test: `tests/test_router.py`

**Interfaces:**
- Consume: nada de otros módulos
- Produce: `RuleRouter` con `resolver(texto) -> tuple[str, dict] | None`

Atiende los comandos frecuentes en 0 ms y $0. Lo que no matchea sube al LLM en la Fase 2.

- [ ] **Paso 1: Escribir el test que falla**

`tests/test_router.py`:

```python
import pytest

from brain.router import RuleRouter


@pytest.mark.parametrize(
    "frase",
    ["qué hora es", "que hora es", "¿Qué hora es?", "dime la hora", "la hora"],
)
def test_reconoce_las_variantes_de_preguntar_la_hora(frase):
    # La transcripcion de Whisper varia en tildes y puntuacion, asi que
    # normalizar es obligatorio, no cosmetico.
    assert RuleRouter().resolver(frase) == ("decir_hora", {})


@pytest.mark.parametrize("frase", ["qué día es hoy", "que dia es", "la fecha"])
def test_reconoce_las_variantes_de_preguntar_la_fecha(frase):
    assert RuleRouter().resolver(frase) == ("decir_fecha", {})


@pytest.mark.parametrize("frase", ["hola", "hola jarvis", "buenas"])
def test_reconoce_el_saludo(frase):
    assert RuleRouter().resolver(frase) == ("saludar", {})


def test_devuelve_none_si_ninguna_regla_matchea():
    # None significa "esto es para el LLM", no "no se puede".
    assert RuleRouter().resolver("ponme algo tranquilo para estudiar") is None


def test_ignora_mayusculas_tildes_y_signos():
    assert RuleRouter().resolver("  ¿QUÉ HORA ES?  ") == ("decir_hora", {})


def test_el_texto_vacio_devuelve_none():
    assert RuleRouter().resolver("") is None
```

- [ ] **Paso 2: Correr el test y verificar que falla**

```bash
pytest tests/test_router.py -v
```

Esperado: `ModuleNotFoundError: No module named 'brain.router'`

- [ ] **Paso 3: Escribir `brain/router.py`**

```python
"""
Router de reglas: atiende los comandos frecuentes sin llamar al LLM.

Compra tres cosas: latencia cero en lo que mas se usa, funcionamiento sin
internet para lo basico, y menos gasto de creditos (PLAN.md §5.2).

Lo que no matchea devuelve None y sube al LLM. None significa "esto es para
el modelo", nunca "no se puede".
"""

import re
import unicodedata

# (patron, nombre_de_skill). El orden importa: gana el primero que matchea.
_REGLAS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(que hora es|dime la hora|la hora)\b"), "decir_hora"),
    (re.compile(r"\b(que dia es|que fecha|la fecha)\b"), "decir_fecha"),
    (re.compile(r"^\s*(hola|buenas|buenos dias|buenas tardes)\b"), "saludar"),
]


def _normalizar(texto: str) -> str:
    """Minusculas, sin tildes y sin signos.

    Whisper transcribe la misma frase con o sin tildes y con o sin signos
    de interrogacion segun la entonacion, asi que comparar en crudo falla.
    """
    sin_tildes = "".join(
        c
        for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^\w\s]", "", sin_tildes).strip()


class RuleRouter:
    """Resuelve comandos frecuentes por coincidencia de patron."""

    def resolver(self, texto: str) -> tuple[str, dict] | None:
        """Devuelve (nombre_de_skill, argumentos) o None si es para el LLM."""
        if not texto.strip():
            return None

        normalizado = _normalizar(texto)
        for patron, skill in _REGLAS:
            if patron.search(normalizado):
                return skill, {}

        return None
```

- [ ] **Paso 4: Correr el test y verificar que pasa**

```bash
pytest tests/test_router.py -v
```

Esperado: 16 passed

- [ ] **Paso 5: Commit y PR**

```bash
git add brain/router.py tests/test_router.py
git commit -m "feat(brain): router de reglas para comandos frecuentes"
git push -u origin rafael/brain-router
gh pr create --fill
```

---

### Tarea 1.R3: `skills/system.py` — hora, fecha y saludo

**Rama:** `rafael/skills-system`

**Archivos:**
- Crear: `skills/system.py`
- Test: `tests/test_skills_system.py`

**Interfaces:**
- Consume: `skills.base.SkillResult`
- Produce: `DecirHoraSkill`, `DecirFechaSkill`, `SaludarSkill`

- [ ] **Paso 1: Escribir el test que falla**

`tests/test_skills_system.py`:

```python
from datetime import datetime

from skills.system import DecirFechaSkill, DecirHoraSkill, SaludarSkill


async def test_decir_hora_responde_con_la_hora_actual():
    resultado = await DecirHoraSkill().execute(DecirHoraSkill.params_model())
    ahora = datetime.now()

    assert resultado.ok is True
    assert str(ahora.hour % 12 or 12) in resultado.speech


async def test_decir_hora_habla_en_formato_natural():
    # "son las 3 y 5", no "15:05:32" — lo tiene que decir una voz.
    resultado = await DecirHoraSkill().execute(DecirHoraSkill.params_model())
    assert ":" not in resultado.speech
    assert "son las" in resultado.speech.lower()


async def test_decir_fecha_incluye_el_dia_del_mes():
    resultado = await DecirFechaSkill().execute(DecirFechaSkill.params_model())
    assert str(datetime.now().day) in resultado.speech


async def test_decir_fecha_esta_en_espanol():
    meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    resultado = await DecirFechaSkill().execute(DecirFechaSkill.params_model())
    assert any(m in resultado.speech.lower() for m in meses)


async def test_saludar_responde_algo():
    resultado = await SaludarSkill().execute(SaludarSkill.params_model())
    assert resultado.ok is True
    assert len(resultado.speech) > 0


def test_los_nombres_coinciden_con_los_del_router():
    # Si estos nombres no coinciden con brain/router.py, el router resuelve
    # una skill que el registro no encuentra y Jarvis responde "no se hacer eso".
    assert DecirHoraSkill.name == "decir_hora"
    assert DecirFechaSkill.name == "decir_fecha"
    assert SaludarSkill.name == "saludar"
```

- [ ] **Paso 2: Correr el test y verificar que falla**

```bash
pytest tests/test_skills_system.py -v
```

Esperado: `ModuleNotFoundError: No module named 'skills.system'`

- [ ] **Paso 3: Escribir `skills/system.py`**

```python
"""
Skills del sistema: hora, fecha y saludo.

Todo lo que devuelven en 'speech' lo va a pronunciar una voz, asi que se
escribe como se habla: "son las tres y cinco", no "15:05".
"""

import random
from datetime import datetime

from pydantic import BaseModel

from skills.base import SkillResult

_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")

_SALUDOS = (
    "Hola, ¿en qué te ayudo?",
    "Acá estoy.",
    "Hola. Decime.",
)


class SinParametros(BaseModel):
    """Para skills que no necesitan argumentos."""


class DecirHoraSkill:
    name = "decir_hora"
    description = "Dice la hora actual."
    params_model = SinParametros

    async def execute(self, params: SinParametros) -> SkillResult:
        ahora = datetime.now()
        hora = ahora.hour % 12 or 12
        franja = "de la mañana" if ahora.hour < 12 else (
            "de la tarde" if ahora.hour < 20 else "de la noche"
        )

        if ahora.minute == 0:
            texto = f"Son las {hora} en punto {franja}."
        else:
            texto = f"Son las {hora} y {ahora.minute} {franja}."

        return SkillResult(ok=True, speech=texto, data={"iso": ahora.isoformat()})


class DecirFechaSkill:
    name = "decir_fecha"
    description = "Dice la fecha de hoy."
    params_model = SinParametros

    async def execute(self, params: SinParametros) -> SkillResult:
        hoy = datetime.now()
        texto = f"Hoy es {_DIAS[hoy.weekday()]} {hoy.day} de {_MESES[hoy.month - 1]}."

        return SkillResult(ok=True, speech=texto, data={"iso": hoy.date().isoformat()})


class SaludarSkill:
    name = "saludar"
    description = "Responde a un saludo del usuario."
    params_model = SinParametros

    async def execute(self, params: SinParametros) -> SkillResult:
        return SkillResult(ok=True, speech=random.choice(_SALUDOS))
```

- [ ] **Paso 4: Correr el test y verificar que pasa**

```bash
pytest tests/test_skills_system.py -v
```

Esperado: 6 passed

- [ ] **Paso 5: Commit y PR**

```bash
git add skills/system.py tests/test_skills_system.py
git commit -m "feat(skills): hora, fecha y saludo"
git push -u origin rafael/skills-system
gh pr create --fill
```

---

### Tarea 1.R4: Cablear el router y el registro en `main.py`

**Rama:** `rafael/brain-cableado`

**Archivos:**
- Modificar: `main.py`
- Test: `tests/test_text_mode.py` (ampliar)

**Interfaces:**
- Consume: `brain.registry.SkillRegistry`, `brain.router.RuleRouter`, `skills.system`
- Produce: `JarvisApp` con el pipeline real

> Requiere que las tareas 1.R1, 1.R2 y 1.R3 estén fusionadas en `main`.
> `git checkout main && git pull origin main` antes de empezar.

- [ ] **Paso 1: Ampliar el test**

Añadir a `tests/test_text_mode.py`:

```python
async def test_responde_la_hora_por_texto():
    app = JarvisApp(bus=EventBus())
    respuesta = await app.procesar_texto("qué hora es")
    assert "son las" in respuesta.lower()


async def test_responde_la_fecha_por_texto():
    app = JarvisApp(bus=EventBus())
    assert "hoy es" in (await app.procesar_texto("qué día es hoy")).lower()


async def test_responde_al_saludo():
    app = JarvisApp(bus=EventBus())
    assert len(await app.procesar_texto("hola")) > 0


async def test_una_orden_sin_regla_avisa_que_falta_el_llm():
    # En la Fase 2 esto sube al LLM. Por ahora tiene que decirlo claro,
    # no quedarse mudo.
    app = JarvisApp(bus=EventBus())
    respuesta = await app.procesar_texto("ponme algo tranquilo para estudiar")
    assert respuesta
```

- [ ] **Paso 2: Correr el test y verificar que falla**

```bash
pytest tests/test_text_mode.py -v
```

Esperado: fallan los 4 nuevos; `procesar_texto` no conoce esas órdenes.

- [ ] **Paso 3: Reescribir `JarvisApp` en `main.py`**

Reemplazar la clase `JarvisApp` de la tarea 0.7 por:

```python
class JarvisApp:
    """Cablea el bus, la maquina de estados, el router y las skills."""

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.maquina = StateMachine(bus)
        self.router = RuleRouter()
        self.registro = SkillRegistry()

        for skill in (
            PingSkill(),
            DecirHoraSkill(),
            DecirFechaSkill(),
            SaludarSkill(),
        ):
            self.registro.registrar(skill)

    async def procesar_texto(self, texto: str) -> str:
        """Desde texto transcrito hasta la respuesta hablada."""
        await self.maquina.transition_to(State.LISTENING)
        await self.bus.publish(
            SpeechTranscribed(text=texto, language="es", duration_s=0.0)
        )
        await self.maquina.transition_to(State.TRANSCRIBING)
        await self.maquina.transition_to(State.THINKING)

        resuelto = self.router.resolver(texto)

        if resuelto is None:
            # En la Fase 2, aca se llama al LLM con tool calling.
            resultado = SkillResult(
                ok=False,
                speech="Todavía no sé responder eso. Me falta el cerebro.",
            )
        else:
            nombre, argumentos = resuelto
            await self.maquina.transition_to(State.ACTING)
            resultado = await self.registro.ejecutar(nombre, argumentos)

        await self.maquina.transition_to(State.SPEAKING)
        await self.bus.publish(SpeakRequested(text=resultado.speech))
        await self.maquina.transition_to(State.IDLE)

        return resultado.speech
```

Actualizar los imports al principio de `main.py`:

```python
from brain.registry import SkillRegistry
from brain.router import RuleRouter
from skills.ping import PingSkill
from skills.system import DecirFechaSkill, DecirHoraSkill, SaludarSkill
```

- [ ] **Paso 4: Correr el test y verificar que pasa**

```bash
pytest tests/test_text_mode.py -v
```

Esperado: 9 passed

- [ ] **Paso 5: Probarlo a mano**

```bash
python main.py --text-mode
```

Escribir: `qué hora es`, `hola`, `la fecha`, `ponme música`. Las tres primeras responden;
la cuarta avisa que falta el cerebro.

- [ ] **Paso 6: Commit y PR**

```bash
git add main.py tests/test_text_mode.py
git commit -m "feat(brain): cablear router y registro en el pipeline"
git push -u origin rafael/brain-cableado
gh pr create --fill
```

---

### Tarea 1.FINAL: Integración con audio (los dos juntos)

**Rama:** `rafael/integracion-fase-1`

Requiere **todas** las tareas anteriores fusionadas. Es el momento en que las dos mitades
se tocan por primera vez, así que conviene hacerlo en una llamada.

**Archivos:**
- Modificar: `main.py`

- [ ] **Paso 1: Añadir el pipeline de audio a `main.py`**

```python
async def bucle_audio(app: JarvisApp, config) -> None:
    """Pipeline real: microfono -> wake word -> Whisper -> skill -> voz."""
    from ears.capture import AudioCapture
    from ears.stt import Transcriber
    from ears.wakeword import WakeWordDetector
    from voice.piper_tts import PiperTTS

    detector = WakeWordDetector(config.wakeword)
    transcriptor = Transcriber(config.stt)
    tts = PiperTTS(config.tts)

    async def al_pedir_voz(evento: SpeakRequested) -> None:
        await tts.decir(evento.text)
        await app.bus.publish(SpeakFinished())

    app.bus.subscribe(SpeakRequested, al_pedir_voz)

    def al_llegar_bloque(bloque) -> None:
        # Gate half-duplex: mientras Jarvis habla no se escucha a si mismo.
        if not app.maquina.puede_escuchar:
            return

        confianza = detector.procesar(bloque)
        if confianza is not None:
            app.bus.publish_threadsafe(
                WakeDetected(source="wakeword", confidence=confianza)
            )

    captura = AudioCapture(config.audio, on_block=al_llegar_bloque)

    async def al_activarse(evento: WakeDetected) -> None:
        # Fase 1: se graban 4 segundos fijos tras la wake word.
        # La Fase 2 mete el VAD para cortar cuando el usuario deja de hablar.
        await asyncio.sleep(4.0)
        audio = captura.ultimo_segundo_n(4)
        texto, duracion = await asyncio.to_thread(transcriptor.transcribir, audio)
        if texto:
            await app.procesar_texto(texto)

    app.bus.subscribe(WakeDetected, al_activarse)

    captura.start()
    console.print("[bold cyan]Jarvis escuchando.[/] Decí 'hey jarvis'. Ctrl-C para salir.")
    try:
        await asyncio.Event().wait()
    finally:
        captura.stop()
```

- [ ] **Paso 2: Añadir `ultimo_segundo_n()` a `ears/capture.py`**

Generaliza `ultimo_segundo()`. Requiere un PR de Hemsy o su visto bueno explícito, porque
toca su carpeta.

```python
    def ultimo_segundo_n(self, segundos: int) -> np.ndarray:
        """Los ultimos N segundos de audio, o todo lo que haya si es menos."""
        if not self._buffer:
            return np.zeros(0, dtype=np.int16)

        audio = np.concatenate(list(self._buffer))
        return audio[-self._config.sample_rate * segundos :]
```

- [ ] **Paso 3: Conectar `ConsoleUI` y el modo audio en `main()`**

```python
    bus = EventBus()
    bus.bind_loop(asyncio.get_running_loop())
    app = JarvisApp(bus=bus)
    ConsoleUI(bus)

    if args.text_mode:
        await bucle_texto(app)
    else:
        await bucle_audio(app, cargar_config())
```

- [ ] **Paso 4: LA DEMO — el criterio de la Fase 1**

```bash
python main.py
```

Decir: **"hey jarvis"**, esperar el cambio de estado en consola, decir **"qué hora es"**.

Esperado: Jarvis responde en voz alta con la hora, y la consola muestra la latencia total.

- [ ] **Paso 5: Correr la suite completa**

```bash
pytest -v
```

- [ ] **Paso 6: Commit, PR y etiqueta**

```bash
git add main.py ears/capture.py
git commit -m "feat: integrar el pipeline de audio completo"
git push -u origin rafael/integracion-fase-1
gh pr create --fill
```

Después de fusionar:

```bash
git checkout main && git pull origin main
git tag fase-1 && git push origin fase-1
```

---

## ✅ Fase 1 terminada cuando

- Decir *"oye Jarvis, qué hora es"* produce una respuesta hablada
- `pytest` pasa entero
- La latencia total desde el fin de la frase hasta la voz es **menor a 2 segundos**
- Está la etiqueta `fase-1` en `main`

**Sin OpenAI todavía.** Este hito ya es un producto usable, y es donde aparecen el 90% de
los problemas reales: latencia, eco, ruido y dispositivos de audio.

---

## Qué sigue

La Fase 2 (PLAN.md §8) mete el cerebro de verdad —tool calling contra OpenAI— y las
palmadas, más el VAD para no grabar 4 segundos fijos. Se planifica cuando la Fase 1 esté
etiquetada, no antes: lo que se aprenda acá va a cambiar decisiones de la siguiente.
