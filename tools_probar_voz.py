"""
Escucha las voces disponibles y mide su latencia.

    py -3.11 tools_probar_voz.py              # la voz configurada
    py -3.11 tools_probar_voz.py --todas      # compara todas las descargadas
    py -3.11 tools_probar_voz.py "texto"      # dice lo que le pases

La latencia del TTS es la parte mas lenta de toda la respuesta de Jarvis
(mas que Whisper), asi que elegir voz es elegir cuanto tarda en contestarte.
"""

import statistics
import sys
import time

from core.config import TTSConfig, cargar_config
from voice.piper_tts import DIRECTORIO_VOCES, PiperTTS

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FRASE = "Son las tres y cinco de la tarde."


def voces_descargadas() -> list[str]:
    return sorted(p.stem for p in DIRECTORIO_VOCES.glob("*.onnx"))


def medir(tts: PiperTTS, texto: str, repeticiones: int = 5) -> tuple[float, float]:
    """Devuelve (mediana_ms, segundos_de_audio)."""
    for _ in range(2):
        tts.sintetizar(texto)  # calentar: la primera siempre miente

    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        audio = tts.sintetizar(texto)
        tiempos.append((time.perf_counter() - inicio) * 1000)

    return statistics.median(tiempos), len(audio) / tts.frecuencia


def main() -> None:
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    texto = argumentos[0] if argumentos else FRASE

    if "--todas" in sys.argv:
        disponibles = voces_descargadas()
        if not disponibles:
            sys.exit(f"No hay voces en {DIRECTORIO_VOCES}.")

        print(f'Comparando {len(disponibles)} voces con: "{texto}"\n')
        print(f"{'voz':<24} {'latencia':>10} {'audio':>8}")
        print("-" * 46)

        resultados = []
        for nombre in disponibles:
            tts = PiperTTS(TTSConfig(voice=nombre))
            ms, segundos = medir(tts, texto)
            resultados.append((ms, nombre, tts))
            print(f"{nombre:<24} {ms:>9.0f}ms {segundos:>7.2f}s")

        print("\nAhora las vas a escuchar en orden, de más rápida a más lenta.\n")
        import asyncio

        for ms, nombre, tts in sorted(resultados):
            print(f"  {nombre}  ({ms:.0f} ms)")
            asyncio.run(tts.decir(texto))
        return

    config = cargar_config()
    print(f"Voz configurada: {config.tts.voice}")

    inicio = time.perf_counter()
    tts = PiperTTS(config.tts)
    print(f"Carga          : {time.perf_counter() - inicio:.1f} s")

    ms, segundos = medir(tts, texto)
    print(f"Latencia       : {ms:.0f} ms para {segundos:.2f} s de audio")

    if ms > 1500:
        print("\n  Lento. Probá --todas para comparar con una voz más liviana.")

    print(f'\nDiciendo: "{texto}"')
    import asyncio

    asyncio.run(tts.decir(texto))
    print("\n¿Se escuchó bien? Si no, revisá el volumen y el dispositivo de salida.")


if __name__ == "__main__":
    main()
