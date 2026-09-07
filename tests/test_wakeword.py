"""
Tests del detector de wake word, sin microfono.

Lo que estos tests NO pueden verificar es si el modelo reconoce la wake
word dicha con acento español. Eso solo se ve hablando:

    py -3.11 tools_probar_wakeword.py
"""

import numpy as np
import pytest

from core.config import WakewordConfig
from ears.wakeword import WakeWordDetector

BLOQUE = 1280  # 80 ms a 16 kHz, lo que espera openWakeWord


@pytest.fixture(scope="module")
def detector_estricto():
    return WakeWordDetector(WakewordConfig(threshold=0.5))


def test_el_silencio_no_dispara(detector_estricto):
    detector_estricto.reiniciar()
    silencio = np.zeros(BLOQUE, dtype=np.int16)

    for _ in range(20):
        assert detector_estricto.procesar(silencio) is None


def test_el_ruido_blanco_no_dispara(detector_estricto):
    # Si esto falla, el umbral esta demasiado bajo y va a haber falsos
    # positivos con cualquier ruido de la habitacion.
    detector_estricto.reiniciar()
    rng = np.random.default_rng(42)

    for _ in range(20):
        ruido = rng.integers(-3000, 3000, BLOQUE, dtype=np.int16)
        assert detector_estricto.procesar(ruido) is None


def test_un_umbral_de_cero_dispara_con_cualquier_cosa():
    # Verifica que el cableado con openWakeWord funciona de verdad: que el
    # modelo carga, acepta el bloque y devuelve un numero utilizable.
    detector = WakeWordDetector(WakewordConfig(threshold=0.0))
    resultado = detector.procesar(np.zeros(BLOQUE, dtype=np.int16))

    assert resultado is not None
    assert 0.0 <= resultado <= 1.0


def test_el_periodo_refractario_evita_disparos_encadenados():
    # El modelo da varios frames sobre el umbral por una sola pronunciacion.
    detector = WakeWordDetector(WakewordConfig(threshold=0.0))
    silencio = np.zeros(BLOQUE, dtype=np.int16)

    assert detector.procesar(silencio) is not None
    assert detector.procesar(silencio) is None
    assert detector.procesar(silencio) is None


def test_reiniciar_levanta_el_periodo_refractario():
    detector = WakeWordDetector(WakewordConfig(threshold=0.0))
    silencio = np.zeros(BLOQUE, dtype=np.int16)

    detector.procesar(silencio)
    assert detector.procesar(silencio) is None

    detector.reiniciar()
    assert detector.procesar(silencio) is not None
