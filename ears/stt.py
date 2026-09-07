"""
Transcripcion con faster-whisper.

RIESGO R1 de PLAN.md, el dolor clasico de este stack en Windows:
faster-whisper necesita cublas64_*.dll y cudnn_*.dll para correr en GPU.
pip las instala dentro de site-packages/nvidia/, pero NO las agrega al
buscador de DLLs de Windows, asi que la carga falla con un
"Could not locate cublas64_12.dll" que no dice como arreglarlo.

_registrar_dlls_cuda() lo resuelve, y tiene que ejecutarse ANTES de
importar faster_whisper. Si aun asi falla, se cae a CPU con int8: mas
lento, pero el proyecto sigue andando.
"""

import logging
import os
import site
import sys
from pathlib import Path

import numpy as np

from core.config import STTConfig

log = logging.getLogger(__name__)

# Subcarpetas de site-packages donde pip deja las DLLs de NVIDIA.
_CARPETAS_CUDA = ("nvidia/cublas/bin", "nvidia/cudnn/bin")


def _directorios_de_paquetes() -> list[Path]:
    """site-packages, incluido el del venv, que getsitepackages a veces omite.

    Deduplicado por ruta resuelta: las dos fuentes suelen apuntar al mismo
    directorio y registrar la misma DLL dos veces no rompe, pero ensucia
    el diagnostico cuando algo falla.
    """
    candidatos = [Path(p) for p in site.getsitepackages()]
    # En un venv, las DLLs estan bajo Lib/site-packages junto al ejecutable.
    candidatos.append(Path(sys.prefix) / "Lib" / "site-packages")

    vistos: set[Path] = set()
    directorios = []
    for candidato in candidatos:
        if not candidato.is_dir():
            continue
        resuelto = candidato.resolve()
        if resuelto not in vistos:
            vistos.add(resuelto)
            directorios.append(resuelto)

    return directorios


def _registrar_dlls_cuda() -> list[Path]:
    """Pone las DLLs de cuBLAS y cuDNN al alcance de CTranslate2.

    IMPORTANTE: hay que modificar PATH, no basta con os.add_dll_directory().

    add_dll_directory() solo afecta a lo que carga el propio Python. CTranslate2
    (el motor de faster-whisper) resuelve cuBLAS por su cuenta y no consulta
    esos directorios. El sintoma es traicionero: el modelo CARGA bien en cuda,
    y recien al transcribir explota con

        RuntimeError: Library cublas64_12.dll is not found or cannot be loaded

    Se hacen las dos cosas porque add_dll_directory sigue sirviendo para otras
    dependencias, pero PATH es la que resuelve el problema.
    """
    if sys.platform != "win32":
        return []

    registradas = []
    for base in _directorios_de_paquetes():
        for carpeta in _CARPETAS_CUDA:
            ruta = base / carpeta
            if ruta.is_dir():
                os.add_dll_directory(str(ruta))
                registradas.append(ruta)

    if not registradas:
        log.warning(
            "No encontré las DLLs de CUDA. Si Whisper no arranca en GPU: "
            "pip install nvidia-cublas-cu12 nvidia-cudnn-cu12"
        )
        return []

    nuevas = os.pathsep.join(str(r) for r in registradas)
    os.environ["PATH"] = nuevas + os.pathsep + os.environ.get("PATH", "")
    log.debug("DLLs de CUDA añadidas al PATH: %s", nuevas)

    return registradas


_registrar_dlls_cuda()

from faster_whisper import WhisperModel  # noqa: E402  (despues de las DLLs)


class Transcriber:
    """Convierte audio int16 a 16 kHz en texto."""

    def __init__(self, config: STTConfig) -> None:
        self._config = config
        self.device = config.device
        self.compute_type = config.compute_type

        try:
            self._modelo = WhisperModel(
                config.model_size,
                device=config.device,
                compute_type=config.compute_type,
            )
            # Que el modelo CARGUE en cuda no significa que pueda computar:
            # si falta cublas64_12.dll, la carga pasa y la primera
            # transcripcion revienta. Se comprueba aca, al arrancar, y no
            # cuando el usuario ya esta hablandole.
            self._probar_inferencia()
        except Exception as error:
            if config.device == "cpu":
                raise  # ya estabamos en CPU: no hay a donde caer

            log.warning(
                "Whisper no funciona en %s (%s). Cayendo a CPU con int8.",
                config.device,
                error,
            )
            self.device = "cpu"
            self.compute_type = "int8"
            self._modelo = WhisperModel(
                config.model_size, device="cpu", compute_type="int8"
            )
            self._probar_inferencia()

        log.info(
            "Whisper '%s' cargado en %s (%s)",
            config.model_size,
            self.device,
            self.compute_type,
        )

    def _probar_inferencia(self) -> None:
        """Fuerza un decodificado corto para comprobar que el backend anda.

        vad_filter=False a proposito: con el VAD activo, medio segundo de
        silencio se descarta y Whisper nunca llega a ejecutarse, con lo que
        la prueba no probaria nada.
        """
        mudo = np.zeros(8000, dtype=np.float32)
        segmentos, _ = self._modelo.transcribe(
            mudo, language="es", vad_filter=False, beam_size=1
        )
        list(segmentos)  # los segmentos son perezosos: hay que consumirlos

    def transcribir(self, audio: np.ndarray) -> tuple[str, float]:
        """Devuelve (texto, duracion_del_audio_en_segundos).

        Whisper espera float32 en [-1, 1]; la captura entrega int16.
        """
        if audio.size == 0:
            return "", 0.0

        muestras = audio.astype(np.float32) / 32768.0
        duracion = len(muestras) / 16000.0

        segmentos, _ = self._modelo.transcribe(
            muestras,
            language=self._config.language,  # fijarlo es mas rapido y preciso
            vad_filter=True,                 # descarta silencios de los bordes
            beam_size=5,
        )

        texto = " ".join(s.text.strip() for s in segmentos).strip()
        return texto, duracion
