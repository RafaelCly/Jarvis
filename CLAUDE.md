# Instrucciones para Claude — Proyecto JARVIS

Asistente de voz local para Windows 11: palmadas y wake word para activarlo, órdenes
en español, acciones sobre el sistema, tareas y Spotify.

**La fuente de verdad del diseño es [PLAN.md](PLAN.md).** Este archivo es el resumen
operativo. Ante cualquier duda de arquitectura, presupuesto o alcance, leé PLAN.md antes
de proponer nada.

---

## 1. Con quién estás hablando

**Averigualo antes de proponer trabajo.** Somos dos personas con tracks distintos:

```bash
git config user.name
```

| Si es | Track | Carpetas que le tocan |
|---|---|---|
| `RafaelCly` / Rafael | **Cerebro y Manos** | `brain/`, `skills/` |
| `HemsyCA` / Hemsy | **Oídos, Voz e Interfaz** | `ears/`, `voice/`, `ui/` |
| Otro / no coincide | — | **Preguntá antes de seguir** |

**Rafael** construye la orquestación con el LLM: el router de reglas, el tool calling
contra OpenAI, el registro de skills, y las skills de archivos, tareas y Spotify.

**Hemsy** construye todo el camino del audio: captura, detección de palmadas, wake word,
VAD, transcripción con Whisper, síntesis de voz, y la interfaz (bandeja y HUD).

### Respetá los límites del track

No edites archivos del track de la otra persona sin que te lo pidan explícitamente.
Si una tarea parece necesitarlo, **decilo y proponé la alternativa** — normalmente
significa que falta un evento en `core/`, no que haya que cruzar la frontera.

---

## 2. La regla más importante: `core/` es sagrado

`core/events.py` y `skills/base.py` son los contratos que permiten que dos personas
trabajen en paralelo sin pisarse. Todo el riesgo de conflicto del proyecto está ahí.

> **Los cambios a `core/` van en su propio PR, pequeño, primero, y avisando a la otra
> persona.** Nunca mezclados dentro de un PR de feature.

Si durante una tarea hace falta un evento o un campo nuevo:

1. Pará.
2. Decíselo a quien estés ayudando, para que avise a la otra persona.
3. PR mínimo que solo toca `core/`.
4. Fusionar, que ambos hagan `git pull`.
5. Recién entonces seguir con la feature.

Ver [PLAN.md §7.5](PLAN.md).

---

## 3. Flujo de trabajo con git

**Nunca commitees a `main`.** Todo entra por rama y Pull Request.

```bash
git checkout main && git pull origin main
git checkout -b rafael/brain-tool-calling      # <nombre>/<área>-<qué>
# ...trabajar...
git push -u origin rafael/brain-tool-calling
gh pr create --fill
```

- Ramas cortas, de 1 a 3 días. Si la tarea es más larga, partila.
- Una rama = una cosa.
- Commits en español, con prefijo de área: `feat(ears):`, `fix(brain):`, `docs:`.
- El merge es siempre **squash** (ya es la única opción configurada en el repo).
- Revisión cruzada: el PR de uno lo revisa el otro. Es lo que evita que cada mitad del
  código la entienda una sola persona.

Estrategia completa en [PLAN.md §7](PLAN.md).

---

## 4. Cómo arrancar una sesión de trabajo

1. `git config user.name` → identificá el track.
2. `git pull origin main` → traé lo último.
3. Mirá en qué fase estamos ([PLAN.md §8](PLAN.md)) y qué tareas quedan del track.
4. Proponé **una** tarea concreta y esperá confirmación antes de escribir código.
5. Creá la rama antes de tocar archivos.

No arranques a programar sin que la persona confirme qué tarea es. El plan tiene orden
por una razón: cada fase termina en algo demostrable.

---

## 5. Stack y comandos

**Python 3.11** — no 3.13 ni 3.14, que tienen wheels incompletos para `onnxruntime`
y `faster-whisper`.

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

pytest                          # tests
python main.py                  # Jarvis completo
python main.py --text-mode      # sin audio: comandos por teclado
py -3.11 tools_md2pdf.py        # regenerar PLAN.pdf
```

`--text-mode` es la herramienta más útil del proyecto: salta todo el pipeline de audio
y lee órdenes por stdin. Permite desarrollar y depurar el cerebro sin micrófono ni GPU.
Si estás trabajando en `brain/` o `skills/`, usalo siempre.

**Piezas principales:** `sounddevice` · `openWakeWord` · `silero-vad` ·
`faster-whisper` (GPU) · Piper TTS · OpenAI `gpt-4o-mini` con tool calling ·
`spotipy` + SMTC (`winsdk`) · SQLite. Justificación de cada una en
[PLAN.md §4](PLAN.md).

---

## 6. Reglas que no se rompen

**El LLM nunca ejecuta código.** Solo elige el nombre de una función de una lista fija y
rellena parámetros que se validan con pydantic antes de ejecutar nada. Jarvis escucha
todo lo que suena en la habitación —un video de YouTube, una visita—, así que cualquier
audio ambiente es una superficie de ataque.

- Nada de `exec`, `eval`, ni `os.system` con strings que vengan del modelo.
- Sin herramientas destructivas en el catálogo de skills.
- Operaciones de archivos restringidas a una lista blanca de carpetas.

**Nunca commitees `.env`, claves, ni rutas absolutas de una máquina concreta.**
Si una credencial se sube por error: revocarla primero en OpenAI o Spotify, después
limpiar el historial. Borrar el commit no sirve — el repo es público y la clave ya salió.

**El micrófono es el array interno del laptop, nunca unos auriculares Bluetooth.**
Bluetooth conmuta a modo Hands-Free al abrir el micro y degrada toda la salida de audio
a mono 8 kHz. Se fija por índice explícito en `config.yaml`. Ver [PLAN.md §2](PLAN.md).

---

## 7. Al escribir código

- Español en comentarios, docstrings, mensajes de commit y texto que oye el usuario.
  Inglés en nombres de variables, funciones y clases.
- Módulos chicos y con una responsabilidad. Si un archivo crece mucho, está haciendo
  demasiado.
- Los módulos de audio se testean con fixtures WAV, sin micrófono. Las skills se testean
  llamando `execute()` directo, sin voz ni LLM. Ver [PLAN.md §9](PLAN.md).
- Antes de añadir una dependencia, agregala a `requirements.txt` y decilo — toca un
  archivo compartido.
