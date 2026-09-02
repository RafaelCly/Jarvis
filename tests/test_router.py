import pytest

from brain.router import RuleRouter


@pytest.mark.parametrize(
    "frase",
    ["qué hora es", "que hora es", "¿Qué hora es?", "dime la hora", "la hora"],
)
def test_reconoce_las_variantes_de_preguntar_la_hora(frase):
    # Whisper transcribe la misma frase con o sin tildes y con o sin signos
    # segun la entonacion, asi que normalizar es obligatorio, no cosmetico.
    assert RuleRouter().resolver(frase) == ("decir_hora", {})


@pytest.mark.parametrize("frase", ["qué día es hoy", "que dia es", "la fecha"])
def test_reconoce_las_variantes_de_preguntar_la_fecha(frase):
    assert RuleRouter().resolver(frase) == ("decir_fecha", {})


@pytest.mark.parametrize("frase", ["hola", "hola jarvis", "buenas"])
def test_reconoce_el_saludo(frase):
    assert RuleRouter().resolver(frase) == ("saludar", {})


def test_devuelve_none_si_ninguna_regla_matchea():
    # None significa "esto es para el LLM", no "no se puede".
    assert RuleRouter().resolver("ponme algo tranquilo para estudiar") is None


def test_ignora_mayusculas_tildes_y_signos():
    assert RuleRouter().resolver("  ¿QUÉ HORA ES?  ") == ("decir_hora", {})


def test_el_texto_vacio_devuelve_none():
    assert RuleRouter().resolver("") is None
    assert RuleRouter().resolver("   ") is None


def test_no_confunde_una_frase_que_solo_contiene_la_palabra():
    # "ahora" contiene "hora" pero no es una pregunta por la hora.
    assert RuleRouter().resolver("reprodúcelo ahora") is None
