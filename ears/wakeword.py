"""
Deteccion de wake word con openWakeWord.

Corre en ONNX sobre CPU en unos 4 ms por bloque de 80 ms, asi que puede
estar escuchando todo el tiempo sin costo perceptible y sin tocar la GPU,
que queda libre para Whisper.

AVISO SOBRE EL ACENTO (riesgo R2 de PLAN.md): el modelo "hey_jarvis" que
viene con openWakeWord esta entrenado con voces sinteticas en ingles. Puede
no reconocer una pronunciacion en español. Antes de construir nada encima:

    py -3.11 tools_probar_wakeword.py

Si detecta menos de 4 de cada 10, hay dos salidas, en este orden:
  1. Bajar wakeword.threshold en config.local.yaml (probar 0.35).
  2. Entrenar un modelo propio en español con el notebook de openWakeWord,
     que genera las muestras con Piper. Es gratis y permite "oye Jarvis".
Y si tampoco, queda la activacion por palmada, que llega en la Fase 2.
"""

import logging
import time

import numpy as np
from openwakeword.model import Model

from core.config import WakewordConfig

log = logging.getLogger(__name__)

# Tras un disparo, ignorar detecciones un rato: el modelo suele dar varios
# frames seguidos por encima del umbral para una sola pronunciacion, y sin
# esto Jarvis se activaria tres veces por cada "hey jarvis".
REFRACTARIO_S = 2.0


class WakeWordDetector:
    """Devuelve la confianza cuando oye la wake word, o None."""

    def __init__(self, config: WakewordConfig) -> None:
        self._umbral = config.threshold
        self._nombre = config.model
        self._modelo = Model(
            wakeword_models=[config.model], inference_framework="onnx"
        )
        self._ultimo_disparo = 0.0

        log.info(
            "Wake word '%s' cargada, umbral %.2f", config.model, config.threshold
        )

    def procesar(self, bloque: np.ndarray) -> float | None:
        """Procesa 1280 muestras int16. Devuelve la confianza o None.

        None significa "no era la wake word", tanto si la confianza no llego
        al umbral como si todavia estamos en el periodo refractario.
        """
        if time.monotonic() - self._ultimo_disparo < REFRACTARIO_S:
            return None

        predicciones = self._modelo.predict(bloque)
        confianza = float(predicciones.get(self._nombre, 0.0))

        if confianza < self._umbral:
            return None

        self._ultimo_disparo = time.monotonic()
        log.info("Wake word detectada (confianza %.2f)", confianza)
        return confianza

    def reiniciar(self) -> None:
        """Olvida el periodo refractario. Util en tests y al reanudar."""
        self._ultimo_disparo = 0.0
