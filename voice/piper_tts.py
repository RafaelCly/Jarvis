"""
Sintesis local con Piper.

LATENCIA MEDIDA (i7-12650H, ver PLAN.md §4). El plan original decia "<100 ms"
y era falso. Para una frase de 2 segundos:

    es_MX-claude-high     ~1400 ms      mejor voz
    es_MX-ald-medium      ~1000 ms      equilibrio, es el default
    es_ES-carlfm-x_low     ~630 ms      mas rapida, se nota peor

No es falta de hilos: con OMP_NUM_THREADS en 1, 4 o 10 el tiempo no cambia.
El modelo es asi. edge-tts tampoco mejora (940 ms al primer audio) y encima
necesita internet, asi que Piper se queda por ser offline.

Esto convierte al TTS en la latencia dominante de la respuesta. Por eso
decir() reproduce por trozos: Piper trocea por oracion, asi que en una
respuesta de varias frases la primera empieza a sonar mientras se genera la
segunda. En respuestas de una sola frase no hay nada que ganar.
"""

import asyncio
import logging
from pathlib import Path

import numpy as np
import sounddevice as sd
from piper import PiperVoice

from core.config import TTSConfig

log = logging.getLogger(__name__)

DIRECTORIO_VOCES = Path("models/piper")


class PiperTTS:
    """Motor de voz local."""

    def __init__(self, config: TTSConfig) -> None:
        modelo = DIRECTORIO_VOCES / f"{config.voice}.onnx"
        if not modelo.is_file():
            raise FileNotFoundError(
                f"No encuentro la voz {modelo}. Descargala con:\n"
                f"    python -m piper.download_voices "
                f"--download-dir {DIRECTORIO_VOCES} {config.voice}"
            )

        self._voz = PiperVoice.load(modelo)
        self.frecuencia = self._voz.config.sample_rate
        log.info("Voz '%s' cargada a %d Hz", config.voice, self.frecuencia)

    def sintetizar(self, texto: str) -> np.ndarray:
        """Convierte texto en muestras int16. Sincrono, para tests y archivos."""
        trozos = list(self._trozos(texto))
        if not trozos:
            return np.zeros(0, dtype=np.int16)
        return np.concatenate(trozos)

    def _trozos(self, texto: str):
        """Genera el audio por partes, como las va produciendo Piper."""
        if not texto.strip():
            return
        for chunk in self._voz.synthesize(texto):
            yield np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)

    def _decir_bloqueante(self, texto: str) -> None:
        """Reproduce cada trozo apenas esta listo, sin esperar al resto."""
        stream = None
        try:
            for trozo in self._trozos(texto):
                if trozo.size == 0:
                    continue
                if stream is None:
                    stream = sd.OutputStream(
                        samplerate=self.frecuencia, channels=1, dtype="int16"
                    )
                    stream.start()
                stream.write(trozo)
        finally:
            if stream is not None:
                stream.stop()
                stream.close()

    async def decir(self, texto: str) -> None:
        """Dice el texto y espera a que termine de sonar.

        La sintesis y la reproduccion bloquean, asi que van a un hilo aparte:
        si corrieran en el loop de asyncio, el pipeline de audio se congelaria
        justo mientras Jarvis habla.
        """
        if not texto.strip():
            return
        await asyncio.to_thread(self._decir_bloqueante, texto)
