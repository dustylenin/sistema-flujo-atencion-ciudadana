"""Intenciones firmadas de interfaz; los servicios conservan la autorización."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from django import forms
from django.core import signing

from .models import SolicitudOperador, validar_motivo


DESTINOS_OPERADOR = frozenset({"usuarios:operacion", "usuarios:operador_actual"})
_SALT = "folios.operador.formulario.v1"
_CAMPOS = {"actor_id", "operacion", "solicitud_id", "destino", "pausa_id"}


@dataclass(frozen=True)
class IntencionOperador:
    solicitud_id: UUID
    destino: str
    pausa_id: int | None


class FormularioOperacion(forms.Form):
    token = forms.CharField(
        widget=forms.HiddenInput, strip=False, max_length=2048,
        error_messages={"required": "El formulario no tiene una intención válida. Vuelve a la pantalla de Operador."},
    )
    operacion = None

    def __init__(self, *args, actor, destino="usuarios:operacion", pausa_id=None, **kwargs):
        kwargs.setdefault("auto_id", f"id_{self.operacion.lower()}_%s")
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.intencion = None
        if not self.is_bound:
            if destino not in DESTINOS_OPERADOR:
                raise ValueError("Destino de Operador no permitido.")
            if self.operacion == SolicitudOperador.Operacion.REANUDAR:
                if type(pausa_id) is not int or pausa_id <= 0:
                    raise ValueError("Reanudar requiere una pausa concreta.")
            elif pausa_id is not None:
                raise ValueError("Solo reanudar recibe una pausa objetivo.")
            self.initial["token"] = signing.dumps({
                "actor_id": actor.pk, "operacion": self.operacion,
                "solicitud_id": str(uuid4()), "destino": destino, "pausa_id": pausa_id,
            }, salt=_SALT)

    def clean_token(self):
        token = self.cleaned_data["token"]
        try:
            datos = signing.loads(token, salt=_SALT)
            if not isinstance(datos, dict) or set(datos) != _CAMPOS:
                raise ValueError
            if (
                type(datos["actor_id"]) is not int or datos["actor_id"] != self.actor.pk
                or datos["operacion"] != self.operacion
                or not isinstance(datos["destino"], str) or datos["destino"] not in DESTINOS_OPERADOR
                or not isinstance(datos["solicitud_id"], str)
            ):
                raise ValueError
            if self.operacion == SolicitudOperador.Operacion.REANUDAR:
                if type(datos["pausa_id"]) is not int or datos["pausa_id"] <= 0:
                    raise ValueError
            elif datos["pausa_id"] is not None:
                raise ValueError
            self.intencion = IntencionOperador(
                UUID(datos["solicitud_id"]), datos["destino"], datos["pausa_id"],
            )
        except (signing.BadSignature, TypeError, ValueError) as error:
            raise forms.ValidationError(
                "El formulario no es válido para esta cuenta o acción. Vuelve a la pantalla de Operador.",
            ) from error
        return token

    def marcar_errores(self):
        for nombre in self.errors:
            if nombre in self.fields and not self.fields[nombre].widget.is_hidden:
                self.fields[nombre].widget.attrs.update({
                    "aria-invalid": "true", "aria-describedby": f"ayuda-{nombre} error-{nombre}",
                })


class FormularioLlamar(FormularioOperacion):
    operacion = SolicitudOperador.Operacion.LLAMAR


class FormularioPausa(FormularioOperacion):
    operacion = SolicitudOperador.Operacion.PAUSAR
    motivo = forms.CharField(
        label="Motivo de la pausa", strip=False, validators=[validar_motivo],
        widget=forms.Textarea(attrs={
            "class": "campo", "rows": 3, "aria-describedby": "ayuda-motivo",
        }),
        error_messages={"required": "Escribe el motivo de la pausa."},
    )


class FormularioReanudar(FormularioOperacion):
    operacion = SolicitudOperador.Operacion.REANUDAR
