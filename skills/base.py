"""
Contrato de las skills (PLAN.md §5.6).

Anadir una capacidad nueva a Jarvis es escribir una clase que cumpla el
Protocol Skill y registrarla. No hay que tocar el prompt ni el orquestador:
tool_schema() deriva el JSON de OpenAI del modelo pydantic.
"""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


@dataclass
class SkillResult:
    """Lo que devuelve una skill al ejecutarse.

    speech es lo que Jarvis dice en voz alta; data es informacion
    estructurada para la interfaz, que no se pronuncia.
    """

    ok: bool
    speech: str
    data: dict[str, Any] | None = None


@runtime_checkable
class Skill(Protocol):
    """Una capacidad de Jarvis.

    name debe ser un identificador valido de funcion: el LLM lo devuelve
    literalmente cuando elige esta skill.

    description es lo unico que el LLM lee para decidir si usarla. Escribirla
    pensando en el modelo, no en un humano.
    """

    name: str
    description: str
    params_model: type[BaseModel]

    async def execute(self, params: BaseModel) -> SkillResult: ...


def tool_schema(skill: Skill) -> dict[str, Any]:
    """Convierte una skill al formato de herramienta de OpenAI.

    Deriva los parametros del JSON Schema que genera pydantic, asi que el
    esquema nunca se desincroniza del modelo real.
    """
    parametros = skill.params_model.model_json_schema()
    parametros.pop("title", None)

    return {
        "type": "function",
        "function": {
            "name": skill.name,
            "description": skill.description,
            "parameters": parametros,
        },
    }
