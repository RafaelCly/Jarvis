"""
Mide si el wake word reconoce TU voz. Es el riesgo R2 de PLAN.md.

    py -3.11 tools_probar_wakeword.py

El modelo "hey_jarvis" que trae openWakeWord esta entrenado con voces
sinteticas en INGLES. Que funcione con acento español no esta garantizado.

Este script NO se limita a contar detecciones sobre el umbral: muestra la
confianza MAXIMA que alcanzo el modelo, que es el dato que decide que
hacer. No es lo mismo quedarse en 0.45 (basta bajar el umbral) que en 0.01
(el modelo no te reconoce y hay que entrenar uno propio).

Tambien muestra el nivel de audio en vivo, para descartar de entrada que el
problema sea el microfono y no el modelo.
"""

import sys
import time

import numpy as np

from core.config import cargar_config
from ears.capture import AudioCapture
from ears.wakeword import WakeWordDetector

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

INTENTOS = 10
DURACION_S = 45
NIVEL_MINIMO = 800  # por debajo de esto, el microfono no te esta oyendo


def barra(valor: float, maximo: float, ancho: int = 20) -> str:
    llenos = int(min(valor / maximo, 1.0) * ancho)
    return "#" * llenos + "." * (ancho - llenos)


def veredicto(confianza_maxima: float, detecciones: int, umbral: float) -> str:
    if detecciones >= 8:
        return "EXCELENTE. El modelo en inglés te entiende. Seguí con el plan tal cual."

    if confianza_maxima >= umbral:
        return (
            f"PARCIAL. Llegaste a {confianza_maxima:.2f} y detectó {detecciones} veces.\n"
            "  Decilo más separado (hay 2 s de periodo refractario) y repetí."
        )

    if confianza_maxima >= 0.15:
        nuevo = max(0.20, round(confianza_maxima * 0.7, 2))
        return (
            f"CERCA. El modelo llegó a {confianza_maxima:.2f}, por debajo del umbral\n"
            f"  {umbral}. Probá bajarlo en config.local.yaml:\n\n"
            "    wakeword:\n"
            f"      threshold: {nuevo}\n\n"
            "  y repetí esta prueba. Si sube a 8 de 10, listo. Ojo con los\n"
            "  falsos positivos: correlo también en silencio para ver que no\n"
            "  se dispare solo."
        )

    return (
        f"NO TE RECONOCE. La confianza máxima fue {confianza_maxima:.2f}, que es\n"
        "  ruido de fondo. Bajar el umbral no arregla esto: solo traería falsos\n"
        "  positivos. Es el riesgo R2 previsto. Dos salidas:\n\n"
        "  1. Entrenar un modelo propio en español ('oye Jarvis') con el notebook\n"
        "     de openWakeWord, que genera las muestras con Piper. Es gratis.\n"
        "  2. Activación solo por palmada, que llega en la Fase 2.\n\n"
        "  Esto NO bloquea el proyecto: el resto del pipeline es independiente."
    )


def veredicto_falsos(confianza_maxima: float, disparos: int, umbral: float) -> str:
    """Veredicto del modo --falsos: aca CERO es el buen resultado."""
    if disparos == 0:
        margen = umbral - confianza_maxima
        if margen > 0.1:
            return (
                f"PERFECTO. Ningún falso positivo, y hablando normal el modelo no\n"
                f"  pasó de {confianza_maxima:.3f}, con {margen:.2f} de margen hasta el\n"
                f"  umbral {umbral}. Este umbral es seguro. Dejalo así."
            )
        return (
            f"BIEN, pero justo. Ningún disparo, pero llegaste a {confianza_maxima:.3f}\n"
            f"  contra un umbral de {umbral}: solo {margen:.2f} de margen. Va a fallar\n"
            "  alguna vez. Si te molesta, subí el umbral un poco y volvé a probar\n"
            "  que siga reconociéndote."
        )

    return (
        f"DEMASIADO SENSIBLE. Se disparó {disparos} veces hablando de otra cosa,\n"
        f"  y llegó a {confianza_maxima:.3f}. Con este umbral Jarvis se va a activar\n"
        "  solo mientras hablás o mirás un video.\n\n"
        f"  Subí wakeword.threshold por encima de {confianza_maxima:.2f} en\n"
        "  config.local.yaml y repetí LAS DOS pruebas: si al subirlo deja de\n"
        "  reconocerte, el modelo en inglés no da para tu voz y toca entrenar\n"
        "  uno propio en español."
    )


def main() -> None:
    # Modo falsos positivos: hablar de todo MENOS la wake word. Es la prueba
    # que de verdad valida un umbral bajo. Que no se dispare en silencio no
    # dice nada: el riesgo real es una conversacion o un video de YouTube.
    modo_falsos = "--falsos" in sys.argv

    config = cargar_config()
    detector = WakeWordDetector(config.wakeword)
    umbral = config.wakeword.threshold

    detecciones: list[float] = []
    confianzas: list[float] = []
    niveles: list[float] = []
    ultimo_pintado = 0.0

    def al_llegar_bloque(bloque: np.ndarray) -> None:
        nonlocal ultimo_pintado

        nivel = float(np.abs(bloque).max())
        niveles.append(nivel)

        # La confianza cruda, sin filtrar por umbral ni refractario: es el
        # dato que dice si el modelo te oye aunque no llegue a disparar.
        cruda = float(detector._modelo.predict(bloque).get(config.wakeword.model, 0.0))
        confianzas.append(cruda)

        if cruda >= umbral and time.monotonic() - ultimo_pintado > 2.0:
            detecciones.append(cruda)
            ultimo_pintado = time.monotonic()
            print(f"\r   DETECTADA #{len(detecciones)}  (confianza {cruda:.2f})      ")
        elif time.monotonic() - ultimo_pintado > 0.2:
            ultimo_pintado = time.monotonic()
            print(
                f"\r   audio [{barra(nivel, 8000)}]  "
                f"confianza [{barra(cruda, 1.0)}] {cruda:.2f}   ",
                end="",
                flush=True,
            )

    print(f"Micrófono     : dispositivo {config.audio.input_device_index}")
    print(f"Modelo        : {config.wakeword.model}")
    print(f"Umbral        : {umbral}\n")

    if modo_falsos:
        print("MODO FALSOS POSITIVOS")
        print("Hablá normal de CUALQUIER cosa, menos 'hey jarvis'. Contá tu día,")
        print("leé algo en voz alta, poné un video. Lo que sea, pero sin decirla.")
        print(f"\nNO debería detectar NADA. Tenés {DURACION_S} segundos.\n")
    else:
        print(f"Decí 'hey jarvis' {INTENTOS} veces, separadas 3 segundos.")
        print("Pronuncialo natural, NO fuerces acento inglés.")
        print(f"Tenés {DURACION_S} segundos. Empezá.\n")

    with AudioCapture(config.audio, on_block=al_llegar_bloque):
        inicio = time.monotonic()
        while time.monotonic() - inicio < DURACION_S:
            time.sleep(0.1)

    confianza_maxima = max(confianzas) if confianzas else 0.0
    nivel_maximo = max(niveles) if niveles else 0.0
    top = sorted(confianzas, reverse=True)[:5]

    print("\n" + "=" * 64)
    if modo_falsos:
        print(f"Falsos positivos   : {len(detecciones)}   (deberían ser 0)")
    else:
        print(f"Detecciones        : {len(detecciones)} de {INTENTOS}")
    print(f"Confianza máxima   : {confianza_maxima:.3f}   (umbral: {umbral})")
    print(f"5 picos más altos  : {', '.join(f'{c:.3f}' for c in top)}")
    print(f"Nivel de audio máx : {nivel_maximo:.0f}")

    if nivel_maximo < NIVEL_MINIMO:
        print("\n" + "!" * 64)
        print("EL MICRÓFONO NO TE ESTÁ OYENDO. El resultado no es válido.")
        print(f"  Pico registrado: {nivel_maximo:.0f}, y hablando debería pasar de 3000.")
        print("  Revisá: ¿el dispositivo correcto? ¿permisos de micrófono de Windows?")
        print("  Corré:  py -3.11 tools_listar_dispositivos.py")
        print("!" * 64)
        return

    if modo_falsos:
        print(f"\n{veredicto_falsos(confianza_maxima, len(detecciones), umbral)}")
    else:
        print(f"\n{veredicto(confianza_maxima, len(detecciones), umbral)}")


if __name__ == "__main__":
    main()
