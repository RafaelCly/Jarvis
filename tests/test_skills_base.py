from pydantic import BaseModel, Field

from skills.base import Skill, SkillResult, tool_schema


class ParamsDePrueba(BaseModel):
    query: str = Field(description="Lo que hay que buscar")
    limite: int = 5


class SkillDePrueba:
    name = "buscar_algo"
    description = "Busca algo en algun lado"
    params_model = ParamsDePrueba

    async def execute(self, params: ParamsDePrueba) -> SkillResult:
        return SkillResult(ok=True, speech=f"busque {params.query}")


def test_skill_result_guarda_lo_que_se_dice():
    resultado = SkillResult(ok=True, speech="son las tres")
    assert resultado.ok is True
    assert resultado.speech == "son las tres"
    assert resultado.data is None


def test_una_clase_bien_formada_cumple_el_protocolo():
    assert isinstance(SkillDePrueba(), Skill)


def test_una_clase_incompleta_no_cumple_el_protocolo():
    class SkillRota:
        name = "rota"

    assert not isinstance(SkillRota(), Skill)


def test_tool_schema_arma_el_json_que_espera_openai():
    esquema = tool_schema(SkillDePrueba())

    assert esquema["type"] == "function"
    assert esquema["function"]["name"] == "buscar_algo"
    assert esquema["function"]["description"] == "Busca algo en algun lado"
    assert "query" in esquema["function"]["parameters"]["properties"]


def test_tool_schema_marca_como_requeridos_los_campos_sin_default():
    esquema = tool_schema(SkillDePrueba())
    requeridos = esquema["function"]["parameters"].get("required", [])

    assert "query" in requeridos
    assert "limite" not in requeridos


def test_tool_schema_conserva_la_descripcion_de_cada_campo():
    # El LLM lee esas descripciones para rellenar los parametros.
    esquema = tool_schema(SkillDePrueba())
    propiedades = esquema["function"]["parameters"]["properties"]

    assert propiedades["query"]["description"] == "Lo que hay que buscar"


async def test_execute_devuelve_un_skill_result():
    resultado = await SkillDePrueba().execute(ParamsDePrueba(query="pdfs"))
    assert isinstance(resultado, SkillResult)
    assert "pdfs" in resultado.speech
