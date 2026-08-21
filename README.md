# JARVIS

Asistente de voz local para Windows 11. Se activa por palmadas o por wake word,
entiende órdenes en español y ejecuta acciones sobre el sistema, tus tareas y Spotify.

> **Estado: fase de diseño.** Todavía no hay código. El diseño está cerrado y
> documentado en **[PLAN.md](PLAN.md)** — empezá por ahí.

---

## La idea en una línea

Todo el audio se procesa localmente; la nube solo convierte una frase en español en una
llamada a función. Eso hace que el costo por comando sea de ~$0.0002 y que el micrófono
nunca salga de la máquina.

## Documentación

| Archivo | Qué contiene |
|---|---|
| **[PLAN.md](PLAN.md)** | Diseño completo: arquitectura, stack, división del trabajo, fases, riesgos y presupuesto |
| [PLAN.pdf](PLAN.pdf) | Lo mismo en PDF, para leer o compartir |
| [tools_md2pdf.py](tools_md2pdf.py) | Regenera el PDF cuando cambia el markdown |

## Stack previsto

Python 3.11 · `sounddevice` · `openWakeWord` · `silero-vad` · `faster-whisper` (GPU) ·
Piper TTS · OpenAI `gpt-4o-mini` con *tool calling* · `spotipy` + SMTC · SQLite

Detalle y justificación de cada elección en [PLAN.md §4](PLAN.md).

## Presupuesto

**$5 USD de créditos OpenAI, una sola vez.** Alcanzan para ~21,000 comandos, cerca de
2 años de uso normal entre dos personas. Todo el resto del stack es open source o
freeware. El cálculo está en [PLAN.md §3](PLAN.md).

## Equipo

| | Track | Carpetas |
|---|---|---|
| Persona A | Oídos, Voz e Interfaz | `ears/`, `voice/`, `ui/` |
| Persona B | Cerebro y Manos | `brain/`, `skills/` |

Los contratos compartidos (`core/events.py` y `skills/base.py`) se escriben entre los dos
antes que nada. Ver [PLAN.md §6](PLAN.md).

## Puesta en marcha

Todavía no aplica — no hay código. El checklist de lo que hay que preparar antes de la
primera línea está en [PLAN.md §11](PLAN.md): venv con Python 3.11, instalar
[Everything](https://www.voidtools.com/), crear la app en el Spotify Developer Dashboard
y cargar los créditos de OpenAI.

### Regenerar el PDF

```bash
py -3.11 tools_md2pdf.py
```

Requiere `pip install markdown`. Edge ya viene con Windows 11.

---

## Seguridad

El LLM **nunca ejecuta código**: solo elige el nombre de una función de una lista fija y
rellena parámetros que después se validan con pydantic. Jarvis escucha todo lo que suena
en la habitación, así que cualquier audio ambiente es una superficie de ataque potencial.
Nada de `exec`, nada de shell con strings del modelo, sin herramientas destructivas en el
catálogo, y operaciones de archivos restringidas a una lista blanca de carpetas.

**El archivo `.env` está en `.gitignore` desde el primer commit y nunca debe salir de ahí.**
