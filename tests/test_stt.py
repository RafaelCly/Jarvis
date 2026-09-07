"""
Tests de transcripcion.

Usan el modelo 'tiny' a proposito: cargar 'small' en cada corrida haria
que la suite tardara demasiado para correrla seguido. La calidad real se
verifica a mano con tools_probar_stt.py.
"""

import numpy as np
import pytest

from core.config import STTConfig
from ears.stt import Transcriber, _registrar_dlls_cuda


@pytest.fixture(scope="module")
def transcriber():
    return Transcriber(STTConfig(model_size="tiny", language="es"))


def test_registrar_dlls_no_revienta_aunque_no_haya_cuda():
    # En una maquina sin las DLLs esto tiene que devolver lista vacia,
    # no explotar: el fallback a CPU depende de que se llegue hasta el.
    assert isinstance(_registrar_dlls_cuda(), list)


def test_el_audio_vacio_devuelve_texto_vacio(transcriber):
    texto, duracion = transcriber.transcribir(np.zeros(0, dtype=np.int16))
    assert texto == ""
    assert duracion == 0.0


def test_el_silencio_no_inventa_texto(transcriber):
    # Con vad_filter activo, un segundo de silencio no debe alucinar nada.
    texto, _ = transcriber.transcribir(np.zeros(16000, dtype=np.int16))
    assert texto.strip() == ""


def test_calcula_bien_la_duracion(transcriber):
    _, duracion = transcriber.transcribir(np.zeros(32000, dtype=np.int16))
    assert duracion == pytest.approx(2.0)


def test_informa_en_que_dispositivo_quedo(transcriber):
    # Si pedimos cuda y quedo en cpu, el atributo lo tiene que reflejar:
    # es como se diagnostica el riesgo R1 sin leer logs.
    assert transcriber.device in ("cuda", "cpu")
    assert transcriber.compute_type in ("float16", "int8", "int8_float16", "float32")


def test_cae_a_cpu_si_cuda_no_esta_disponible():
    # No debe reventar en una maquina sin GPU: el proyecto tiene que poder
    # desarrollarse tambien sin tarjeta.
    t = Transcriber(STTConfig(model_size="tiny", device="cuda"))
    assert t.device in ("cuda", "cpu")


def test_el_ruido_no_produce_una_frase_larga(transcriber):
    # Whisper alucina con ruido puro. No exigimos vacio, pero si que no
    # devuelva un parrafo que despues el router intente interpretar.
    rng = np.random.default_rng(0)
    ruido = rng.integers(-2000, 2000, 16000, dtype=np.int16)

    texto, _ = transcriber.transcribir(ruido)

    assert len(texto) < 120
