import pytest

from core.config import Config, cargar_config

YAML_MINIMO = """
audio:
  input_device_index: 3
  sample_rate: 16000
  channels: 1
  block_size: 1280
wakeword:
  model: hey_jarvis
  threshold: 0.6
stt:
  model_size: small
  device: cuda
  compute_type: float16
  language: es
tts:
  engine: piper
  voice: es_MX-claude-high
llm:
  model: gpt-4o-mini
  max_tool_iterations: 2
"""


def _escribir(tmp_path, contenido=YAML_MINIMO, nombre="config.yaml"):
    ruta = tmp_path / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def test_carga_el_yaml_completo(tmp_path):
    config = cargar_config(_escribir(tmp_path), None)

    assert config.audio.input_device_index == 3
    assert config.wakeword.threshold == 0.6
    assert config.stt.language == "es"
    assert config.llm.model == "gpt-4o-mini"


def test_el_sample_rate_debe_ser_16000(tmp_path):
    # openWakeWord, silero-vad y Whisper esperan 16 kHz. Fallar temprano
    # es mucho mejor que depurar por que la transcripcion sale en chino.
    ruta = _escribir(tmp_path, YAML_MINIMO.replace("sample_rate: 16000", "sample_rate: 44100"))

    with pytest.raises(ValueError, match="16000"):
        cargar_config(ruta, None)


def test_falla_claro_si_el_archivo_no_existe(tmp_path):
    with pytest.raises(FileNotFoundError, match="config.yaml"):
        cargar_config(tmp_path / "no-existe.yaml", None)


def test_input_device_index_puede_ser_none(tmp_path):
    # null significa "todavia sin configurar"; capture.py da un error util.
    ruta = _escribir(tmp_path, YAML_MINIMO.replace("input_device_index: 3", "input_device_index: null"))

    assert cargar_config(ruta, None).audio.input_device_index is None


def test_es_un_config(tmp_path):
    assert isinstance(cargar_config(_escribir(tmp_path), None), Config)


def test_config_local_pisa_al_compartido(tmp_path):
    # config.yaml esta commiteado; config.local.yaml esta en .gitignore y
    # lleva lo propio de cada maquina (PLAN.md §2.3).
    compartido = _escribir(tmp_path)
    local = _escribir(
        tmp_path,
        "stt:\n  device: cpu\naudio:\n  input_device_index: 7\n",
        "config.local.yaml",
    )

    config = cargar_config(compartido, local)

    assert config.stt.device == "cpu"
    assert config.audio.input_device_index == 7


def test_config_local_no_borra_lo_que_no_menciona(tmp_path):
    # Fusion recursiva: poner solo stt.device no debe perder stt.model_size.
    compartido = _escribir(tmp_path)
    local = _escribir(tmp_path, "stt:\n  device: cpu\n", "config.local.yaml")

    config = cargar_config(compartido, local)

    assert config.stt.device == "cpu"
    assert config.stt.model_size == "small"  # heredado del compartido
    assert config.stt.language == "es"


def test_funciona_sin_config_local(tmp_path):
    # No es obligatorio: si tu maquina coincide con los valores compartidos,
    # no hace falta crearlo.
    config = cargar_config(_escribir(tmp_path), tmp_path / "no-existe.yaml")

    assert config.stt.device == "cuda"
