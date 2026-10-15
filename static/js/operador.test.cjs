"use strict";

// Preparadas para ejecución posterior; no ejecutarlas durante la conservación DEMO.
const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const vm = require("node:vm");

function pantalla(conMensaje = false) {
  const ventana = {};
  let focos = 0;
  const formularios = ["Llamar siguiente", "Confirmar pausa"].map((texto) => {
    const eventos = {};
    const atributos = {};
    const boton = {textContent: texto, disabled: false};
    const form = {
      // La ayuda visual no debe modificar ninguna parte de la intención.
      elements: Object.freeze({token: Object.freeze({value: "intencion-original"}), motivo: Object.freeze({value: "  Motivo  "})}),
      querySelector: () => boton,
      addEventListener: (nombre, funcion) => { eventos[nombre] = funcion; },
      getAttribute: (nombre) => atributos[nombre],
      setAttribute: (nombre, valor) => { atributos[nombre] = valor; },
      removeAttribute: (nombre) => { delete atributos[nombre]; },
    };
    boton.closest = () => form;
    return {form, boton, eventos};
  });
  vm.runInNewContext(readFileSync(`${__dirname}/operador.js`, "utf8"), {
    document: {
      querySelectorAll: () => formularios.map((f) => f.form),
      querySelector: () => conMensaje ? {focus: () => { focos++; }} : null,
    },
    window: {addEventListener: (nombre, funcion) => { ventana[nombre] = funcion; }},
    fetch: () => { throw new Error("No debe emitir solicitudes por JavaScript"); },
  });
  return {formularios, ventana, focos: () => focos};
}

test("el primer envío permanece nativo y conserva intención y captura", () => {
  const {form, boton, eventos} = pantalla().formularios[0];
  let cancelado = false;
  eventos.submit({preventDefault: () => { cancelado = true; }});
  assert.equal(cancelado, false);
  assert.equal(boton.disabled, true);
  assert.equal(form.getAttribute("aria-busy"), "true");
  assert.equal(form.elements.token.value, "intencion-original");
  assert.equal(form.elements.motivo.value, "  Motivo  ");
});

test("un doble envío se detiene visualmente sin afectar otro formulario", () => {
  const p = pantalla();
  const uno = p.formularios[0];
  let cancelados = 0;
  const evento = {preventDefault: () => { cancelados++; }};
  uno.eventos.submit(evento);
  uno.eventos.submit(evento);
  p.formularios[1].eventos.submit(evento);
  assert.equal(cancelados, 1);
});

test("volver a la página permite reintentar con los mismos datos", () => {
  const p = pantalla();
  const {form, boton, eventos} = p.formularios[0];
  eventos.submit({preventDefault() {}});
  p.ventana.pageshow();
  assert.equal(boton.disabled, false);
  assert.equal(boton.textContent, "Llamar siguiente");
  assert.equal(form.getAttribute("aria-busy"), undefined);
  assert.equal(form.elements.token.value, "intencion-original");
});

test("los mensajes reciben foco y la página sin mensajes sigue funcionando", () => {
  assert.equal(pantalla(true).focos(), 1);
  assert.equal(pantalla(false).focos(), 0);
});
