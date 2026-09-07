"""Tests de captura. Ninguno abre el microfono: se inyectan bloques a mano."""

import numpy as np
import pytest

from core.config import AudioConfig
from ears.capture import AudioCapture


def _config(**extra):
    return AudioConfig(input_device_index=1, **extra)


def test_falla_claro_si_no_hay_dispositivo_configurado():
    with pytest.raises(ValueError, match="input_device_index"):
        AudioCapture(AudioConfig(input_device_index=None), on_block=lambda b: None)


def test_el_callback_recibe_los_bloques():
    recibidos = []
    captura = AudioCapture(_config(), on_block=recibidos.append)

    captura._procesar_bloque(np.zeros(1280, dtype=np.int16))

    assert len(recibidos) == 1
    assert recibidos[0].shape == (1280,)


def test_el_buffer_guarda_el_ultimo_segundo():
    captura = AudioCapture(_config(), on_block=lambda b: None)

    # 16000 / 1280 = 12.5 bloques por segundo. 20 bloques > 1 s.
    for i in range(20):
        captura._procesar_bloque(np.full(1280, i, dtype=np.int16))

    audio = captura.ultimos_segundos(1)

    assert len(audio) == 16000
    assert audio.dtype == np.int16
    assert audio[-1] == 19  # conserva el final, no el principio


def test_el_buffer_no_falla_si_hay_menos_audio_del_pedido():
    captura = AudioCapture(_config(), on_block=lambda b: None)
    captura._procesar_bloque(np.zeros(1280, dtype=np.int16))

    assert len(captura.ultimos_segundos(5)) == 1280


def test_el_buffer_vacio_devuelve_un_array_vacio():
    audio = AudioCapture(_config(), on_block=lambda b: None).ultimos_segundos(1)

    assert len(audio) == 0
    assert audio.dtype == np.int16


def test_pide_varios_segundos():
    captura = AudioCapture(_config(), on_block=lambda b: None)
    for _ in range(80):  # 80 bloques = 6.4 s
        captura._procesar_bloque(np.ones(1280, dtype=np.int16))

    assert len(captura.ultimos_segundos(4)) == 64000


def test_un_consumidor_que_revienta_no_corta_la_captura():
    # El callback de PortAudio corre en su propio hilo. Si una excepcion se
    # propagara, el stream se cerraria y Jarvis quedaria sordo en silencio.
    captura = AudioCapture(_config(), on_block=lambda b: 1 / 0)

    captura._procesar_bloque(np.zeros(1280, dtype=np.int16))  # no debe lanzar

    assert len(captura.ultimos_segundos(1)) == 1280  # y sigue guardando


def test_el_buffer_tiene_tope():
    # Sin tope, un proceso de dias se comeria toda la RAM.
    captura = AudioCapture(_config(), on_block=lambda b: None)
    for _ in range(500):
        captura._procesar_bloque(np.zeros(1280, dtype=np.int16))

    assert len(captura.ultimos_segundos(60)) <= 16000 * 6
