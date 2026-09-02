"""Skill de humo: confirma que el pipeline completo esta cableado."""

from pydantic import BaseModel

from skills.base import SkillResult


class PingParams(BaseModel):
    """No necesita parametros."""


class PingSkill:
    name = "ping"
    description = "Responde 'pong'. Sirve para verificar que Jarvis esta vivo."
    params_model = PingParams

    async def execute(self, params: PingParams) -> SkillResult:
        return SkillResult(ok=True, speech="pong")
