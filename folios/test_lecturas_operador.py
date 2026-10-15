"""Lectores de Operador preparados; preservar DEMO antes de ejecutar el runner.

Requieren la configuración y las barreras PostgreSQL de las pruebas existentes.
Las escrituras de fixtures solo se ejecutan al correr estas pruebas aisladas.
"""

from dataclasses import FrozenInstanceError, asdict
from datetime import datetime, timedelta
from itertools import product
from unittest.mock import patch
from uuid import UUID, uuid4

from django.contrib.auth.models import AnonymousUser
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from oficinas.models import AsignacionOperadorOficina, EventoAsignacion, Oficina
from oficinas.services import reactivar_asignacion
from oficinas.testing import CatalogosPostgreSQLTestCase
from tramites.models import Tramite
from usuarios.models import Usuario

from .models import EventoDisponibilidad, EventoFolio, Folio, PausaOperador, SolicitudOperador
from .services_disponibilidad import Disponibilidad, consultar_disponibilidad
from .services_llamado import EstadoLlamado
from .services_operador import (
    FolioActualPropio, FolioPendiente, PaginaPendientesOperador,
    consultar_folio_actual_operador, consultar_pendientes_operador,
)
from .test_llamado import LlamadoFixturesMixin


LECTORES = (consultar_pendientes_operador, consultar_folio_actual_operador)
CAMPOS_FOLIO = {
    "folio_id", "nombre_completo", "estado", "llegada_original",
    "oficina_id", "oficina_nombre", "tramite_id", "tramite_nombre",
}


class LecturasOperadorTests(LlamadoFixturesMixin, CatalogosPostgreSQLTestCase):
    def setUp(self):
        self.preparar()

    def leer(self, lector=consultar_pendientes_operador, *, actor=None, **kwargs):
        with self.assertNumQueries(1), CaptureQueriesContext(connection) as consultas:
            resultado = lector(actor=actor or self.operador, **kwargs)
        sql = consultas[0]["sql"].upper()
        self.assertTrue(sql.lstrip().startswith("SELECT"))
        self.assertNotIn("FOR UPDATE", sql)
        self.assertNotIn("FOR SHARE", sql)
        self.assertIn('"USUARIOS_USUARIO"', sql)
        return resultado

    def ids(self, *, actor=None, cursor=None):
        pagina = self.leer(actor=actor, cursor=cursor)
        return [folio.folio_id for folio in pagina.pendientes]

    def estado_persistido(self):
        return tuple(
            list(modelo.objects.order_by("pk").values())
            for modelo in (
                Usuario, Oficina, Tramite, AsignacionOperadorOficina, EventoAsignacion,
                Folio, EventoFolio, PausaOperador, EventoDisponibilidad, SolicitudOperador,
            )
        )

    def test_cola_vacia_autorizada_y_actual_ausente(self):
        pagina = self.leer()
        self.assertEqual(pagina, PaginaPendientesOperador((), None))
        self.assertIsNone(self.leer(consultar_folio_actual_operador))

    def test_sin_asignaciones_no_oculta_la_diferencia_con_acceso_denegado(self):
        self.registrar()
        for asignacion in self.asignaciones.values():
            self.historica_inactiva(asignacion)
        self.assertEqual(self.leer(), PaginaPendientesOperador((), None))
        self.assertIsNone(self.leer(consultar_folio_actual_operador))
        for lector in LECTORES:
            with self.assertNumQueries(1), self.assertRaises(PermissionDenied):
                lector(actor=self.admin)

    def test_autenticacion_persistencia_y_alias(self):
        ajeno = Usuario.objects.get(pk=self.operador.pk)
        ajeno._state.db = "otra_base"
        for actor in (None, AnonymousUser(), object(), Usuario(rol="OPERADOR"),
                      Usuario(pk=self.operador.pk, rol="OPERADOR"), ajeno):
            for lector in LECTORES:
                with self.subTest(actor=type(actor).__name__, lector=lector.__name__):
                    with self.assertNumQueries(0), self.assertRaises(PermissionDenied):
                        lector(actor=actor)

    def test_usuario_que_ya_no_existe_no_autoriza(self):
        ausente = Usuario.objects.get(pk=self.operador.pk)
        ausente.pk += 1000000
        for lector in LECTORES:
            with self.assertNumQueries(1), self.assertRaises(PermissionDenied):
                lector(actor=ausente)

    def test_cuenta_desactivada_se_relee_con_instancia_obsoleta(self):
        self.registrar()
        self.llamar()
        obsoleto = Usuario.objects.get(pk=self.operador.pk)
        self.operador.is_active = False
        self.operador.save(update_fields=["is_active"])
        self.assertTrue(obsoleto.is_active)
        for lector in LECTORES:
            with self.assertNumQueries(1), self.assertRaises(PermissionDenied):
                lector(actor=obsoleto)

    def test_rol_se_relee_incluso_con_folio_propio(self):
        self.registrar()
        self.llamar()
        # Estado histórico controlado; no habilita salida pública de OPERADOR.
        self.escribir_sql("usuarios_usuario", "rol", "RECEPCION", self.operador.pk)
        self.assertEqual(self.operador.rol, "OPERADOR")
        for lector in LECTORES:
            with self.assertNumQueries(1), self.assertRaises(PermissionDenied):
                lector(actor=self.operador)

    def test_se_usan_valores_de_base_y_no_los_de_instancia(self):
        folio = self.registrar()
        self.llamar()
        self.operador.is_active = False
        self.operador.rol = "ADMINISTRADOR"
        self.assertEqual(self.leer(consultar_folio_actual_operador).folio_id, folio.pk)
        self.assertEqual(self.ids(), [])

    def test_todas_las_combinaciones_de_flags_no_sustituyen_el_rol(self):
        self.registrar()
        self.llamar()
        for actor, (staff, superuser) in product(
            (self.operador, self.admin, self.recepcion), product((False, True), repeat=2),
        ):
            actor.is_staff, actor.is_superuser = staff, superuser
            actor.save(update_fields=["is_staff", "is_superuser"])
            for lector in LECTORES:
                with self.subTest(rol=actor.rol, flags=(staff, superuser), lector=lector.__name__):
                    if actor.rol == "OPERADOR":
                        self.leer(lector, actor=actor)
                    else:
                        with self.assertNumQueries(1), self.assertRaises(PermissionDenied):
                            lector(actor=actor)

    def test_cola_conjunta_incluye_antiguos_y_excluye_oficinas_ajenas(self):
        ahora = timezone.now()
        self.registrar(self.ajena, ahora - timedelta(days=20))
        reciente = self.registrar(self.oficina, ahora)
        antiguo = self.registrar(self.segunda, ahora - timedelta(days=10))
        intermedio = self.registrar(self.oficina, ahora - timedelta(hours=1))
        self.assertEqual(self.ids(), [antiguo.pk, intermedio.pk, reciente.pk])

    def test_colas_compartidas_y_propias_de_varios_operadores(self):
        compartido = self.registrar(self.oficina)
        exclusivo = self.registrar(self.segunda)
        self.assertEqual(self.ids(), [compartido.pk, exclusivo.pk])
        self.assertEqual(self.ids(actor=self.otro), [compartido.pk])
        self.assertIsNone(self.leer(consultar_folio_actual_operador, actor=self.otro))

    def test_misma_llegada_desempata_por_uuid_y_coincide_con_llamado(self):
        instante = timezone.now()
        identificadores = [UUID(int=n) for n in (30, 10, 20)]
        for folio_id, oficina in zip(identificadores, (self.oficina, self.segunda, self.oficina)):
            # Controla solo la generación del UUID del fixture, también si
            # Django ya ha cacheado el callable predeterminado del campo.
            with patch.object(Folio._meta.get_field("id"), "get_default", return_value=folio_id):
                self.registrar(oficina, instante)
        self.assertEqual(self.ids(), sorted(identificadores))
        llamado = self.llamar()
        self.assertEqual(llamado.folio_id, min(identificadores))
        self.assertEqual(self.ids(), sorted(identificadores)[1:])

    def test_catalogos_desactivados_conservan_pendientes(self):
        primero = self.registrar(self.oficina)
        segundo = self.registrar(self.segunda)
        self.oficina.activo = False
        self.oficina.save(update_fields=["activo"])
        tramite = self.tramites[self.segunda.pk]
        tramite.activo = False
        tramite.save(update_fields=["activo"])
        self.assertEqual(self.ids(), [primero.pk, segundo.pk])

    def test_asignacion_inactiva_excluye_solo_sus_pendientes(self):
        self.registrar(self.oficina)
        vigente = self.registrar(self.segunda)
        self.historica_inactiva(self.asignaciones[self.oficina.pk])
        self.assertEqual(self.ids(), [vigente.pk])
        self.assertEqual(len(self.ids(actor=self.otro)), 1)

    def test_campos_y_tipos_de_pendiente(self):
        folio = self.registrar()
        pendiente = self.leer().pendientes[0]
        self.assertIsInstance(pendiente, FolioPendiente)
        self.assertEqual(set(asdict(pendiente)), CAMPOS_FOLIO)
        self.assertEqual(asdict(pendiente), {
            "folio_id": folio.pk, "nombre_completo": folio.nombre_completo,
            "estado": "EN_ESPERA", "llegada_original": folio.llegada_original,
            "oficina_id": self.oficina.pk, "oficina_nombre": self.oficina.nombre,
            "tramite_id": folio.tramite_id, "tramite_nombre": self.tramites[self.oficina.pk].nombre,
        })
        self.assertIsInstance(pendiente.folio_id, UUID)
        self.assertIsInstance(pendiente.llegada_original, datetime)
        self.assertTrue(timezone.is_aware(pendiente.llegada_original))

    def test_paginacion_50_con_desempates_en_el_limite(self):
        instante = timezone.now()
        folios = [self.registrar(self.oficina if n % 2 else self.segunda, instante) for n in range(103)]
        esperados = sorted(folio.pk for folio in folios)
        uno = self.leer()
        dos = self.leer(cursor=uno.cursor_siguiente)
        tres = self.leer(cursor=dos.cursor_siguiente)
        self.assertEqual([len(p.pendientes) for p in (uno, dos, tres)], [50, 50, 3])
        self.assertIsInstance(uno.cursor_siguiente, str)
        self.assertIsInstance(dos.cursor_siguiente, str)
        self.assertIsNone(tres.cursor_siguiente)
        self.assertEqual([f.folio_id for p in (uno, dos, tres) for f in p.pendientes], esperados)
        self.assertEqual(self.leer(cursor=uno.cursor_siguiente), dos)

    def test_exactamente_50_no_anuncia_otra_pagina(self):
        for _ in range(50):
            self.registrar()
        pagina = self.leer()
        self.assertEqual(len(pagina.pendientes), 50)
        self.assertIsNone(pagina.cursor_siguiente)

    def test_cursor_ordena_por_llegada_antes_del_uuid(self):
        instante = timezone.now()
        primeros = [self.registrar(llegada=instante) for _ in range(50)]
        with patch.object(Folio._meta.get_field("id"), "get_default", return_value=UUID(int=1)):
            posterior = self.registrar(self.segunda, instante + timedelta(microseconds=1))
        primera = self.leer()
        self.assertEqual([f.folio_id for f in primera.pendientes], sorted(f.pk for f in primeros))
        self.assertEqual(self.ids(cursor=primera.cursor_siguiente), [posterior.pk])

    def test_cursor_invalido_rechaza_formato_firma_y_contenido(self):
        # Solo se firman payloads inválidos para probar su validación interna;
        # no se altera ni se omite la comprobación de firma del servicio.
        def firmar(datos):
            return signing.dumps(datos, salt="folios.pendientes_operador.v1")
        valido = {"llegada_original": timezone.now().isoformat(), "folio_id": str(uuid4())}
        invalidos = (
            "", "no-es-un-cursor", 1, True, b"cursor", {}, "x" * 513,
            signing.dumps(valido, salt="otro-ambito"), firmar([]), firmar(None),
            firmar({}), firmar({**valido, "operador_id": self.operador.pk}),
            firmar({**valido, "llegada_original": "2026-10-14T12:00:00"}),
            firmar({**valido, "llegada_original": "fecha-invalida"}),
            firmar({**valido, "llegada_original": 123}),
            firmar({**valido, "folio_id": "no-uuid"}), firmar({**valido, "folio_id": None}),
        )
        for cursor in invalidos:
            with self.subTest(cursor=cursor):
                with self.assertNumQueries(0), self.assertRaises(ValidationError):
                    consultar_pendientes_operador(actor=self.operador, cursor=cursor)

    def test_cada_pagina_revalida_cuenta_y_rol(self):
        for _ in range(51):
            self.registrar()
        cursor = self.leer().cursor_siguiente
        self.operador.is_active = False
        self.operador.save(update_fields=["is_active"])
        with self.assertNumQueries(1), self.assertRaises(PermissionDenied):
            consultar_pendientes_operador(actor=self.operador, cursor=cursor)
        self.operador.is_active = True
        self.operador.save(update_fields=["is_active"])
        self.escribir_sql("usuarios_usuario", "rol", "RECEPCION", self.operador.pk)
        with self.assertNumQueries(1), self.assertRaises(PermissionDenied):
            consultar_pendientes_operador(actor=self.operador, cursor=cursor)

    def test_cada_pagina_revalida_asignaciones_y_cursor_no_concede_acceso(self):
        instante = timezone.now()
        for _ in range(50):
            self.registrar(self.oficina, instante)
        oculto = self.registrar(self.segunda, instante + timedelta(seconds=1))
        posterior = self.registrar(self.oficina, instante + timedelta(seconds=2))
        self.registrar(self.ajena, instante + timedelta(seconds=3))
        primera = self.leer()
        self.historica_inactiva(self.asignaciones[self.segunda.pk])
        self.assertEqual(self.ids(cursor=primera.cursor_siguiente), [posterior.pk])
        self.assertEqual(self.ids(actor=self.otro, cursor=primera.cursor_siguiente), [posterior.pk])
        self.historica_inactiva(self.asignaciones[self.oficina.pk])
        self.assertEqual(self.ids(cursor=primera.cursor_siguiente), [])
        reactivar_asignacion(actor=self.admin, operador_id=self.operador.pk, oficina_id=self.segunda.pk)
        self.assertEqual(self.ids(cursor=primera.cursor_siguiente), [oculto.pk])

    def test_llamado_entre_paginas_desaparece_y_no_invalida_cursor(self):
        instante = timezone.now()
        for _ in range(51):
            self.registrar(llegada=instante)
        primera = self.leer()
        llamado = self.llamar()
        self.assertEqual(llamado.folio_id, primera.pendientes[0].folio_id)
        segunda = self.leer(cursor=primera.cursor_siguiente)
        self.assertEqual(len(segunda.pendientes), 1)
        self.assertEqual(len(self.leer().pendientes), 50)
        self.assertIsNone(self.leer().cursor_siguiente)

    def test_actual_global_desde_llamado_y_exclusion_de_ajenos(self):
        propio = self.registrar(self.segunda)
        ajeno = self.registrar(self.oficina)
        self.assertEqual(self.llamar().folio_id, propio.pk)
        self.assertEqual(self.llamar(actor=self.otro).folio_id, ajeno.pk)
        actual = self.leer(consultar_folio_actual_operador)
        otro = self.leer(consultar_folio_actual_operador, actor=self.otro)
        self.assertIsInstance(actual, FolioActualPropio)
        self.assertEqual(set(asdict(actual)), CAMPOS_FOLIO | {"operador_responsable_id"})
        self.assertEqual((actual.folio_id, actual.estado, actual.operador_responsable_id),
                         (propio.pk, "LLAMADO", self.operador.pk))
        self.assertEqual(otro.folio_id, ajeno.pk)
        self.assertEqual(self.ids(), [])

    def test_reserva_ajena_no_es_actual_propio_ni_pendiente(self):
        folio = self.registrar()
        self.assertEqual(self.llamar(actor=self.otro).folio_id, folio.pk)
        self.assertEqual(self.ids(), [])
        self.assertIsNone(self.leer(consultar_folio_actual_operador))

    def test_actual_conservado_sin_asignaciones_y_catalogos_desactivados(self):
        folio = self.registrar()
        self.llamar()
        antes = self.leer(consultar_folio_actual_operador)
        for asignacion in self.asignaciones.values():
            self.historica_inactiva(asignacion)
        for catalogo in (self.oficina, self.tramites[self.oficina.pk]):
            catalogo.activo = False
            catalogo.save(update_fields=["activo"])
        self.assertEqual(self.leer(consultar_folio_actual_operador), antes)
        self.assertEqual(self.ids(), [])
        estado = consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk)
        self.assertEqual((estado.disponibilidad, estado.folio_actual.folio_id),
                         (Disponibilidad.OCUPADO, folio.pk))

    def test_lecturas_disponibles_durante_pausa_y_ocupacion(self):
        propio = self.registrar()
        pendiente = self.registrar(self.segunda)
        self.assertEqual(self.ids(), [propio.pk, pendiente.pk])
        pausa = self.pausar()
        self.assertEqual(self.ids(), [propio.pk, pendiente.pk])
        self.assertIsNone(self.leer(consultar_folio_actual_operador))
        self.reanudar(pausa.pausa_id)
        self.llamar()
        actual = self.leer(consultar_folio_actual_operador)
        self.assertEqual(self.ids(), [pendiente.pk])
        self.pausar()
        self.assertEqual(self.leer(consultar_folio_actual_operador), actual)
        self.assertEqual(self.ids(), [pendiente.pk])

    def test_disponibilidad_conserva_contrato_y_permisos_en_integracion(self):
        def comprobar(esperado, folio_id=None):
            with self.assertNumQueries(1):
                estado = consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk)
            actual = self.leer(consultar_folio_actual_operador)
            self.assertEqual(set(asdict(estado)), {
                "operador_id", "username", "disponibilidad", "pausa_abierta_id", "folio_actual",
            })
            self.assertEqual(estado.disponibilidad, esperado)
            self.assertEqual(actual.folio_id if actual else None, folio_id)
            self.assertEqual(estado.folio_actual.folio_id if estado.folio_actual else None, folio_id)
            recepcion = consultar_disponibilidad(actor=self.recepcion, operador_id=self.operador.pk)
            self.assertEqual(set(asdict(recepcion)), {"operador_id", "username", "disponibilidad"})
            self.assertEqual(recepcion.disponibilidad, esperado)

        comprobar(Disponibilidad.LIBRE)
        folio = self.registrar()
        self.llamar()
        comprobar(Disponibilidad.OCUPADO, folio.pk)
        pausa = self.pausar()
        comprobar(Disponibilidad.EN_PAUSA, folio.pk)
        self.reanudar(pausa.pausa_id)
        comprobar(Disponibilidad.OCUPADO, folio.pk)
        with self.assertRaises(PermissionDenied):
            consultar_disponibilidad(actor=self.operador, operador_id=self.otro.pk)
        with self.assertRaises(PermissionDenied):
            consultar_disponibilidad(actor=self.admin, operador_id=self.operador.pk)

    def test_materializacion_profunda_e_inmutabilidad(self):
        self.registrar()
        self.registrar(self.segunda)
        pagina = self.leer()
        self.llamar()
        actual = self.leer(consultar_folio_actual_operador)
        with self.assertNumQueries(0):
            self.assertIsInstance(pagina.pendientes, tuple)
            self.assertEqual(len(pagina.pendientes), 2)
            for folio in (*pagina.pendientes, actual):
                for valor in asdict(folio).values():
                    self.assertIsInstance(valor, (str, int, UUID, datetime))
                with self.assertRaises(FrozenInstanceError):
                    folio.nombre_completo = "Cambio"
            with self.assertRaises(FrozenInstanceError):
                pagina.cursor_siguiente = "Cambio"
        # La proyección materializada conserva su instantánea tras el llamado.
        self.assertTrue(all(f.estado == "EN_ESPERA" for f in pagina.pendientes))
        self.assertEqual(actual.estado, "LLAMADO")

    def test_lectores_no_escriben_ni_reservan_con_o_sin_pausa(self):
        self.registrar()
        self.registrar(self.segunda)
        for fase in ("libre", "ocupado", "pausa"):
            if fase == "ocupado":
                self.llamar()
            elif fase == "pausa":
                self.pausar()
            antes = self.estado_persistido()

            def solo_select(execute, sql, params, many, context):
                self.assertTrue(sql.lstrip().upper().startswith("SELECT"))
                self.assertNotIn("FOR UPDATE", sql.upper())
                return execute(sql, params, many, context)

            with connection.execute_wrapper(solo_select):
                pagina = self.leer()
                self.leer(consultar_folio_actual_operador)
                consultar_disponibilidad(actor=self.operador, operador_id=self.operador.pk)
                if pagina.cursor_siguiente:
                    self.leer(cursor=pagina.cursor_siguiente)
            self.assertEqual(self.estado_persistido(), antes)

    def test_alias_se_resuelve_una_vez_y_subconsultas_no_reenrutan(self):
        self.registrar()
        for lector in LECTORES:
            with patch("folios.services_operador.router.db_for_read", return_value="default") as ruta:
                self.leer(lector)
            ruta.assert_called_once_with(Folio)

    def test_argumentos_no_admiten_destinos_filtros_o_seleccion_manual(self):
        for lector in LECTORES:
            for campo in ("oficina_id", "folio_id", "operador_id", "estado", "fecha", "using", "limite"):
                with self.subTest(lector=lector.__name__, campo=campo):
                    with self.assertNumQueries(0), self.assertRaises(TypeError):
                        lector(actor=self.operador, **{campo: 1})

    def test_lectura_no_cambia_seleccion_del_llamado_ni_habilita_en_atencion(self):
        folio = self.registrar()
        self.assertEqual(self.ids(), [folio.pk])
        llamado = self.llamar()
        self.assertEqual((llamado.resultado, llamado.folio_id), (EstadoLlamado.LLAMADO, folio.pk))
        self.assertEqual(self.leer(consultar_folio_actual_operador).estado, "LLAMADO")
        self.assertEqual(self.llamar().resultado, EstadoLlamado.OCUPADO)
        self.assertNotIn("EN_ATENCION", Folio.Estado.values)
