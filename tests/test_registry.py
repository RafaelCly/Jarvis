import pytest
from pydantic import BaseModel

from brain.registry import SkillRegistry
from skills.base import SkillResult
from skills.ping import PingSkill


class SumaParams(BaseModel):
    a: int
    b: int


class SumaSkill:
    name = "sumar"
    description = "Suma dos numeros"
    params_model = SumaParams

    async def execute(self, params: SumaParams) -> SkillResult:
        return SkillResult(ok=True, speech=f"{params.a + params.b}")


def test_registrar_y_obtener():
    registro = SkillRegistry()
    registro.registrar(PingSkill())
    assert registro.obtener("ping") is not None


def test_obtener_una_skill_inexistente_devuelve_none():
    assert SkillRegistry().obtener("no_existe") is None


def test_no_deja_registrar_dos_skills_con_el_mismo_nombre():
    # Dos skills con el mismo nombre haria que el LLM eligiera una al azar.
    registro = SkillRegistry()
    registro.registrar(PingSkill())
    with pytest.raises(ValueError, match="ping"):
        registro.registrar(PingSkill())


def test_tools_para_openai_incluye_todas_las_skills():
    registro = SkillRegistry()
    registro.registrar(PingSkill())
    registro.registrar(SumaSkill())

    nombres = {t["function"]["name"] for t in registro.tools_para_openai()}
    assert nombres == {"ping", "sumar"}


async def test_ejecutar_valida_y_corre_la_skill():
    registro = SkillRegistry()
    registro.registrar(SumaSkill())

    resultado = await registro.ejecutar("sumar", {"a": 2, "b": 3})

    assert resultado.ok is True
    assert resultado.speech == "5"


async def test_ejecutar_rechaza_argumentos_invalidos_sin_correr_la_skill():
    # Esta es la barrera de seguridad: lo que devuelve el LLM se valida
    # ANTES de ejecutar nada (PLAN.md §1).
    registro = SkillRegistry()
    registro.registrar(SumaSkill())

    resultado = await registro.ejecutar("sumar", {"a": "no soy un numero"})

    assert resultado.ok is False
    assert "parámetros" in resultado.speech.lower()


async def test_ejecutar_una_skill_inexistente_devuelve_error():
    # El LLM puede alucinar un nombre de funcion que no existe.
    resultado = await SkillRegistry().ejecutar("inventada", {})
    assert resultado.ok is False


async def test_una_skill_que_revienta_no_tumba_a_jarvis():
    class SkillRota:
        name = "rota"
        description = "Falla siempre"
        params_model = SumaParams

        async def execute(self, params):
            raise RuntimeError("boom")

    registro = SkillRegistry()
    registro.registrar(SkillRota())

    resultado = await registro.ejecutar("rota", {"a": 1, "b": 2})

    assert resultado.ok is False


def test_nombres_lista_lo_registrado():
    registro = SkillRegistry()
    registro.registrar(PingSkill())
    registro.registrar(SumaSkill())

    assert sorted(registro.nombres()) == ["ping", "sumar"]
