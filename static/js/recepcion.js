"use strict";

(() => {
  const form = document.getElementById("nueva-atencion");
  if (!form) return;
  const oficina = document.getElementById("id_oficina");
  const tramite = document.getElementById("id_tramite");
  const estado = document.getElementById("estado-tramites");
  const registrar = document.getElementById("registrar");
  let revision = 0;
  let peticion = null;

  oficina.addEventListener("change", async () => {
    const actual = ++revision;
    if (peticion) peticion.abort();
    tramite.replaceChildren(new Option("Primero selecciona una oficina", ""));
    if (!oficina.value) {
      tramite.disabled = false;
      estado.textContent = "Selecciona una oficina y carga sus trámites.";
      return;
    }
    peticion = new AbortController();
    tramite.disabled = true;
    estado.textContent = "Cargando trámites…";
    try {
      const url = new URL(form.dataset.tramitesUrl, window.location.href);
      url.searchParams.set("oficina", oficina.value);
      const response = await fetch(url, {
        signal: peticion.signal, credentials: "same-origin", headers: {Accept: "application/json"},
      });
      if (!response.ok) throw new Error("No fue posible cargar los trámites.");
      const datos = await response.json();
      if (actual !== revision) return;
      tramite.replaceChildren(new Option("Selecciona un trámite", ""));
      for (const opcion of datos.tramites) tramite.add(new Option(opcion.nombre, opcion.id));
      estado.textContent = datos.tramites.length
        ? "Trámites actualizados. Selecciona el trámite."
        : "La oficina ya no tiene trámites disponibles. Selecciona otra oficina.";
    } catch (error) {
      if (actual !== revision) return;
      estado.textContent = "No fue posible cargar los trámites. Pulsa Cargar trámites para continuar.";
    } finally {
      if (actual === revision) tramite.disabled = false;
    }
  });

  form.addEventListener("submit", (event) => {
    if (event.submitter !== registrar) return;
    // El botón deshabilitado no forma parte del POST: preservar la acción.
    const accion = document.createElement("input");
    accion.type = "hidden";
    accion.name = "accion";
    accion.value = "registrar";
    form.append(accion);
    registrar.disabled = true;
    registrar.textContent = "Registrando…";
  });
  window.addEventListener("pageshow", () => {
    // Volver desde la confirmación puede restaurar una página del navegador.
    form.querySelectorAll('input[type="hidden"][name="accion"]').forEach((input) => input.remove());
    registrar.disabled = oficina.options.length <= 1;
    registrar.textContent = "Registrar atención";
  });
})();
