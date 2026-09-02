"""Los eventos son el contrato entre capas: se testean como tal."""

import dataclasses

import pytest

from core.events import (
    ErrorOccurred,
    SpeakFinished,
    SpeakRequested,
    SpeechTranscribed,
    StateChanged,
    WakeDetected,
)


def test_wake_detected_lleva_origen_y_confianza():
    evento = WakeDetected(source="clap", confidence=0.92)
    assert evento.source == "clap"
    assert evento.confidence == 0.92
    assert evento.timestamp > 0


def test_speech_transcribed_lleva_texto_y_duracion():
    evento = SpeechTranscribed(text="qué hora es", language="es", duration_s=1.4)
    assert evento.text == "qué hora es"
    assert evento.language == "es"
    assert evento.duration_s == 1.4


def test_speak_requested_es_interrumpible_por_defecto():
    assert SpeakRequested(text="hola").interruptible is True


def test_los_eventos_son_inmutables():
    # Un evento es un hecho ocurrido. Si un handler pudiera mutarlo, el
    # siguiente handler veria algo distinto y el bug seria irrastreable.
    evento = SpeechTranscribed(text="hola", language="es", duration_s=1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        evento.text = "otra cosa"


def test_el_timestamp_se_rellena_solo():
    assert WakeDetected(source="wakeword", confidence=0.7).timestamp > 0


def test_state_changed_lleva_estado_viejo_y_nuevo():
    evento = StateChanged(old="idle", new="listening")
    assert (evento.old, evento.new) == ("idle", "listening")


def test_error_occurred_lleva_donde_y_que():
    evento = ErrorOccurred(where="ears.stt", message="modelo no encontrado")
    assert evento.where == "ears.stt"
    assert "modelo" in evento.message


def test_speak_finished_existe_para_cerrar_el_gate():
    # ui/ y ears/ dependen de este evento para saber cuando volver a escuchar.
    assert SpeakFinished().timestamp > 0
