"use strict";

(() => {
  // Ayuda visual solamente: no cambia tokens, claves, argumentos o destinos,
  // no intercepta la petición y no reintenta ni genera solicitudes.
  const botones = new Map();
  document.querySelectorAll("form[data-envio-operador]").forEach((form) => {
    const boton = form.querySelector('button[type="submit"]');
    if (!boton) return;
    botones.set(boton, boton.textContent);
    form.addEventListener("submit", (event) => {
      if (form.getAttribute("aria-busy") === "true") {
        event.preventDefault();
        return;
      }
      form.setAttribute("aria-busy", "true");
      boton.disabled = true;
      boton.textContent = "Enviando…";
    });
  });
  window.addEventListener("pageshow", () => {
    botones.forEach((texto, boton) => {
      boton.disabled = false;
      boton.textContent = texto;
      boton.closest("form").removeAttribute("aria-busy");
    });
  });
  const mensaje = document.querySelector("[data-foco-mensajes]");
  if (mensaje) mensaje.focus();
})();
