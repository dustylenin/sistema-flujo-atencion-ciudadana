from django import forms
from django.contrib.auth.forms import AuthenticationForm


ERROR_ACCESO = "No fue posible iniciar sesión. Verifica tu usuario y contraseña."


class FormularioAcceso(AuthenticationForm):
    error_messages = {"invalid_login": ERROR_ACCESO, "inactive": ERROR_ACCESO}

    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        for field in self.fields.values():
            field.widget.attrs["class"] = "campo-acceso"

    def clean(self):
        try:
            return super().clean()
        except forms.ValidationError:
            for field in self.fields.values():
                field.widget.attrs.update({
                    "aria-invalid": "true", "aria-describedby": "error-acceso",
                })
            raise
