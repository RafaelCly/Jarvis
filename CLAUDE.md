# Instrucciones para Claude — Proyecto JARVIS

Asistente de voz local para Windows 11: palmadas y wake word para activarlo, órdenes
en español, acciones sobre el sistema, tareas y Spotify.

Proyecto de una sola persona (Rafael, `@RafaelCly`).

**La fuente de verdad del diseño es [PLAN.md](PLAN.md).** Este archivo es el resumen
operativo. Ante cualquier duda de arquitectura, presupuesto o alcance, leé PLAN.md antes
de proponer nada.

---

## 1. Cómo arrancar una sesión

**Hacé estos cuatro pasos antes de proponer nada.** No los saltes aunque te digan "seguí":
sin ellos podés proponer una tarea cuyo prerrequisito no existe todavía.

1. **`git pull origin main`** → traé lo último.
2. **Averiguá qué está hecho, no lo supongas:**

   ```bash
   git log --oneline -15     # qué se fusionó ya
   pytest -q                 # ¿main está sano?
   ```

3. **Abrí el plan vigente** de `docs/superpowers/plans/` y ubicá la primera tarea que
   **no** esté hecha. Verificá que sus prerrequisitos —el bloque `Interfaces: Consume`—
   ya existan en el árbol.
4. **Proponé UNA tarea concreta y esperá confirmación.** Recién después empezá.

Los planes cubren de a una o dos fases. Cuando el plan vigente se termina, **no improvises
la fase siguiente**: se planifica cuando la anterior está etiquetada, porque lo aprendido
cambia decisiones.

| Documento | Para qué |
|---|---|
| [PLAN.md](PLAN.md) | El diseño: por qué cada decisión es como es |
| `docs/superpowers/plans/*.md` | Las tareas concretas: qué archivo crear y en qué orden |
| Este archivo | Cómo trabajar en el repo |

---

## 2. Organización del código

| Carpeta | Responsabilidad |
|---|---|
| `core/` | Eventos, bus, máquina de estados, config. **Las costuras.** |
| `ears/` | Captura, palmadas, wake word, VAD, transcripción |
| `voice/` | Síntesis de voz |
| `ui/` | Consola, bandeja del sistema, HUD |
| `brain/` | Router de reglas, tool calling, registro de skills |
| `skills/` | Las capacidades: archivos, tareas, Spotify, sistema |

**`core/` se toca con cuidado.** Es de lo que depende todo lo demás: un campo nuevo en un
evento puede romper cosas en silencio tres capas más abajo. Los cambios a `core/` van en
su propio commit, nunca mezclados dentro de uno de feature. Así, si algo se rompe, se sabe
en qué commit mirar.

---

## 3. Flujo de trabajo con git

**`main` siempre tiene que funcionar.** Si clonás y ejecutás, arranca.

Rama por tarea o por grupo chico de tareas relacionadas:

```bash
git checkout main && git pull origin main
git checkout -b rafael/brain-tool-calling      # rafael/<área>-<qué>
# ...trabajar, un commit por paso significativo...
git checkout main && git merge --ff-only rafael/brain-tool-calling
git push origin main
```

- Ramas cortas, de 1 a 3 días. Si la tarea es más larga, partila.
- Commits en español, con prefijo de área: `feat(ears):`, `fix(brain):`, `docs:`.
- **Un commit por tarea del plan.** El historial de `main` se lee como la lista de tareas.
- Merge con `--ff-only` para conservar esos commits. No hace falta squash: cada commit
  ya es limpio y corresponde a algo concreto.
- Al cerrar una fase: `git tag fase-N`. Es el punto de retorno seguro.

---

## 4. Stack y comandos

**Python 3.11** — no 3.13 ni 3.14, que tienen wheels incompletos para `onnxruntime`
y `faster-whisper`.

```bash
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

**Configuración:** `config.yaml` está commiteado y trae los valores compartidos.
`config.local.yaml` está en `.gitignore` y trae lo propio de esta máquina —índice de
micrófono, `cuda` vs `cpu`—, para que el repo no lleve rutas ni índices de una
computadora concreta. Los secretos van en `.env`, también ignorado.

---

## 5. Reglas que no se rompen

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
a mono 8 kHz. Se fija por índice explícito en `config.local.yaml`. Ver [PLAN.md §2](PLAN.md).

---

## 6. Al escribir código

- Español en comentarios, docstrings, mensajes de commit y texto que oye el usuario.
  Inglés en nombres de variables, funciones y clases.
- Módulos chicos y con una responsabilidad. Si un archivo crece mucho, está haciendo
  demasiado.
- **Test primero.** Escribir el test, verlo fallar, implementar, verlo pasar, commitear.
- Los módulos de audio se testean con fixtures WAV, sin micrófono. Las skills se testean
  llamando `execute()` directo, sin voz ni LLM. Ver [PLAN.md §8](PLAN.md).
- Antes de añadir una dependencia, agregala a `requirements.txt` en el mismo commit.
