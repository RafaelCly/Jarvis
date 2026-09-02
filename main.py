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

# Windows usa cp1252 por defecto, asi que "todavía" sale como "todav?a" en
# cuanto se redirige la salida. Todo lo que dice Jarvis lleva acentos.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from core.bus import EventBus
from core.events import SpeakRequested, SpeechTranscribed
from core.state import State, StateMachine
from skills.base import Skill, SkillResult
from skills.ping import PingSkill

console = Console()


class JarvisApp:
    """Cablea el bus, la maquina de estados y las skills."""

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.maquina = StateMachine(bus)
        self.skills: dict[str, Skill] = {}

        self._registrar(PingSkill())

    def _registrar(self, skill: Skill) -> None:
        self.skills[skill.name] = skill

    async def procesar_texto(self, texto: str) -> str:
        """Recorre el pipeline desde texto ya transcrito hasta la respuesta."""
        await self.maquina.transition_to(State.LISTENING)
        await self.bus.publish(
            SpeechTranscribed(text=texto, language="es", duration_s=0.0)
        )

        await self.maquina.transition_to(State.TRANSCRIBING)
        await self.maquina.transition_to(State.THINKING)

        # Despacho provisional por nombre exacto. La tarea 1.R4 lo reemplaza
        # por el router de reglas y el registro de skills.
        skill = self.skills.get(texto.strip().lower())
        if skill is None:
            resultado = SkillResult(ok=False, speech="No sé hacer eso todavía.")
        else:
            await self.maquina.transition_to(State.ACTING)
            resultado = await skill.execute(skill.params_model())

        await self.maquina.transition_to(State.SPEAKING)
        await self.bus.publish(SpeakRequested(text=resultado.speech))
        await self.maquina.transition_to(State.IDLE)

        return resultado.speech


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
