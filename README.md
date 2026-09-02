# JARVIS

Asistente de voz local para Windows 11. Se activa por palmadas o por wake word,
entiende órdenes en español y ejecuta acciones sobre el sistema, tus tareas y Spotify.

> **Estado: Fase 0 completa.** Los contratos, el bus, la máquina de estados y el modo
> texto ya funcionan. El diseño está en **[PLAN.md](PLAN.md)**.

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
2 años de uso normal. Todo el resto del stack es open source o
freeware. El cálculo está en [PLAN.md §3](PLAN.md).

## Cómo trabajo en el repo

`main` siempre funciona. Una rama por tarea, merge con `--ff-only` para que el historial
se lea como la lista de tareas hechas.

```bash
git checkout main && git pull origin main
git checkout -b rafael/brain-tool-calling     # rafael/<área>-<qué>
# ...trabajar...
git checkout main && git merge --ff-only rafael/brain-tool-calling
```

**Los cambios a `core/` van en su propio commit**, nunca mezclados con una feature: es de
lo que depende todo lo demás, y separarlo es lo que hace que `git bisect` sirva de algo.

Detalle completo en [PLAN.md §7](PLAN.md).

## Puesta en marcha

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp config.local.yaml.example config.local.yaml

pytest                       # 46 tests
python main.py --text-mode   # escribí "ping", responde "pong"
```

La clave de OpenAI todavía no hace falta: llega en la Fase 2, con el tool calling.

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
