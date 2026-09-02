"""
Punto de entrada de Jarvis.

    python main.py              pipeline completo con microfono
    python main.py --text-mode  ordenes por teclado, sin audio

--text-mode recorre exactamente el mismo camino que el audio real, salvo
la captura y la transcripcion. Es la forma de trabajar en brain/ y skills/
sin microfono ni GPU.
"""

import argparse
import asyncio
import sys

from rich.console import Console

def _forzar_utf8() -> None:
    """Windows usa cp1252 por defecto y eso rompe los acentos.

    En la salida, "todavía" sale como "todav?a". En la entrada es peor:
    "qué hora es" llega como "quÃ© hora es" y el router deja de reconocerlo.

    stdin solo se toca si viene de una tuberia o un archivo. En una consola
    interactiva Python ya lee Unicode nativo, y reconfigurarlo lo empeora.
    """
    if sys.platform != "win32":
        return

    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")

    # Bajo pytest, sys.stdin es un doble sin reconfigure() ni isatty() util.
    try:
        if hasattr(sys.stdin, "reconfigure") and not sys.stdin.isatty():
            sys.stdin.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


_forzar_utf8()

from brain.registry import SkillRegistry
from brain.router import RuleRouter
from core.bus import EventBus
from core.events import SpeakRequested, SpeechTranscribed
from core.state import State, StateMachine
from skills.base import SkillResult
from skills.ping import PingSkill
from skills.system import DecirFechaSkill, DecirHoraSkill, SaludarSkill

console = Console()


class JarvisApp:
    """Cablea el bus, la maquina de estados, el router y las skills."""

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.maquina = StateMachine(bus)
        self.router = RuleRouter()
        self.registro = SkillRegistry()

        for skill in (
            PingSkill(),
            DecirHoraSkill(),
            DecirFechaSkill(),
            SaludarSkill(),
        ):
            self.registro.registrar(skill)

    async def procesar_texto(self, texto: str) -> str:
        """Recorre el pipeline desde texto ya transcrito hasta la respuesta."""
        await self.maquina.transition_to(State.LISTENING)
        await self.bus.publish(
            SpeechTranscribed(text=texto, language="es", duration_s=0.0)
        )

        await self.maquina.transition_to(State.TRANSCRIBING)
        await self.maquina.transition_to(State.THINKING)

        resultado = await self._decidir(texto)

        await self.maquina.transition_to(State.SPEAKING)
        await self.bus.publish(SpeakRequested(text=resultado.speech))
        await self.maquina.transition_to(State.IDLE)

        return resultado.speech

    async def _decidir(self, texto: str) -> SkillResult:
        """Router de reglas primero; lo que no matchea ira al LLM."""
        resuelto = self.router.resolver(texto)

        # "ping" no tiene regla porque es de diagnostico, no un comando real.
        if resuelto is None and texto.strip().lower() in self.registro.nombres():
            resuelto = (texto.strip().lower(), {})

        if resuelto is None:
            # Fase 2: acá se llama al LLM con tool calling.
            return SkillResult(
                ok=False, speech="Todavía no sé responder eso. Me falta el cerebro."
            )

        nombre, argumentos = resuelto
        await self.maquina.transition_to(State.ACTING)
        return await self.registro.ejecutar(nombre, argumentos)


async def bucle_texto(app: JarvisApp) -> None:
    """Lee ordenes de stdin hasta Ctrl-C o 'salir'."""
    console.print("[bold cyan]Jarvis en modo texto.[/] Escribí 'salir' para terminar.\n")

    while True:
        try:
            texto = await asyncio.to_thread(input, "> ")
        except (EOFError, KeyboardInterrupt):
            break

        if texto.strip().lower() in {"salir", "exit", "quit"}:
            break
        if not texto.strip():
            continue

        respuesta = await app.procesar_texto(texto)
        console.print(f"[bold green]Jarvis:[/] {respuesta}")

    console.print("\n[dim]Hasta luego.[/]")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis, asistente de voz local")
    parser.add_argument(
        "--text-mode",
        action="store_true",
        help="Leer ordenes por teclado en vez de por microfono",
    )
    args = parser.parse_args()

    bus = EventBus()
    bus.bind_loop(asyncio.get_running_loop())
    app = JarvisApp(bus=bus)

    if args.text_mode:
        await bucle_texto(app)
    else:
        console.print(
            "[yellow]El pipeline de audio llega en la Fase 1.[/] "
            "Mientras tanto: [bold]python main.py --text-mode[/]"
        )


if __name__ == "__main__":
    asyncio.run(main())
