from django import forms
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower, Trim

from oficinas.models import Oficina
from .models import Tramite


class FormularioTramite(forms.Form):
    nombre = forms.CharField(
        max_length=150,
        required=True,
        error_messages={"required": "El nombre debe tener contenido."},
        widget=forms.TextInput(
            attrs={
                "class": "campo",
                "placeholder": "Ej. Licencia de conducir",
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
                "placeholder": "Descripción opcional del trámite",
                "id": "id_descripcion",
            }
        ),
        label="Descripción",
    )
    oficina_id = forms.ModelChoiceField(
        queryset=Oficina.objects.filter(activo=True),
        required=True,
        error_messages={"required": "La oficina es obligatoria."},
        widget=forms.Select(
            attrs={"class": "campo", "id": "id_oficina_id"},
        ),
        label="Oficina responsable",
        empty_label="Selecciona una oficina",
    )
    activo = forms.CharField(
        required=False,
        initial="true",
        widget=forms.Select(
            choices=[("true", "Activo"), ("false", "Inactivo")],
            attrs={"class": "campo", "id": "id_activo"},
        ),
        label="Estado",
    )

    def __init__(self, *args, **kwargs):
        # Asegura que si los datos vienen con clave 'oficina' en vez de 'oficina_id', se mapee correctamente
        if args and hasattr(args[0], "copy"):
            data = args[0].copy()
            if "oficina" in data and "oficina_id" not in data:
                data["oficina_id"] = data["oficina"]
            args = (data,) + args[1:]
        super().__init__(*args, **kwargs)
        # Refresca el queryset de oficinas activas en cada instanciación
        self.fields["oficina_id"].queryset = Oficina.objects.filter(activo=True)

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()
        if not nombre:
            raise ValidationError("El nombre debe tener contenido.")
        return nombre

    def clean_activo(self):
        val = self.cleaned_data.get("activo")
        if val is None or val == "":
            return True
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        if s in ("false", "0", "off", "no", "inactivo"):
            return False
        return True

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get("nombre")
        oficina = cleaned_data.get("oficina_id")
        if nombre and oficina:
            if (
                Tramite.objects.filter(oficina=oficina)
                .annotate(n_lower=Lower(Trim("nombre")))
                .filter(n_lower=nombre.lower())
                .exists()
            ):
                raise ValidationError(
                    {"nombre": f"Ya existe el trámite «{nombre}» en la oficina seleccionada."}
                )
        return cleaned_data
