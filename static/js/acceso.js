"use strict";

const contrasena = document.getElementById("id_password");
const control = document.getElementById("mostrar-contrasena");
const contenedor = document.getElementById("control-contrasena");

if (contrasena && control && contenedor) {
  control.checked = false;
  contrasena.type = "password";
  control.addEventListener("change", () => {
    contrasena.type = control.checked ? "text" : "password";
  });
  contenedor.hidden = false;
}
