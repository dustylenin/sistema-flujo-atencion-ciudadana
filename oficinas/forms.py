from django import forms
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower, Trim

from .models import Oficina


class FormularioOficina(forms.Form):
    nombre = forms.CharField(
        max_length=150,
        required=True,
        error_messages={"required": "El nombre debe tener contenido."},
        widget=forms.TextInput(
            attrs={
                "class": "campo",
                "placeholder": "Ej. Licencias y Tránsito",
                "id": "id_nombre",
            }
        ),
        label="Nombre",
    )
    descripcion = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "campo",
                "rows": 3,
                "placeholder": "Descripción opcional de la oficina",
                "id": "id_descripcion",
            }
        ),
        label="Descripción",
    )
    activo = forms.CharField(
        required=False,
        initial="true",
        widget=forms.Select(
            choices=[("true", "Activa"), ("false", "Inactiva")],
            attrs={"class": "campo", "id": "id_activo"},
        ),
        label="Estado",
    )

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()
        if not nombre:
            raise ValidationError("El nombre debe tener contenido.")
        if (
            Oficina.objects.annotate(n_lower=Lower(Trim("nombre")))
            .filter(n_lower=nombre.lower())
            .exists()
        ):
            raise ValidationError("Ya existe una oficina con este nombre.")
        return nombre

    def clean_activo(self):
        val = self.cleaned_data.get("activo")
        if val is None or val == "":
            return True
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        if s in ("false", "0", "off", "no"):
            return False
        return True
