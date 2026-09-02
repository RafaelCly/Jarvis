"""
Configuracion de Jarvis.

Tres archivos con roles distintos:
  config.yaml        commiteado, valores compartidos
  config.local.yaml  en .gitignore, lo propio de esta maquina
  .env               en .gitignore, los secretos

Los secretos nunca van al YAML porque el YAML se commitea.
"""

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class AudioConfig(BaseModel):
    input_device_index: int | None = None
    sample_rate: int = 16000
    channels: int = 1
    block_size: int = 1280

    @field_validator("sample_rate")
    @classmethod
    def _debe_ser_16k(cls, v: int) -> int:
        # openWakeWord, silero-vad y Whisper asumen 16 kHz. Si alguien lo
        # cambia, falla aca y no tres capas mas abajo con audio corrupto.
        if v != 16000:
            raise ValueError("sample_rate debe ser 16000 para todo el pipeline")
        return v


class WakewordConfig(BaseModel):
    model: str = "hey_jarvis"
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class STTConfig(BaseModel):
    model_size: str = "small"
    device: Literal["cuda", "cpu"] = "cuda"
    compute_type: str = "float16"
    language: str = "es"


class TTSConfig(BaseModel):
    engine: Literal["piper", "edge"] = "piper"
    voice: str = "es_MX-claude-high"


class LLMConfig(BaseModel):
    model: str = "gpt-4o-mini"
    max_tool_iterations: int = 2


class Config(BaseModel):
    audio: AudioConfig = AudioConfig()
    wakeword: WakewordConfig = WakewordConfig()
    stt: STTConfig = STTConfig()
    tts: TTSConfig = TTSConfig()
    llm: LLMConfig = LLMConfig()

    @property
    def openai_api_key(self) -> str | None:
        """Se lee del entorno, nunca del YAML."""
        return os.environ.get("OPENAI_API_KEY")


def _fusionar(base: dict[str, Any], encima: dict[str, Any]) -> dict[str, Any]:
    """Fusion recursiva: 'encima' pisa a 'base', seccion por seccion.

    Recursiva y no plana para que poner solo stt.device en el archivo local
    no borre stt.model_size del compartido.
    """
    resultado = dict(base)
    for clave, valor in encima.items():
        if isinstance(valor, dict) and isinstance(resultado.get(clave), dict):
            resultado[clave] = _fusionar(resultado[clave], valor)
        else:
            resultado[clave] = valor
    return resultado


def cargar_config(
    ruta: Path | str = "config.yaml",
    ruta_local: Path | str | None = "config.local.yaml",
) -> Config:
    """Carga config.yaml y le superpone config.local.yaml si existe.

    config.local.yaml esta en .gitignore y lleva lo que es propio de cada
    maquina: indice de microfono, cuda vs cpu, tamano del modelo. Sin esa
    separacion, un mismo archivo tendria que valer para computadoras
    distintas (PLAN.md §2.3).
    """
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(
            f"No encuentro {ruta}. Copiá config.yaml del repo a la raíz del proyecto."
        )

    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}

    if ruta_local is not None:
        ruta_local = Path(ruta_local)
        if ruta_local.is_file():
            locales = yaml.safe_load(ruta_local.read_text(encoding="utf-8")) or {}
            datos = _fusionar(datos, locales)

    return Config(**datos)
