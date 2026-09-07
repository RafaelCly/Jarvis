"""
Graba unos segundos y los transcribe. Mide calidad y latencia reales.

    py -3.11 tools_probar_stt.py            # graba 5 s del microfono
    py -3.11 tools_probar_stt.py archivo.wav

Verifica dos cosas que los tests no pueden:

  - Si Whisper quedo en GPU o cayo a CPU (riesgo R1 de PLAN.md). En la
    RTX 4050 con el modelo 'small' esperamos 200-400 ms; si tarda mas de
    2 segundos, esta en CPU.
  - Si transcribe bien tu voz en español, sobre todo nombres propios y
    titulos de canciones, que es donde mas se equivoca.
"""

import sys
import time

import numpy as np

from core.config import cargar_config
from ears.capture import AudioCapture
from ears.stt import Transcriber

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SEGUNDOS = 5


def grabar(config) -> np.ndarray:
    """Graba del microfono durante SEGUNDOS."""
    print(f"Grabando {SEGUNDOS} segundos. Decí algo, por ejemplo:")
    print('   "oye Jarvis, qué hora es"\n')

    with AudioCapture(config.audio, on_block=lambda b: None) as captura:
        for restantes in range(SEGUNDOS, 0, -1):
            print(f"   {restantes}...", end="\r", flush=True)
            time.sleep(1)
        audio = captura.ultimos_segundos(SEGUNDOS)

    print("   listo.        \n")
    return audio


def main() -> None:
    config = cargar_config()

    print(f"Modelo pedido : {config.stt.model_size} en {config.stt.device}")
    inicio_carga = time.perf_counter()
    transcriptor = Transcriber(config.stt)
    print(f"Carga         : {time.perf_counter() - inicio_carga:.1f} s")
    print(f"Corriendo en  : {transcriptor.device} ({transcriptor.compute_type})")

    if transcriptor.device == "cpu" and config.stt.device == "cuda":
        print("\n  AVISO: pediste GPU y quedó en CPU. Es el riesgo R1.")
        print("  Probá:  pip install nvidia-cublas-cu12 nvidia-cudnn-cu12\n")

    print()

    if len(sys.argv) > 1:
        import soundfile as sf

        audio, frecuencia = sf.read(sys.argv[1], dtype="int16")
        if frecuencia != 16000:
            sys.exit(f"El archivo está a {frecuencia} Hz; hacen falta 16000.")
        if audio.ndim > 1:
            audio = audio[:, 0]
    else:
        audio = grabar(config)

    nivel = float(np.abs(audio).max())
    if nivel < 500:
        print(f"AVISO: nivel de audio muy bajo (pico {nivel:.0f}). ¿Micrófono correcto?\n")

    # Primera pasada para calentar: la primera siempre es mas lenta.
    transcriptor.transcribir(audio[: 16000 // 2])

    inicio = time.perf_counter()
    texto, duracion = transcriptor.transcribir(audio)
    tardanza = time.perf_counter() - inicio

    print(f'Transcripción : "{texto}"')
    print(f"Audio         : {duracion:.1f} s")
    print(f"Tardanza      : {tardanza * 1000:.0f} ms")

    if tardanza > 2.0:
        print("\n  Lento. Casi seguro está en CPU, o el modelo es muy grande.")
    elif tardanza < 0.6:
        print("\n  Excelente. Corriendo en GPU como esperábamos.")


if __name__ == "__main__":
    main()
