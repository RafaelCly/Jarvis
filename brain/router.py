"""
Router de reglas: atiende los comandos frecuentes sin llamar al LLM.

Compra tres cosas: latencia cero en lo que mas se usa, funcionamiento sin
internet para lo basico, y menos gasto de creditos (PLAN.md §5.2).

Lo que no matchea devuelve None y sube al LLM. None significa "esto es para
el modelo", nunca "no se puede".
"""

import re
import unicodedata

# (patron, nombre_de_skill). El orden importa: gana el primero que matchea.
#
# Los patrones usan \b para no matchear dentro de otra palabra: sin eso,
# "reproducelo ahora" dispararia la regla de la hora.
_REGLAS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(que hora es|dime la hora|dame la hora|la hora)\b"), "decir_hora"),
    (re.compile(r"\b(que dia es|que fecha|dime la fecha|la fecha)\b"), "decir_fecha"),
    (re.compile(r"^(hola|buenas|buenos dias|buenas tardes|buenas noches)\b"), "saludar"),
]


def _normalizar(texto: str) -> str:
    """Minusculas, sin tildes y sin signos de puntuacion.

    Whisper transcribe la misma frase con o sin tildes y con o sin signos de
    interrogacion segun la entonacion, asi que comparar en crudo falla la
    mitad de las veces.
    """
    sin_tildes = "".join(
        c
        for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^\w\s]", " ", sin_tildes).strip()


class RuleRouter:
    """Resuelve comandos frecuentes por coincidencia de patron."""

    def resolver(self, texto: str) -> tuple[str, dict] | None:
        """Devuelve (nombre_de_skill, argumentos) o None si es para el LLM."""
        if not texto.strip():
            return None

        normalizado = _normalizar(texto)
        for patron, skill in _REGLAS:
            if patron.search(normalizado):
                return skill, {}

        return None
