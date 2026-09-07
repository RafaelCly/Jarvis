"""
Lista los dispositivos de entrada y prueba cuales sirven para Jarvis.

    py -3.11 tools_listar_dispositivos.py

Un dispositivo sirve solo si acepta abrirse a 16 kHz mono, que es lo que
esperan openWakeWord, silero-vad y Whisper.

Dos trampas que este script hace visibles:

  - WASAPI suele RECHAZAR 16 kHz. Su modo compartido no reconvierte y la
    frecuencia nativa del hardware es 44.1 o 48 kHz. Aparece con la mejor
    latencia de la lista y luego no abre.
  - Los auriculares Bluetooth aparecen como "Hands-Free". Al abrirles el
    microfono, Windows degrada TODA la salida de audio a mono 8 kHz
    (PLAN.md §2). Nunca elegirlos.
"""

import sys

import sounddevice as sd

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FRECUENCIA = 16000

# Drivers de Windows que solo existen para audio Bluetooth.
_DRIVERS_BLUETOOTH = ("bthhfenum", "btha2dp", "bthenum")

# WDM-KS toma el microfono en modo exclusivo: si Jarvis lo abre, ninguna
# otra app puede grabar, y si otra lo tiene, Jarvis no arranca. Sirve, pero
# no como primera opcion para algo que corre todo el dia en segundo plano.
_APIS_PENALIZADAS = ("WDM-KS",)

# Dispositivos virtuales que redirigen al "predeterminado de Windows". Si el
# predeterminado son unos auriculares Bluetooth, Jarvis termina usandolos sin
# enterarse. El plan exige un indice fisico explicito (PLAN.md §2).
_VIRTUALES = (
    "asignador de sonido",
    "sound mapper",
    "controlador primario",
    "primary sound",
    "mapeador",
)


def acepta_16k(indice: int) -> bool:
    """Intenta abrir el dispositivo a 16 kHz mono."""
    try:
        sd.check_input_settings(
            device=indice, samplerate=FRECUENCIA, channels=1, dtype="int16"
        )
        return True
    except Exception:
        return False


def nombres_bluetooth() -> set[str]:
    """Nombres de dispositivos que Windows expone por un driver Bluetooth.

    No se puede buscar la palabra "Bluetooth" en el nombre: unos auriculares
    aparecen como "Auriculares con micrófono (Redmi Buds 6 Play)", sin
    ninguna pista. Pero los MISMOS auriculares aparecen tambien bajo
    bthhfenum.sys, y de ahi se saca el nombre real del aparato para vetarlo
    en todas sus apariciones.
    """
    encontrados: set[str] = set()

    for dispositivo in sd.query_devices():
        nombre = dispositivo["name"]
        if not any(d in nombre.lower() for d in _DRIVERS_BLUETOOTH):
            continue
        # El nombre del aparato viene entre parentesis al final.
        if "(" in nombre:
            crudo = nombre[nombre.rfind("(") + 1 :]
            encontrados.add(crudo.strip(" )\r\n"))

    return {n for n in encontrados if len(n) > 3}


def _es_bluetooth(nombre: str, aparatos_bt: set[str]) -> bool:
    """True si este dispositivo es uno de los aparatos Bluetooth detectados.

    MME trunca los nombres a 31 caracteres, asi que los mismos auriculares
    aparecen como "Auriculares con micrófono (Redm". Por eso no alcanza con
    buscar el nombre completo: hay que probar tambien si el nombre del
    dispositivo termina con un trozo inicial del nombre del aparato.
    """
    if any(d in nombre.lower() for d in _DRIVERS_BLUETOOTH):
        return True

    for aparato in aparatos_bt:
        if aparato in nombre:
            return True
        # El nombre truncado deja un prefijo del aparato al final, tras "(".
        if "(" in nombre:
            cola = nombre[nombre.rfind("(") + 1 :].strip(" )")
            if len(cola) >= 4 and aparato.startswith(cola):
                return True

    return False


def main() -> None:
    apis = sd.query_hostapis()
    bluetooth = nombres_bluetooth()
    candidatos = []

    if bluetooth:
        print(f"Aparatos Bluetooth detectados y vetados: {', '.join(sorted(bluetooth))}\n")

    print(f"Dispositivos de entrada, probados a {FRECUENCIA} Hz mono:\n")

    for indice, dispositivo in enumerate(sd.query_devices()):
        if dispositivo["max_input_channels"] <= 0:
            continue

        nombre = " ".join(dispositivo["name"].split())
        api = apis[dispositivo["hostapi"]]["name"]
        latencia_ms = dispositivo["default_low_input_latency"] * 1000
        es_bluetooth = _es_bluetooth(nombre, bluetooth)
        es_virtual = any(v in nombre.lower() for v in _VIRTUALES)
        penalizada = any(a in api for a in _APIS_PENALIZADAS)

        if not acepta_16k(indice):
            marca = "NO 16kHz"
        elif es_bluetooth:
            marca = "BLUETOOTH"
        elif es_virtual:
            marca = "VIRTUAL "
        else:
            marca = "  OK    "
            # La penalizacion ordena, no descarta: WDM-KS queda al final.
            candidatos.append((penalizada, latencia_ms, indice, nombre, api))

        print(f"  [{indice:>2}] {marca:<9} {api:<20} {latencia_ms:>6.0f} ms  {nombre[:45]}")

    print()
    if not candidatos:
        print("Ningun dispositivo acepta 16 kHz sin ser Bluetooth.")
        print("Revisa los drivers de audio del microfono interno.")
        return

    penalizada, latencia, indice, nombre, api = min(candidatos)
    print(f"Recomendado: [{indice}] {nombre}")
    print(f"             {api}, {latencia:.0f} ms de latencia")
    print("\nPonelo en config.local.yaml:\n")
    print("audio:")
    print(f"  input_device_index: {indice}")


if __name__ == "__main__":
    main()
