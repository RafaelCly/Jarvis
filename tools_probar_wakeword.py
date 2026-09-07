"""
Mide si el wake word reconoce TU voz. Es el riesgo R2 de PLAN.md.

    py -3.11 tools_probar_wakeword.py

El modelo "hey_jarvis" que trae openWakeWord esta entrenado con voces
sinteticas en INGLES. Que funcione con acento español no esta garantizado,
y es mejor descubrirlo ahora que despues de construir medio pipeline.

Decir "hey jarvis" 10 veces, con tono normal, separadas unos segundos.
Al final el script dice si sirve o que hacer.
"""

import sys
import time

import numpy as np

from core.config import cargar_config
from ears.capture import AudioCapture
from ears.wakeword import WakeWordDetector

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

INTENTOS_SUGERIDOS = 10
DURACION_S = 45


def veredicto(detecciones: int) -> str:
    if detecciones >= 8:
        return (
            "EXCELENTE. El modelo en inglés te entiende. Seguí con el plan tal cual."
        )
    if detecciones >= 4:
        return (
            "REGULAR. Bajá wakeword.threshold a 0.35 en config.local.yaml y repetí\n"
            "  esta prueba. Si sube a 8+, listo. Ojo con los falsos positivos."
        )
    return (
        "NO SIRVE para tu voz, que era el riesgo R2 previsto. Dos salidas:\n"
        "  1. Entrenar un modelo propio en español ('oye Jarvis') con el notebook\n"
        "     de openWakeWord, que genera las muestras con Piper. Es gratis.\n"
        "  2. Activación solo por palmada, que llega en la Fase 2.\n"
        "  Esto NO bloquea el proyecto: el resto del pipeline es independiente."
    )


def main() -> None:
    config = cargar_config()
    detector = WakeWordDetector(config.wakeword)

    detecciones: list[float] = []
    nivel_pico = 0.0

    def al_llegar_bloque(bloque: np.ndarray) -> None:
        nonlocal nivel_pico
        nivel_pico = max(nivel_pico, float(np.abs(bloque).max()))

        confianza = detector.procesar(bloque)
        if confianza is not None:
            detecciones.append(confianza)
            print(f"   detectada #{len(detecciones)}  (confianza {confianza:.2f})")

    print(f"Umbral configurado: {config.wakeword.threshold}")
    print(f"Modelo: {config.wakeword.model}\n")
    print(f"Decí 'hey jarvis' {INTENTOS_SUGERIDOS} veces, separadas unos segundos.")
    print(f"Tenés {DURACION_S} segundos. Empezá.\n")

    with AudioCapture(config.audio, on_block=al_llegar_bloque):
        inicio = time.monotonic()
        while time.monotonic() - inicio < DURACION_S:
            time.sleep(0.2)

    print(f"\n{'=' * 62}")
    print(f"Detecciones: {len(detecciones)} de {INTENTOS_SUGERIDOS} intentos sugeridos")
    if detecciones:
        print(f"Confianza media: {sum(detecciones) / len(detecciones):.2f}")

    if nivel_pico < 500:
        print("\nAVISO: el nivel de audio fue muy bajo. ¿Micrófono correcto?")
        print(f"  pico registrado: {nivel_pico:.0f}  (esperado: miles al hablar)")

    print(f"\n{veredicto(len(detecciones))}")
    print("\nAnotá el resultado: decide si hace falta entrenar un modelo propio.")


if __name__ == "__main__":
    main()
