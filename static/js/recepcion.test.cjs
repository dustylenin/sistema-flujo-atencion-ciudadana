"use strict";

// Pruebas de respuestas fuera de orden y alternativa ante fallos sin dependencias.
const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const vm = require("node:vm");

function pantalla() {
  const pendientes = [];
  const eventos = {};
  const ventana = {};
  const ocultos = [];
  const oficina = {value: "", options: [{}, {}], addEventListener: (name, fn) => { eventos[name] = fn; }};
  const tramite = {
    disabled: false, options: [],
    replaceChildren(...options) { this.options = options; },
    add(option) { this.options.push(option); },
  };
  const estado = {textContent: ""};
  const registrar = {disabled: false, textContent: "Registrar atención"};
  const form = {
    dataset: {tramitesUrl: "/recepcion/tramites/"},
    addEventListener: (name, fn) => { eventos[name] = fn; },
    append: (input) => { ocultos.push(input); },
    querySelectorAll: () => ocultos,
  };
  const elementos = {"nueva-atencion": form, id_oficina: oficina, id_tramite: tramite, "estado-tramites": estado, registrar};
  vm.runInNewContext(readFileSync(`${__dirname}/recepcion.js`, "utf8"), {
    document: {
      getElementById: (id) => elementos[id],
      createElement: () => ({remove() { ocultos.splice(ocultos.indexOf(this), 1); }}),
    },
    window: {location: {href: "http://localhost/recepcion/"}, addEventListener: (name, fn) => { ventana[name] = fn; }},
    URL, AbortController,
    Option: function(text, value) { this.text = text; this.value = value; },
    fetch: (url, options) => new Promise((resolve, reject) => { pendientes.push({url, options, resolve, reject}); }),
  });
  return {oficina, tramite, estado, registrar, pendientes, eventos, ventana, ocultos};
}

function respuesta(id, nombre) {
  return {ok: true, json: async () => ({tramites: [{id, nombre}]})};
}

test("una respuesta atrasada no reemplaza los trámites de la oficina vigente", async () => {
  const p = pantalla();
  p.oficina.value = "1";
  const primera = p.eventos.change();
  p.oficina.value = "2";
  const segunda = p.eventos.change();
  assert.equal(p.pendientes[0].options.signal.aborted, true);
  assert.equal(p.pendientes[1].url.searchParams.get("oficina"), "2");
  p.pendientes[1].resolve(respuesta(20, "Trámite vigente"));
  await segunda;
  // Simula una respuesta que llega aun después de cancelar la petición.
  p.pendientes[0].resolve(respuesta(10, "Trámite anterior"));
  await primera;
  assert.equal(p.tramite.options[1].text, "Trámite vigente");
  assert.equal(p.tramite.disabled, false);
});

test("vaciar la oficina descarta una respuesta pendiente", async () => {
  const p = pantalla();
  p.oficina.value = "1";
  const primera = p.eventos.change();
  p.oficina.value = "";
  await p.eventos.change();
  p.pendientes[0].resolve(respuesta(10, "Trámite anterior"));
  await primera;
  assert.equal(p.tramite.options.length, 1);
  assert.equal(p.tramite.options[0].value, "");
  assert.equal(p.tramite.disabled, false);
});

test("un fallo de red o una sesión vencida ofrece Cargar trámites", async () => {
  for (const tipo of ["red", "http", "html"]) {
    const p = pantalla();
    p.oficina.value = "1";
    const carga = p.eventos.change();
    if (tipo === "red") p.pendientes[0].reject(new Error("sin conexión"));
    if (tipo === "http") p.pendientes[0].resolve({ok: false});
    if (tipo === "html") p.pendientes[0].resolve({ok: true, json: async () => { throw new Error("HTML de login"); }});
    await carga;
    assert.match(p.estado.textContent, /Pulsa Cargar trámites/);
    assert.equal(p.tramite.disabled, false);
    assert.equal(p.tramite.options.length, 1);
  }
});

test("la ayuda visual preserva la acción del POST y se restaura al volver", () => {
  const p = pantalla();
  p.eventos.submit({submitter: {value: "cargar_tramites"}});
  assert.equal(p.ocultos.length, 0);
  assert.equal(p.registrar.disabled, false);
  p.eventos.submit({submitter: p.registrar});
  assert.equal(p.ocultos[0].name, "accion");
  assert.equal(p.ocultos[0].value, "registrar");
  assert.equal(p.registrar.disabled, true);
  p.ventana.pageshow();
  assert.equal(p.ocultos.length, 0);
  assert.equal(p.registrar.disabled, false);
  assert.equal(p.registrar.textContent, "Registrar atención");
  p.oficina.options = [{}];
  p.ventana.pageshow();
  assert.equal(p.registrar.disabled, true);
});
