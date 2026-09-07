"""
Captura de microfono y buffer circular.

El callback de PortAudio corre en su propio hilo y tiene un presupuesto de
tiempo estricto: si tarda mas que la duracion del bloque (80 ms), el audio
se corta. Por eso aca no se hace nada pesado — solo copiar y delegar.

Sobre la eleccion de dispositivo: NO usar el predeterminado del sistema.
Tiene que ser un indice fisico explicito, y nunca unos auriculares
Bluetooth (PLAN.md §2). Para averiguarlo:

    py -3.11 tools_listar_dispositivos.py
"""

import logging
from collections import deque

import numpy as np
import sounddevice as sd

from core.config import AudioConfig

log = logging.getLogger(__name__)

# Segundos de audio que se conservan hacia atras. Da margen para arrancar la
# transcripcion un poco antes de la deteccion, y pone un techo a la memoria:
# sin tope, un proceso que corre todo el dia se comeria la RAM.
SEGUNDOS_DE_BUFFER = 6


class AudioCapture:
    """Abre el microfono y entrega bloques de int16 a 16 kHz mono."""

    def __init__(self, config: AudioConfig, on_block) -> None:
        if config.input_device_index is None:
            raise ValueError(
                "audio.input_device_index no está configurado. Corré:\n"
                "    py -3.11 tools_listar_dispositivos.py\n"
                "y poné el índice en config.local.yaml"
            )

        self._config = config
        self._on_block = on_block
        self._stream: sd.InputStream | None = None

        bloques_por_segundo = config.sample_rate / config.block_size
        self._buffer: deque[np.ndarray] = deque(
            maxlen=int(bloques_por_segundo * SEGUNDOS_DE_BUFFER)
        )

    def _procesar_bloque(self, bloque: np.ndarray) -> None:
        """Guarda en el buffer y avisa al consumidor.

        Separado del callback de PortAudio para poder testearlo sin abrir el
        microfono. Una excepcion del consumidor se registra y se traga: si se
        propagara, PortAudio cerraria el stream y Jarvis quedaria sordo sin
        que nada lo indique.
        """
        self._buffer.append(bloque)
        try:
            self._on_block(bloque)
        except Exception:
            log.exception("El consumidor de audio falló")

    def _callback(self, indata, frames, time_info, status) -> None:
        if status:
            log.warning("Estado de PortAudio: %s", status)
        # copy() porque PortAudio reutiliza el buffer en el proximo callback.
        self._procesar_bloque(indata[:, 0].copy())

    def ultimos_segundos(self, segundos: int) -> np.ndarray:
        """Los ultimos N segundos de audio, o lo que haya si es menos."""
        if not self._buffer:
            return np.zeros(0, dtype=np.int16)

        audio = np.concatenate(list(self._buffer))
        return audio[-self._config.sample_rate * segundos :]

    def start(self) -> None:
        self._stream = sd.InputStream(
            samplerate=self._config.sample_rate,
            channels=self._config.channels,
            dtype="int16",
            blocksize=self._config.block_size,
            device=self._config.input_device_index,
            callback=self._callback,
        )
        self._stream.start()
        log.info(
            "Micrófono abierto: dispositivo %s a %d Hz",
            self._config.input_device_index,
            self._config.sample_rate,
        )

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            log.info("Micrófono cerrado")

    def __enter__(self) -> "AudioCapture":
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.stop()
