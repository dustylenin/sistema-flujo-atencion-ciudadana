"""Captura de Recepción; la escritura y validación final pertenecen al servicio."""

from django import forms

from oficinas.models import Oficina
from tramites.models import Tramite

from .models import validar_nombre_completo


def oficinas_disponibles():
    return Oficina.objects.filter(activo=True, tramites__activo=True).distinct().order_by("nombre", "pk")


def tramites_disponibles(oficina_id):
    return Tramite.objects.filter(
        oficina_id=oficina_id, oficina__activo=True, activo=True,
    ).order_by("nombre", "pk")


class OpcionCatalogo(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.nombre


class FormularioOficina(forms.Form):
    oficina = OpcionCatalogo(
        label="Oficina", queryset=Oficina.objects.none(), empty_label="Selecciona una oficina",
        error_messages={
            "required": "Selecciona una oficina.",
            "invalid_choice": "Selecciona una oficina activa con trámites disponibles.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["oficina"].queryset = oficinas_disponibles()


class FormularioNuevaAtencion(FormularioOficina):
    nombre_completo = forms.CharField(
        label="Nombre completo", strip=False, validators=[validar_nombre_completo],
        error_messages={"required": "Escribe el nombre completo del ciudadano."},
    )
    correo = forms.EmailField(label="Correo electrónico", required=False, max_length=254)
    telefono = forms.CharField(
        label="Teléfono", required=False, strip=False, widget=forms.TextInput(attrs={"type": "tel"}),
    )
    tramite = OpcionCatalogo(
        label="Trámite", queryset=Tramite.objects.none(), empty_label="Primero selecciona una oficina",
        error_messages={
            "required": "Selecciona un trámite de la oficina elegida.",
            "invalid_choice": "Selecciona un trámite activo de la oficina elegida.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["correo"].strip = False
        valor_oficina = self.data.get("oficina") if self.is_bound else self.initial.get("oficina")
        try:
            oficina = self.fields["oficina"].clean(valor_oficina)
        except forms.ValidationError:
            oficina = None
        if oficina:
            self.fields["tramite"].queryset = tramites_disponibles(oficina.pk)
            self.fields["tramite"].empty_label = "Selecciona un trámite"
        self.order_fields(["nombre_completo", "correo", "telefono", "oficina", "tramite"])
        for name, field in self.fields.items():
            field.widget.attrs.update({"class": "campo", "aria-describedby": f"ayuda-{name}"})
        self.fields["nombre_completo"].widget.attrs["autocomplete"] = "off"
        self.fields["correo"].widget.attrs["autocomplete"] = "off"
        self.fields["telefono"].widget.attrs["autocomplete"] = "off"

    def marcar_errores(self):
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs.update({
                    "aria-invalid": "true",
                    "aria-describedby": f"ayuda-{name} error-{name}",
                })
