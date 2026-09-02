"""
Skills del sistema: hora, fecha y saludo.

Todo lo que devuelven en 'speech' lo va a pronunciar una voz, asi que se
escribe como se habla: "son las tres y cinco", no "15:05".
"""

import random
from datetime import datetime

from pydantic import BaseModel

from skills.base import SkillResult

_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")

_SALUDOS = (
    "Hola, ¿en qué te ayudo?",
    "Acá estoy.",
    "Hola. Decime.",
)


class SinParametros(BaseModel):
    """Para skills que no necesitan argumentos."""


class DecirHoraSkill:
    name = "decir_hora"
    description = "Dice la hora actual."
    params_model = SinParametros

    async def execute(self, params: SinParametros) -> SkillResult:
        ahora = datetime.now()
        hora = ahora.hour % 12 or 12

        if ahora.hour < 12:
            franja = "de la mañana"
        elif ahora.hour < 20:
            franja = "de la tarde"
        else:
            franja = "de la noche"

        if ahora.minute == 0:
            texto = f"Son las {hora} en punto {franja}."
        else:
            texto = f"Son las {hora} y {ahora.minute} {franja}."

        return SkillResult(ok=True, speech=texto, data={"iso": ahora.isoformat()})


class DecirFechaSkill:
    name = "decir_fecha"
    description = "Dice la fecha de hoy."
    params_model = SinParametros

    async def execute(self, params: SinParametros) -> SkillResult:
        hoy = datetime.now()
        texto = f"Hoy es {_DIAS[hoy.weekday()]} {hoy.day} de {_MESES[hoy.month - 1]}."

        return SkillResult(ok=True, speech=texto, data={"iso": hoy.date().isoformat()})


class SaludarSkill:
    name = "saludar"
    description = "Responde a un saludo del usuario."
    params_model = SinParametros

    async def execute(self, params: SinParametros) -> SkillResult:
        return SkillResult(ok=True, speech=random.choice(_SALUDOS))
