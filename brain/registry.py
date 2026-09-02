"""
Registro y despacho de skills.

ejecutar() es la frontera de seguridad del proyecto: los argumentos que
propone el LLM se validan contra el modelo pydantic ANTES de que se ejecute
una sola linea de la skill (PLAN.md §1).

Nunca lanza excepcion hacia arriba. Jarvis corre en segundo plano todo el
dia; una skill rota tiene que producir una disculpa hablada, no matar el
proceso y dejar al usuario hablandole a la nada.
"""

import logging
from typing import Any

from pydantic import ValidationError

from skills.base import Skill, SkillResult, tool_schema

log = logging.getLogger(__name__)


class SkillRegistry:
    """Catalogo de lo que Jarvis sabe hacer."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def registrar(self, skill: Skill) -> None:
        """Anade una skill. Falla si el nombre ya existe.

        Falla fuerte a proposito: con dos skills del mismo nombre, cual se
        ejecuta dependeria del orden de registro, y eso es un bug silencioso
        muy caro de encontrar.
        """
        if skill.name in self._skills:
            raise ValueError(f"Ya hay una skill registrada con el nombre '{skill.name}'")
        self._skills[skill.name] = skill
        log.debug("Skill registrada: %s", skill.name)

    def obtener(self, nombre: str) -> Skill | None:
        return self._skills.get(nombre)

    def nombres(self) -> list[str]:
        return list(self._skills)

    def tools_para_openai(self) -> list[dict[str, Any]]:
        """El array 'tools' que se le manda al LLM, derivado de las skills."""
        return [tool_schema(s) for s in self._skills.values()]

    async def ejecutar(self, nombre: str, argumentos: dict[str, Any]) -> SkillResult:
        """Valida los argumentos y ejecuta. Nunca lanza excepcion."""
        skill = self._skills.get(nombre)
        if skill is None:
            log.warning("Pidieron una skill inexistente: %s", nombre)
            return SkillResult(ok=False, speech="No sé hacer eso.")

        try:
            params = skill.params_model(**argumentos)
        except ValidationError as error:
            log.warning("Parámetros inválidos para %s: %s", nombre, error)
            return SkillResult(
                ok=False, speech="No entendí bien los parámetros de esa orden."
            )

        try:
            return await skill.execute(params)
        except Exception:
            log.exception("La skill %s falló", nombre)
            return SkillResult(ok=False, speech="Algo falló al hacer eso.")
