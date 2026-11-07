from builtins import Exception
import logging
import re
from abc import ABC, abstractmethod

# ==========================================================
# 1. CONFIGURACIÓN DEL ARCHIVO DE LOGS
# ==========================================================
logging.basicConfig(
    filename="sistema_software_fj.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)

def formatear_cop(valor: float) -> str:
    """Da formato de pesos colombianos (COP): 50000 -> $50.000 COP."""
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if texto.endswith(",00"):
        texto = texto[:-3]
    return f"${texto} COP"

# ==========================================================
# 2. EXCEPCIONES PERSONALIZADAS
# ==========================================================
class SoftwareFJError(Exception):
    """Excepcion base de todos los errores controlados de Software FJ."""


class ClienteInvalidoError(SoftwareFJError):
    """Datos del cliente inválidos (nombre, correo, teléfono, id)."""


class ServicioInvalidoError(SoftwareFJError):
    """Errores en la definicion, parámetros o cálculo de un servicio."""


class ServicioNoDisponibleError(SoftwareFJError):
    """El servicio solicitado no se encuentra disponible."""


class ReservaError(SoftwareFJError):
    """Fallo en el proceso de reserva u operación no permitida sobre ella."""


class RegistroError(SoftwareFJError):
    """Errores del gestor: duplicados o entidades inexistentes."""


# ==========================================================
# 3. CLASE ABSTRACTA GENERAL Y CLASE CLIENTE
# ==========================================================
class EntidadBase(ABC):
    """Clase abstracta que representa las entidades generales del sistema."""

    def __init__(self, identificador: str):
        if not isinstance(identificador, str) or not identificador.strip():
            msg = f"Identificador inválido: '{identificador}'."
            logging.error(msg)
            raise SoftwareFJError(msg)
        self._identificador = identificador.strip()

    @property
    def identificador(self) -> str:
        return self._identificador

    @abstractmethod
    def obtener_detalles(self) -> str:
        """Devuelve una descripción de la entidad."""


class Cliente(EntidadBase):
    """Cliente con datos personales encapsulados y validaciones estrictas."""

    _PATRON_CORREO = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")

    def __init__(self, identificador: str, nombre: str, correo: str, telefono: str):
        super().__init__(identificador)
        self.nombre = nombre
        self.correo = correo
        self.telefono = telefono

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor):
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            msg = f"Nombre de cliente inválido: '{valor}'."
            logging.error(msg)
            raise ClienteInvalidoError(msg)
        self._nombre = valor.strip()

    @property
    def correo(self) -> str:
        return self._correo

    @correo.setter
    def correo(self, valor):
        if not isinstance(valor, str) or not self._PATRON_CORREO.match(valor.strip()):
            msg = f"Correo electrónico inválido: '{valor}'."
            logging.error(msg)
            raise ClienteInvalidoError(msg)
        self._correo = valor.strip()

    @property
    def telefono(self) -> str:
        return self._telefono

    @telefono.setter
    def telefono(self, valor):
        texto = str(valor).strip() if valor is not None else ""
        if not texto.isdigit() or len(texto) < 7:
            msg = f"Número telefónico inválido: '{valor}'."
            logging.error(msg)
            raise ClienteInvalidoError(msg)
        self._telefono = texto

    def obtener_detalles(self) -> str:
        return (f"Cliente [ID: {self.identificador}, Nombre: {self.nombre}, "
                f"Correo: {self.correo}, Teléfono: {self.telefono}]")


# ==========================================================
# 4. CLASE ABSTRACTA SERVICIO Y SERVICIOS ESPECIALIZADOS
# ==========================================================
class Servicio(EntidadBase):
    """
    Clase abstracta Servicio. Obliga a las clases hijas a sobrescribir:
    calcular_costo, obtener_detalles (describir) y validar_parametros.
    """

    IVA = 0.19

    def __init__(self, identificador: str, nombre_servicio: str, tarifa_base: float,
                 disponible: bool = True):
        super().__init__(identificador)
        self.nombre_servicio = nombre_servicio
        self.tarifa_base = tarifa_base
        self.disponible = disponible

    @property
    def tarifa_base(self) -> float:
        return self._tarifa_base

    @tarifa_base.setter
    def tarifa_base(self, valor):
        try:
            valor = float(valor)
        except (TypeError, ValueError) as e:
            msg = f"La tarifa base debe ser numérica: '{valor}'"
            logging.error(msg)
            raise ServicioInvalidoError(msg) from e
        if valor < 0:
            msg = f"La tarifa base no puede ser negativa: {valor}"
            logging.error(msg)
            raise ServicioInvalidoError(msg)
        self._tarifa_base = valor

    # ---- utilidades comunes (reutilizadas por las clases hijas) ----
    def _validar_comunes(self, cantidad, descuento):
        """Valida cantidad (>0) y descuento (0 a 1). Encadena errores de tipo."""
        try:
            cantidad_num = int(cantidad)
            descuento_num = float(descuento)
        except (TypeError, ValueError) as e:
            raise ServicioInvalidoError(
                f"Parámetros faltantes o de tipo incorrecto "
                f"(cantidad={cantidad}, descuento={descuento}).") from e
        if cantidad_num <= 0:
            raise ServicioInvalidoError(
                f"La cantidad de tiempo debe ser mayor a cero: {cantidad}.")
        if not 0 <= descuento_num < 1:
            raise ServicioInvalidoError(
                f"El descuento debe estar entre 0 y 1: {descuento}.")

    @staticmethod
    def _validar_extras(extras: dict, permitidos: tuple):
        desconocidos = set(extras) - set(permitidos)
        if desconocidos:
            raise ServicioInvalidoError(
                f"Parámetros no permitidos para este servicio: {sorted(desconocidos)}.")

    def _aplicar_ajustes(self, subtotal: float, descuento: float,
                         incluir_impuesto: bool) -> float:
        total = subtotal * (1 - descuento)
        if incluir_impuesto:
            total *= 1 + self.IVA
        total = round(total, 2)
        if total < 0:
            raise ServicioInvalidoError(f"Cálculo inconsistente: total negativo ({total}).")
        return total

    # ---- métodos abstractos (polimorfismo) ----
    @abstractmethod
    def validar_parametros(self, cantidad, descuento=0.0, incluir_impuesto=False, **extras):
        """Valida los parámetros de cálculo; lanza ServicioInvalidoError."""

    @abstractmethod
    def calcular_costo(self, cantidad, descuento=0.0, incluir_impuesto=False, **extras) -> float:
        """Calcula el costo del servicio (comportamiento polimórfico)."""

    # ---- variantes del cálculo (equivalente a sobrecarga en Python) ----
    def calcular_costo_con_impuesto(self, cantidad, **extras) -> float:
        """Variante: costo con IVA, sin descuento."""
        return self.calcular_costo(cantidad, 0.0, True, **extras)

    def calcular_costo_con_descuento(self, cantidad, descuento, **extras) -> float:
        """Variante: costo con descuento, sin IVA."""
        return self.calcular_costo(cantidad, descuento, False, **extras)


class ReservaSalas(Servicio):
    """Servicio de reserva de salas (la cantidad se mide en horas)."""

    def __init__(self, identificador: str, tarifa_base: float, capacidad: int,
                 disponible: bool = True):
        super().__init__(identificador, "Reserva de Salas", tarifa_base, disponible)
        self.capacidad = capacidad

    @property
    def capacidad(self) -> int:
        return self._capacidad

    @capacidad.setter
    def capacidad(self, valor):
        try:
            valor = int(valor)
        except (TypeError, ValueError) as e:
            msg = f"La capacidad debe ser un entero: '{valor}'"
            logging.error(msg)
            raise ServicioInvalidoError(msg) from e
        if valor <= 0:
            msg = f"La capacidad de la sala debe ser mayor a 0: {valor}"
            logging.error(msg)
            raise ServicioInvalidoError(msg)
        self._capacidad = valor

    def validar_parametros(self, cantidad, descuento=0.0, incluir_impuesto=False, **extras):
        self._validar_comunes(cantidad, descuento)
        self._validar_extras(extras, ())

    def calcular_costo(self, cantidad, descuento=0.0, incluir_impuesto=False, **extras) -> float:
        self.validar_parametros(cantidad, descuento, incluir_impuesto, **extras)
        return self._aplicar_ajustes(self.tarifa_base * int(cantidad),
                                     float(descuento), incluir_impuesto)

    def obtener_detalles(self) -> str:
        return (f"Servicio: Reserva de Salas [ID: {self.identificador}, "
                f"Capacidad: {self.capacidad} pers., Tarifa/hora: ${self.tarifa_base}]")


class AlquilerEquipos(Servicio):
    """Servicio de alquiler de equipos (la cantidad se mide en días)."""

    SEGURO_DIARIO = 15.0

    def __init__(self, identificador: str, tarifa_base: float, tipo_equipo: str,
                 disponible: bool = True):
        super().__init__(identificador, "Alquiler de Equipos", tarifa_base, disponible)
        if not isinstance(tipo_equipo, str) or not tipo_equipo.strip():
            msg = f"Tipo de equipo inválido: '{tipo_equipo}'"
            logging.error(msg)
            raise ServicioInvalidoError(msg)
        self.tipo_equipo = tipo_equipo.strip()

    def validar_parametros(self, cantidad, descuento=0.0, incluir_impuesto=False, **extras):
        self._validar_comunes(cantidad, descuento)
        self._validar_extras(extras, ("seguro_adicional",))
        if not isinstance(extras.get("seguro_adicional", False), bool):
            raise ServicioInvalidoError("'seguro_adicional' debe ser True o False.")

    def calcular_costo(self, cantidad, descuento=0.0, incluir_impuesto=False, **extras) -> float:
        self.validar_parametros(cantidad, descuento, incluir_impuesto, **extras)
        dias = int(cantidad)
        subtotal = self.tarifa_base * dias
        if extras.get("seguro_adicional", False):
            subtotal += self.SEGURO_DIARIO * dias
        return self._aplicar_ajustes(subtotal, float(descuento), incluir_impuesto)

    def obtener_detalles(self) -> str:
        return (f"Servicio: Alquiler de Equipos [ID: {self.identificador}, "
                f"Equipo: {self.tipo_equipo}, Tarifa/día: ${self.tarifa_base}]")


class AsesoriaEspecializada(Servicio):
    """Servicio de asesoría técnica (la cantidad se mide en sesiones)."""

    RECARGO_COMPLEJIDAD = 1.35

    def __init__(self, identificador: str, tarifa_base: float, area_experticia: str,
                 disponible: bool = True):
        super().__init__(identificador, "Asesoría Especializada", tarifa_base, disponible)
        if not isinstance(area_experticia, str) or not area_experticia.strip():
            msg = f"Área de experticia inválida: '{area_experticia}'"
            logging.error(msg)
            raise ServicioInvalidoError(msg)
        self.area_experticia = area_experticia.strip()

    def validar_parametros(self, cantidad, descuento=0.0, incluir_impuesto=False, **extras):
        self._validar_comunes(cantidad, descuento)
        self._validar_extras(extras, ("complejidad_alta",))
        if not isinstance(extras.get("complejidad_alta", False), bool):
            raise ServicioInvalidoError("'complejidad_alta' debe ser True o False.")

    def calcular_costo(self, cantidad, descuento=0.0, incluir_impuesto=False, **extras) -> float:
        self.validar_parametros(cantidad, descuento, incluir_impuesto, **extras)
        mult = self.RECARGO_COMPLEJIDAD if extras.get("complejidad_alta", False) else 1.0
        subtotal = self.tarifa_base * int(cantidad) * mult
        return self._aplicar_ajustes(subtotal, float(descuento), incluir_impuesto)

    def obtener_detalles(self) -> str:
        return (f"Servicio: Asesoría Especializada [ID: {self.identificador}, "
                f"Área: {self.area_experticia}, Tarifa/sesión: ${self.tarifa_base}]")


# ==========================================================
# 5. CLASE RESERVA
# ==========================================================
class Reserva(EntidadBase):
    """
    Integra cliente, servicio, duración y estado.
    Estados: Creada -> Procesada -> Confirmada | Cancelada | Fallida
    """

    def __init__(self, id_reserva: str, cliente: Cliente, servicio: Servicio,
                 cantidad_tiempo):
        super().__init__(id_reserva)
        if not isinstance(cliente, Cliente):
            raise ReservaError("La reserva requiere un cliente válido.")
        if not isinstance(servicio, Servicio):
            raise ReservaError("La reserva requiere un servicio válido.")
        if cantidad_tiempo is None:
            raise ReservaError("Falta la duración de la reserva.")
        self.cliente = cliente
        self.servicio = servicio
        self.cantidad_tiempo = cantidad_tiempo
        self.estado = "Creada"
        self.costo_total = 0.0
        logging.info(f"Reserva {self.identificador} creada para {cliente.nombre}.")

    @property
    def id_reserva(self) -> str:
        return self.identificador

    def procesar_reserva(self, **opciones):
        """
        Calcula el costo. Usa try/except/else/finally y encadenamiento.
        opciones: descuento, incluir_impuesto, seguro_adicional, complejidad_alta...
        """
        if self.estado in ("Cancelada", "Confirmada"):
            raise ReservaError(
                f"Operación no permitida: la reserva {self.id_reserva} está {self.estado}.")
        logging.info(f"Iniciando procesamiento de la reserva {self.id_reserva}.")
        try:
            if not self.servicio.disponible:
                raise ServicioNoDisponibleError(
                    f"El servicio {self.servicio.identificador} no está disponible.")
            costo = self.servicio.calcular_costo(self.cantidad_tiempo, **opciones)
        except Exception as e:
            self.estado = "Fallida"
            msg = f"Fallo al procesar la reserva {self.id_reserva}."
            logging.error(f"{msg} Detalle: {e}")
            raise ReservaError(msg) from e          # encadenamiento
        else:
            self.costo_total = costo
            self.estado = "Procesada"
            logging.info(f"Reserva {self.id_reserva} procesada. Costo: ${costo}")
        finally:
            logging.info(f"Fin del procesamiento de {self.id_reserva}. "
                         f"Estado actual: {self.estado}")

    def confirmar_reserva(self):
        """Confirma una reserva ya procesada."""
        if self.estado != "Procesada":
            msg = (f"Operación no permitida: no se puede confirmar la reserva "
                   f"{self.id_reserva} en estado '{self.estado}'.")
            logging.error(msg)
            raise ReservaError(msg)
        self.estado = "Confirmada"
        logging.info(f"Reserva {self.id_reserva} confirmada.")

    def cancelar_reserva(self):
        """Cancela la reserva si aún no está cancelada ni fallida."""
        if self.estado in ("Cancelada", "Fallida"):
            msg = (f"Operación no permitida: la reserva {self.id_reserva} "
                   f"ya está '{self.estado}'.")
            logging.error(msg)
            raise ReservaError(msg)
        self.estado = "Cancelada"
        logging.info(f"Reserva {self.id_reserva} cancelada.")

    def obtener_detalles(self) -> str:
        return (f"Reserva ID: {self.id_reserva} | Estado: {self.estado} | "
                f"Cliente: {self.cliente.nombre} | Servicio: {self.servicio.nombre_servicio} | "
                f"Duración: {self.cantidad_tiempo} | Costo Total: ${self.costo_total}")

    obtener_resumen = obtener_detalles


# ==========================================================
# 6. GESTOR CON LISTAS INTERNAS (SIN BASE DE DATOS)
# ==========================================================
class GestorSoftwareFJ:
    """Administra clientes, servicios y reservas mediante listas internas."""

    def __init__(self):
        self._clientes: list[Cliente] = []
        self._servicios: list[Servicio] = []
        self._reservas: list[Reserva] = []

    @staticmethod
    def _buscar(lista, identificador, nombre_entidad):
        for item in lista:
            if item.identificador == identificador:
                return item
        raise RegistroError(f"{nombre_entidad} '{identificador}' no existe.")

    def _existe(self, lista, identificador) -> bool:
        return any(i.identificador == identificador for i in lista)

    def registrar_cliente(self, identificador, nombre, correo, telefono) -> Cliente:
        if self._existe(self._clientes, identificador):
            raise RegistroError(f"Ya existe un cliente con ID '{identificador}'.")
        try:
            cliente = Cliente(identificador, nombre, correo, telefono)
        except SoftwareFJError as e:
            raise RegistroError(f"No se pudo registrar al cliente '{identificador}'.") from e
        else:
            self._clientes.append(cliente)
            logging.info(f"Cliente registrado: {cliente.identificador}")
            return cliente
        finally:
            logging.info(f"Intento de registro de cliente '{identificador}' finalizado.")

    def registrar_servicio(self, servicio: Servicio) -> Servicio:
        if self._existe(self._servicios, servicio.identificador):
            raise RegistroError(f"Ya existe un servicio con ID '{servicio.identificador}'.")
        self._servicios.append(servicio)
        logging.info(f"Servicio registrado: {servicio.identificador}")
        return servicio

    def crear_reserva(self, id_reserva, id_cliente, id_servicio, cantidad_tiempo) -> Reserva:
        if self._existe(self._reservas, id_reserva):
            raise RegistroError(f"Ya existe una reserva con ID '{id_reserva}'.")
        cliente = self._buscar(self._clientes, id_cliente, "Cliente")
        servicio = self._buscar(self._servicios, id_servicio, "Servicio")
        reserva = Reserva(id_reserva, cliente, servicio, cantidad_tiempo)
        self._reservas.append(reserva)          # se guarda aunque luego falle
        return reserva

    def obtener_reserva(self, id_reserva) -> Reserva:
        return self._buscar(self._reservas, id_reserva, "Reserva")

    @property
    def reservas(self):
        return list(self._reservas)

    @property
    def clientes(self):
        return list(self._clientes)

    @property
    def servicios(self):
        return list(self._servicios)


# ==========================================================
# 7. SIMULACIÓN DE OPERACIONES (VÁLIDAS E INVÁLIDAS)
# ==========================================================
def ejecutar_operacion(numero: int, descripcion: str, accion):
    """Ejecuta una operación; ningún error detiene el programa."""
    print(f"[Op {numero:02d}] {descripcion}")
    logging.info(f"--- Operación {numero}: {descripcion} ---")
    try:
        resultado = accion()
    except SoftwareFJError as e:
        causa = f" | Causa: {e.__cause__}" if e.__cause__ else ""
        print(f"   ✗ Error controlado: {e}{causa}\n")
        logging.error(f"Operación {numero} falló de forma controlada: {e}{causa}")
    except Exception as e:  # error inesperado: se registra y se continúa
        print(f"   ✗ Error inesperado: {type(e).__name__}: {e}\n")
        logging.critical(f"Operación {numero} - error inesperado: {type(e).__name__}: {e}")
    else:
        print(f"   ✓ {resultado}\n")
        logging.info(f"Operación {numero} completada con éxito.")


def main():
    print("=" * 62)
    print(" INICIO DE SIMULACIÓN - SOFTWARE FJ (SIN BASE DE DATOS)")
    print("=" * 62 + "\n")
    logging.info("========== INICIO DE LA SIMULACIÓN ==========")

    g = GestorSoftwareFJ()

    def op_reserva(id_r, id_c, id_s, cant, **opciones):
        def _accion():
            r = g.crear_reserva(id_r, id_c, id_s, cant)
            r.procesar_reserva(**opciones)
            r.confirmar_reserva()
            return r.obtener_resumen()
        return _accion

    # --- Clientes ---
    ejecutar_operacion(1, "Registro VÁLIDO de cliente",
        lambda: g.registrar_cliente("C001", "Carlos Sierra",
                                    "casierracard@unadvirtual.edu.co", "3202210214").obtener_detalles())
    ejecutar_operacion(2, "Registro INVÁLIDO de cliente (correo sin arroba)",
        lambda: g.registrar_cliente("C002", "Ana Gómez", "correo-sin-arroba.com", "3209876543"))
    ejecutar_operacion(3, "Registro INVÁLIDO de cliente (nombre faltante y teléfono corto)",
        lambda: g.registrar_cliente("C003", None, "x@y.com", "123"))

    # --- Servicios ---
    ejecutar_operacion(4, "Creación VÁLIDA de servicio: Reserva de Salas",
        lambda: g.registrar_servicio(ReservaSalas("S001", 50.0, 20)).obtener_detalles())
    ejecutar_operacion(5, "Creación INVÁLIDA de servicio (capacidad negativa)",
        lambda: g.registrar_servicio(ReservaSalas("S002", 40.0, -5)))
    ejecutar_operacion(6, "Creación VÁLIDA de Alquiler de Equipos y Asesoría (S004 no disponible)",
        lambda: [g.registrar_servicio(AlquilerEquipos("S003", 30.0, "Laptop Core i7")).obtener_detalles(),
                 g.registrar_servicio(AsesoriaEspecializada("S004", 80.0, "Arquitectura de Software")).obtener_detalles(),
                 g.registrar_servicio(AsesoriaEspecializada("S005", 90.0, "Ciberseguridad", disponible=False)).obtener_detalles()])
    ejecutar_operacion(7, "Creación INVÁLIDA de servicio (tarifa negativa)",
        lambda: g.registrar_servicio(AlquilerEquipos("S006", -10.0, "Proyector")))

    # --- Reservas exitosas (polimorfismo: mismo método, distinto cálculo) ---
    ejecutar_operacion(8, "Reserva EXITOSA de sala (4 h, 10% desc., con IVA)",
        op_reserva("R001", "C001", "S001", 4, descuento=0.10, incluir_impuesto=True))
    ejecutar_operacion(9, "Reserva EXITOSA de equipo (5 días, con seguro)",
        op_reserva("R002", "C001", "S003", 5, seguro_adicional=True))
    ejecutar_operacion(10, "Reserva EXITOSA de asesoría (3 sesiones, alta complejidad)",
        op_reserva("R003", "C001", "S004", 3, complejidad_alta=True))

    # --- Reservas fallidas ---
    ejecutar_operacion(11, "Reserva FALLIDA (tiempo negativo)",
        op_reserva("R004", "C001", "S001", -2))
    ejecutar_operacion(12, "Reserva FALLIDA (servicio no disponible)",
        op_reserva("R005", "C001", "S005", 2))
    ejecutar_operacion(13, "Reserva FALLIDA (parámetro no permitido para el servicio)",
        op_reserva("R006", "C001", "S001", 2, seguro_adicional=True))
    ejecutar_operacion(14, "Reserva FALLIDA (cliente inexistente)",
        op_reserva("R007", "C999", "S001", 2))
    ejecutar_operacion(15, "Reserva FALLIDA (duración faltante)",
        op_reserva("R008", "C001", "S001", None))

    # --- Cancelaciones ---
    ejecutar_operacion(16, "Cancelación de la reserva R002",
        lambda: (g.obtener_reserva("R002").cancelar_reserva(),
                 g.obtener_reserva("R002").obtener_resumen())[1])
    ejecutar_operacion(17, "Cancelar de nuevo R002 (operación no permitida)",
        lambda: g.obtener_reserva("R002").cancelar_reserva())

    # --- Variantes del cálculo de costos (equivalente a sobrecarga) ---
    ejecutar_operacion(18, "Variantes de cálculo de costos sobre la sala S001 (3 h)",
        lambda: (f"normal=${g.servicios[0].calcular_costo(3)} | "
                 f"con IVA=${g.servicios[0].calcular_costo_con_impuesto(3)} | "
                 f"con 20% desc.=${g.servicios[0].calcular_costo_con_descuento(3, 0.20)}"))

    # --- Resumen final ---
    print("-" * 62)
    print(" RESUMEN DE RESERVAS EN MEMORIA")
    print("-" * 62)
    for r in g.reservas:
        print(" ", r.obtener_resumen())

    logging.info("========== FIN DE LA SIMULACIÓN ==========\n")
    print("\n" + "=" * 62)
    print(" SIMULACIÓN FINALIZADA: el sistema se mantuvo operativo.")
    print(" Revise el archivo 'sistema_software_fj.log'.")
    print("=" * 62)


if __name__ == "__main__":
    main()
