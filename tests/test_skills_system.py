from datetime import datetime

from skills.system import DecirFechaSkill, DecirHoraSkill, SaludarSkill


async def test_decir_hora_responde_con_la_hora_actual():
    resultado = await DecirHoraSkill().execute(DecirHoraSkill.params_model())
    ahora = datetime.now()

    assert resultado.ok is True
    assert str(ahora.hour % 12 or 12) in resultado.speech


async def test_decir_hora_habla_en_formato_natural():
    # "son las 3 y 5", no "15:05:32" — lo tiene que decir una voz.
    resultado = await DecirHoraSkill().execute(DecirHoraSkill.params_model())
    assert ":" not in resultado.speech
    assert "son las" in resultado.speech.lower()


async def test_decir_hora_devuelve_el_iso_en_data():
    # data no se pronuncia: es para la interfaz.
    resultado = await DecirHoraSkill().execute(DecirHoraSkill.params_model())
    assert "iso" in (resultado.data or {})


async def test_decir_fecha_incluye_el_dia_del_mes():
    resultado = await DecirFechaSkill().execute(DecirFechaSkill.params_model())
    assert str(datetime.now().day) in resultado.speech


async def test_decir_fecha_esta_en_espanol():
    meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre")
    resultado = await DecirFechaSkill().execute(DecirFechaSkill.params_model())
    assert any(m in resultado.speech.lower() for m in meses)


async def test_saludar_responde_algo():
    resultado = await SaludarSkill().execute(SaludarSkill.params_model())
    assert resultado.ok is True
    assert len(resultado.speech) > 0


def test_los_nombres_coinciden_con_los_del_router():
    # Si estos nombres no coinciden con brain/router.py, el router resuelve
    # una skill que el registro no encuentra y Jarvis responde "no se hacer eso".
    assert DecirHoraSkill.name == "decir_hora"
    assert DecirFechaSkill.name == "decir_fecha"
    assert SaludarSkill.name == "saludar"


def test_todas_las_reglas_del_router_tienen_una_skill():
    # Test de integracion barato entre los dos modulos: cada nombre que el
    # router puede devolver tiene que existir como skill.
    from brain.router import _REGLAS

    disponibles = {DecirHoraSkill.name, DecirFechaSkill.name, SaludarSkill.name}
    for _, nombre in _REGLAS:
        assert nombre in disponibles, f"el router resuelve '{nombre}' pero no existe"
