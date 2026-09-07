"""
Tests del motor de voz.

Ninguno reproduce audio: se verifica la sintesis, no los parlantes.
Para oirlo de verdad:  py -3.11 tools_probar_voz.py
"""

from pathlib import Path

import numpy as np
import pytest

from core.config import TTSConfig
from voice.base import TTSEngine
from voice.piper_tts import DIRECTORIO_VOCES, PiperTTS

VOZ = "es_MX-ald-medium"
MODELO = DIRECTORIO_VOCES / f"{VOZ}.onnx"

pytestmark = pytest.mark.skipif(
    not MODELO.exists(),
    reason=f"falta {MODELO}; bajala con python -m piper.download_voices",
)


@pytest.fixture(scope="module")
def tts():
    return PiperTTS(TTSConfig(voice=VOZ))


def test_piper_cumple_el_protocolo(tts):
    assert isinstance(tts, TTSEngine)


def test_falla_claro_si_falta_el_modelo():
    with pytest.raises(FileNotFoundError, match="download_voices"):
        PiperTTS(TTSConfig(voice="voz_que_no_existe"))


def test_sintetiza_audio_utilizable(tts):
    audio = tts.sintetizar("Son las tres de la tarde.")

    assert audio.dtype == np.int16
    assert len(audio) > tts.frecuencia * 0.5  # al menos medio segundo
    assert np.abs(audio).max() > 1000  # no es silencio


def test_el_texto_vacio_no_produce_audio(tts):
    assert len(tts.sintetizar("")) == 0
    assert len(tts.sintetizar("   ")) == 0


async def test_decir_texto_vacio_no_revienta(tts):
    # Una skill puede devolver speech vacio; no debe tumbar el pipeline.
    await tts.decir("")


def test_frases_mas_largas_dan_mas_audio(tts):
    corto = tts.sintetizar("Hola.")
    largo = tts.sintetizar("Hola, son las tres y cinco de la tarde de hoy.")

    assert len(largo) > len(corto)


def test_varias_oraciones_llegan_en_varios_trozos(tts):
    # Piper trocea por oracion, y de eso depende que la reproduccion por
    # partes sirva de algo en respuestas largas.
    trozos = list(tts._trozos("Primera oración. Segunda oración. Tercera."))

    assert len(trozos) >= 2
    assert all(t.dtype == np.int16 for t in trozos)


def test_la_frecuencia_es_la_del_modelo(tts):
    # sd.OutputStream se abre con este valor: si no coincide con el modelo,
    # la voz sale acelerada o ralentizada.
    assert tts.frecuencia == tts._voz.config.sample_rate
    assert 16000 <= tts.frecuencia <= 48000
