from django.db import models
from django.core.validators import MinValueValidator


class TipoTecnico(models.TextChoices):
    INTERNO = 'INTERNO', 'Técnico interno'
    EXTERNO = 'EXTERNO', 'Proveedor externo'


class Tecnico(models.Model):
    """Técnico propio o proveedor externo que realiza mantenimientos."""
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=10, choices=TipoTecnico.choices, default=TipoTecnico.INTERNO)
    empresa = models.CharField(max_length=200, blank=True, help_text='Solo para técnicos externos')
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    especialidad = models.CharField(max_length=200, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Técnico'
        verbose_name_plural = 'Técnicos'

    def __str__(self):
        if self.tipo == TipoTecnico.EXTERNO and self.empresa:
            return f'{self.nombre} ({self.empresa})'
        return self.nombre


# ─────────────────────────────────────────────────────────────────────────────
# ÓRDENES DE TRABAJO
# ─────────────────────────────────────────────────────────────────────────────

class TipoOrden(models.TextChoices):
    PREVENTIVO = 'PREVENTIVO', 'Mantenimiento preventivo'
    CORRECTIVO = 'CORRECTIVO', 'Mantenimiento correctivo'
    INSTALACION = 'INSTALACION', 'Instalación'
    RETIRO = 'RETIRO', 'Retiro de equipo'
    REVISION = 'REVISION', 'Revisión general'


class EstadoOrden(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    EN_PROCESO = 'EN_PROCESO', 'En proceso'
    COMPLETADA = 'COMPLETADA', 'Completada'
    CANCELADA = 'CANCELADA', 'Cancelada'
    REPROGRAMADA = 'REPROGRAMADA', 'Reprogramada'


class PrioridadOrden(models.TextChoices):
    BAJA = 'BAJA', 'Baja'
    MEDIA = 'MEDIA', 'Media'
    ALTA = 'ALTA', 'Alta'
    URGENTE = 'URGENTE', 'Urgente'


class OrdenTrabajo(models.Model):
    """
    Orden de trabajo para cualquier intervención en un equipo.
    Referencia al equipo y cliente en ms-equipos / ms-clientes.
    """
    numero_orden = models.CharField(max_length=50, unique=True)
    tipo = models.CharField(max_length=15, choices=TipoOrden.choices)
    estado = models.CharField(max_length=15, choices=EstadoOrden.choices, default=EstadoOrden.PENDIENTE)
    prioridad = models.CharField(max_length=10, choices=PrioridadOrden.choices, default=PrioridadOrden.MEDIA)

    # Referencias a otros microservicios (sin FK real)
    equipo_id = models.PositiveIntegerField(help_text='ID del equipo en ms-equipos')
    equipo_nombre = models.CharField(max_length=200)
    equipo_serial = models.CharField(max_length=100)
    cliente_id = models.PositiveIntegerField(null=True, blank=True)
    cliente_nombre = models.CharField(max_length=200, blank=True)
    ubicacion = models.CharField(max_length=200, blank=True)

    # Técnico asignado
    tecnico = models.ForeignKey(
        Tecnico, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ordenes'
    )

    # Descripción del problema o trabajo a realizar
    descripcion = models.TextField(help_text='Descripción del problema o trabajo a realizar')
    diagnostico = models.TextField(blank=True, help_text='Diagnóstico del técnico')
    solucion_aplicada = models.TextField(blank=True)

    # Fechas
    fecha_programada = models.DateField(help_text='Fecha en que se planea realizar el trabajo')
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    # Contador al momento del mantenimiento (para historial)
    contador_al_servicio = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Valor del contador de ciclos cuando se realizó el servicio'
    )

    # Costo del servicio (para técnicos externos)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    notas_internas = models.TextField(blank=True)
    creado_por = models.CharField(max_length=150, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_programada', '-creado_en']
        verbose_name = 'Orden de trabajo'
        verbose_name_plural = 'Órdenes de trabajo'

    def __str__(self):
        return f'{self.numero_orden} — {self.equipo_nombre} ({self.get_tipo_display()})'

    @property
    def duracion_minutos(self):
        if self.fecha_inicio and self.fecha_fin:
            delta = self.fecha_fin - self.fecha_inicio
            return int(delta.total_seconds() / 60)
        return None

    def save(self, *args, **kwargs):
        # Generar número de orden automático si no tiene
        if not self.numero_orden:
            from django.utils import timezone
            año = timezone.now().year
            ultimo = OrdenTrabajo.objects.filter(
                numero_orden__startswith=f'OT-{año}-'
            ).count()
            self.numero_orden = f'OT-{año}-{str(ultimo + 1).zfill(4)}'
        super().save(*args, **kwargs)


class PiezaReemplazada(models.Model):
    """
    Pieza o componente reemplazado durante una orden de trabajo.
    No maneja stock, solo registra qué se cambió.
    """
    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name='piezas')
    nombre_pieza = models.CharField(max_length=200, help_text='Ej: Fusor, Rodillo de transferencia, Banda OPC')
    numero_parte = models.CharField(max_length=100, blank=True, help_text='Código o número de parte del fabricante')
    marca_pieza = models.CharField(max_length=100, blank=True, help_text='Original, Compatible, Remanufacturada')
    cantidad = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    costo_unitario = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    notas = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = 'Pieza reemplazada'
        verbose_name_plural = 'Piezas reemplazadas'

    def __str__(self):
        return f'{self.nombre_pieza} x{self.cantidad} — {self.orden.numero_orden}'

    @property
    def costo_total(self):
        return self.cantidad * self.costo_unitario


# ─────────────────────────────────────────────────────────────────────────────
# MANTENIMIENTOS PROGRAMADOS
# ─────────────────────────────────────────────────────────────────────────────

class EstadoProgramado(models.TextChoices):
    ACTIVO = 'ACTIVO', 'Activo'
    PAUSADO = 'PAUSADO', 'Pausado'
    COMPLETADO = 'COMPLETADO', 'Completado'
    CANCELADO = 'CANCELADO', 'Cancelado'


class MantenimientoProgramado(models.Model):
    """
    Define la cadencia de mantenimientos preventivos para un equipo.
    Genera órdenes de trabajo automáticamente según la frecuencia.
    """
    equipo_id = models.PositiveIntegerField()
    equipo_nombre = models.CharField(max_length=200)
    equipo_serial = models.CharField(max_length=100)
    cliente_id = models.PositiveIntegerField(null=True, blank=True)
    cliente_nombre = models.CharField(max_length=200, blank=True)

    nombre = models.CharField(max_length=200, help_text='Ej: Mantenimiento preventivo mensual')
    descripcion = models.TextField(blank=True)

    # Frecuencia por fecha
    frecuencia_meses = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Cada cuántos meses se realiza este mantenimiento'
    )

    # Técnico preferido para este mantenimiento
    tecnico = models.ForeignKey(
        Tecnico, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='mantenimientos_programados'
    )

    estado = models.CharField(max_length=12, choices=EstadoProgramado.choices, default=EstadoProgramado.ACTIVO)

    # Fechas de control
    fecha_inicio_programa = models.DateField(help_text='Desde cuándo aplica este programa')
    fecha_ultimo_mantenimiento = models.DateField(null=True, blank=True)
    fecha_proximo_mantenimiento = models.DateField(null=True, blank=True)

    # Días de anticipación para crear la orden automáticamente
    dias_anticipacion = models.PositiveSmallIntegerField(
        default=7,
        help_text='Días antes de la fecha programada para crear la orden de trabajo'
    )

    notas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['fecha_proximo_mantenimiento']
        verbose_name = 'Mantenimiento programado'
        verbose_name_plural = 'Mantenimientos programados'

    def __str__(self):
        return f'{self.nombre} — {self.equipo_nombre}'

    def calcular_proximo(self):
        """Calcula la próxima fecha basándose en el último mantenimiento."""
        from dateutil.relativedelta import relativedelta
        base = self.fecha_ultimo_mantenimiento or self.fecha_inicio_programa
        return base + relativedelta(months=self.frecuencia_meses)

    @property
    def dias_para_proximo(self):
        from django.utils import timezone
        if not self.fecha_proximo_mantenimiento:
            return None
        hoy = timezone.now().date()
        return (self.fecha_proximo_mantenimiento - hoy).days

    @property
    def requiere_atencion(self):
        dias = self.dias_para_proximo
        return dias is not None and dias <= self.dias_anticipacion
