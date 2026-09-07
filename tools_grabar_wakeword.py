"""
Graba intentos de wake word a disco y los analiza. Reproducible.

    py -3.11 tools_grabar_wakeword.py                  # graba 45 s y analiza
    py -3.11 tools_grabar_wakeword.py --analizar X.wav # reanaliza sin regrabar

Por que existe: las pruebas en vivo daban resultados incompatibles entre si
(0.23, luego 0.94, luego 0.07) y cada corrida se perdia, asi que no habia
forma de comparar ni de saber si el que cambiaba era el modelo o la
pronunciacion. Grabando a disco, el mismo audio se puede pasar por el modelo
cuantas veces se quiera, con distintos umbrales y sin volver a hablar.

Los WAV quedan en tests/fixtures/audio/, que SI se versiona: son el dataset
que valida esto y, mas adelante, el detector de palmadas (PLAN.md §9).
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

from core.config import cargar_config
from ears.capture import AudioCapture
from ears.wakeword import WakeWordDetector

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DIRECTORIO = Path("tests/fixtures/audio")
DURACION_S = 45
BLOQUE = 1280
FRECUENCIA = 16000


def grabar(config) -> Path:
    """Graba DURACION_S segundos completos y los guarda."""
    DIRECTORIO.mkdir(parents=True, exist_ok=True)
    destino = DIRECTORIO / f"wakeword_{datetime.now():%Y%m%d_%H%M%S}.wav"

    bloques: list[np.ndarray] = []
    inicio = time.monotonic()

    def al_llegar(bloque: np.ndarray) -> None:
        bloques.append(bloque)
        transcurrido = time.monotonic() - inicio
        nivel = float(np.abs(bloque).max())
        marca = "#" * int(min(nivel / 8000, 1.0) * 20)
        print(
            f"\r  {DURACION_S - transcurrido:>4.0f}s  [{marca:<20}] {nivel:>6.0f}",
            end="",
            flush=True,
        )

    print("Decí 'hey jarvis' 10 veces, separadas unos 3 segundos.")
    print("Pronuncialo como te salga natural. Empezá.\n")

    with AudioCapture(config.audio, on_block=al_llegar):
        while time.monotonic() - inicio < DURACION_S:
            time.sleep(0.1)

    audio = np.concatenate(bloques)
    sf.write(destino, audio, FRECUENCIA)
    print(f"\n\nGuardado: {destino}  ({len(audio) / FRECUENCIA:.0f} s)\n")
    return destino


def analizar(ruta: Path, config) -> None:
    """Pasa el WAV por el modelo y muestra donde y cuanto reconocio."""
    audio, frecuencia = sf.read(ruta, dtype="int16")
    if frecuencia != FRECUENCIA:
        sys.exit(f"{ruta} está a {frecuencia} Hz; hacen falta {FRECUENCIA}.")
    if audio.ndim > 1:
        audio = audio[:, 0]

    detector = WakeWordDetector(config.wakeword)
    confianzas: list[float] = []
    niveles: list[float] = []

    for i in range(0, len(audio) - BLOQUE, BLOQUE):
        bloque = audio[i : i + BLOQUE]
        cruda, _ = detector.procesar_con_detalle(bloque)
        confianzas.append(cruda)
        niveles.append(float(np.abs(bloque).max()))

    c = np.array(confianzas)
    segundos_por_bloque = BLOQUE / FRECUENCIA

    print(f"Archivo   : {ruta.name}")
    print(f"Duración  : {len(audio) / FRECUENCIA:.0f} s   bloques: {len(c)}")
    print(f"Nivel máx : {max(niveles):.0f}\n")

    # Picos aislados: un maximo local por encima del ruido es un intento.
    umbral_pico = max(0.05, float(np.percentile(c, 95)))
    picos = []
    i = 0
    while i < len(c):
        if c[i] >= umbral_pico:
            fin = i
            while fin < len(c) and c[fin] >= umbral_pico * 0.5:
                fin += 1
            tramo = c[i:fin]
            picos.append((i * segundos_por_bloque, float(tramo.max())))
            i = fin + int(1.5 / segundos_por_bloque)  # saltar 1.5 s
        else:
            i += 1

    print(f"Intentos detectados en el audio: {len(picos)}")
    for segundo, valor in picos:
        barra = "#" * int(valor * 40)
        print(f"  {segundo:>5.1f}s  {valor:.3f}  {barra}")

    if picos:
        valores = np.array([v for _, v in picos])
        print(f"\nDe esos {len(picos)} intentos:")
        print(f"  mejor       : {valores.max():.3f}")
        print(f"  peor        : {valores.min():.3f}")
        print(f"  mediana     : {np.median(valores):.3f}")
        print(f"  desviación  : {valores.std():.3f}")

        print("\n¿Qué umbral atraparía cuántos intentos?")
        for u in (0.05, 0.1, 0.2, 0.3, 0.5, 0.7):
            atrapados = int((valores >= u).sum())
            print(f"  umbral {u:.2f}  ->  {atrapados}/{len(valores)} intentos")

        print(
            "\nUn umbral sirve si atrapa casi todos los intentos Y queda\n"
            "muy por encima del ruido de fondo. Compará con el modo --falsos."
        )
    else:
        print("\nNi un solo pico por encima del ruido. El modelo no reconoce nada.")


def main() -> None:
    config = cargar_config()

    if "--analizar" in sys.argv:
        indice = sys.argv.index("--analizar")
        analizar(Path(sys.argv[indice + 1]), config)
        return

    ruta = grabar(config)
    analizar(ruta, config)
    print(f"\nPara reanalizar sin volver a grabar:")
    print(f"  py -3.11 tools_grabar_wakeword.py --analizar {ruta}")


if __name__ == "__main__":
    main()
