from datetime import date
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema

from .models import (
    Tecnico, OrdenTrabajo, PiezaReemplazada,
    MantenimientoProgramado, EstadoOrden, EstadoProgramado
)
from .serializers import (
    TecnicoSerializer,
    OrdenTrabajoListSerializer,
    OrdenTrabajoWriteSerializer,
    PiezaReemplazadaSerializer,
    MantenimientoProgramadoSerializer,
    ResumenMantenimientoSerializer,
)


class TecnicoViewSet(viewsets.ModelViewSet):
    queryset = Tecnico.objects.all()
    serializer_class = TecnicoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['tipo', 'activo']
    search_fields = ['nombre', 'empresa', 'especialidad']
    permission_classes = [AllowAny]


@extend_schema_view(
    list=extend_schema(summary='Listar órdenes de trabajo'),
    retrieve=extend_schema(summary='Detalle de orden'),
    create=extend_schema(summary='Crear orden de trabajo'),
    update=extend_schema(summary='Actualizar orden'),
    partial_update=extend_schema(summary='Actualizar parcialmente'),
    destroy=extend_schema(summary='Eliminar orden'),
)
class OrdenTrabajoViewSet(viewsets.ModelViewSet):
    queryset = OrdenTrabajo.objects.select_related('tecnico').prefetch_related('piezas').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tipo', 'estado', 'prioridad', 'equipo_id', 'cliente_id', 'tecnico']
    search_fields = ['numero_orden', 'equipo_nombre', 'equipo_serial', 'cliente_nombre', 'descripcion']
    ordering_fields = ['fecha_programada', 'creado_en', 'prioridad']
    ordering = ['-fecha_programada']
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return OrdenTrabajoWriteSerializer
        return OrdenTrabajoListSerializer

    @extend_schema(summary='Resumen para dashboard')
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)

        programados = MantenimientoProgramado.objects.filter(estado=EstadoProgramado.ACTIVO)
        proximos = [p for p in programados if p.requiere_atencion and (p.dias_para_proximo or 0) >= 0]
        vencidos = [p for p in programados if (p.dias_para_proximo or 1) < 0]

        data = {
            'ordenes_pendientes': OrdenTrabajo.objects.filter(estado=EstadoOrden.PENDIENTE).count(),
            'ordenes_en_proceso': OrdenTrabajo.objects.filter(estado=EstadoOrden.EN_PROCESO).count(),
            'ordenes_completadas_mes': OrdenTrabajo.objects.filter(
                estado=EstadoOrden.COMPLETADA,
                fecha_fin__date__gte=inicio_mes
            ).count(),
            'programados_proximos': len(proximos),
            'programados_vencidos': len(vencidos),
            'tecnicos_activos': Tecnico.objects.filter(activo=True).count(),
        }
        return Response(ResumenMantenimientoSerializer(data).data)

    @extend_schema(
        summary='Iniciar orden (cambia estado a EN_PROCESO)',
        responses={200: OrdenTrabajoListSerializer},
    )
    @action(detail=True, methods=['post'], url_path='iniciar')
    def iniciar(self, request, pk=None):
        orden = self.get_object()
        if orden.estado != EstadoOrden.PENDIENTE:
            return Response(
                {'detail': 'Solo se pueden iniciar órdenes en estado PENDIENTE.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        orden.estado = EstadoOrden.EN_PROCESO
        orden.fecha_inicio = timezone.now()
        orden.save(update_fields=['estado', 'fecha_inicio', 'actualizado_en'])
        return Response(OrdenTrabajoListSerializer(orden).data)

    @extend_schema(
        summary='Completar orden',
        responses={200: OrdenTrabajoListSerializer},
    )
    @action(detail=True, methods=['post'], url_path='completar')
    def completar(self, request, pk=None):
        orden = self.get_object()
        if orden.estado not in (EstadoOrden.PENDIENTE, EstadoOrden.EN_PROCESO):
            return Response(
                {'detail': 'Solo se pueden completar órdenes pendientes o en proceso.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        orden.estado = EstadoOrden.COMPLETADA
        orden.fecha_fin = timezone.now()
        if not orden.fecha_inicio:
            orden.fecha_inicio = orden.fecha_fin

        # Actualizar datos del técnico y solución si vienen en el payload
        orden.solucion_aplicada = request.data.get('solucion_aplicada', orden.solucion_aplicada)
        orden.diagnostico = request.data.get('diagnostico', orden.diagnostico)
        orden.contador_al_servicio = request.data.get('contador_al_servicio', orden.contador_al_servicio)
        orden.costo = request.data.get('costo', orden.costo)
        orden.save()

        # Si viene de un mantenimiento programado, actualizar su fecha
        prog_id = request.data.get('mantenimiento_programado_id')
        if prog_id:
            try:
                prog = MantenimientoProgramado.objects.get(pk=prog_id)
                prog.fecha_ultimo_mantenimiento = timezone.now().date()
                prog.fecha_proximo_mantenimiento = prog.calcular_proximo()
                prog.save(update_fields=[
                    'fecha_ultimo_mantenimiento',
                    'fecha_proximo_mantenimiento',
                    'actualizado_en'
                ])
            except MantenimientoProgramado.DoesNotExist:
                pass

        return Response(OrdenTrabajoListSerializer(orden).data)

    @extend_schema(summary='Historial de órdenes de un equipo')
    @action(detail=False, methods=['get'], url_path='equipo/(?P<equipo_id>[^/.]+)')
    def por_equipo(self, request, equipo_id=None):
        ordenes = self.get_queryset().filter(equipo_id=equipo_id)
        serializer = OrdenTrabajoListSerializer(ordenes, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(summary='Listar mantenimientos programados'),
    retrieve=extend_schema(summary='Detalle de programa'),
    create=extend_schema(summary='Crear programa de mantenimiento'),
    update=extend_schema(summary='Actualizar programa'),
    partial_update=extend_schema(summary='Actualizar parcialmente'),
    destroy=extend_schema(summary='Eliminar programa'),
)
class MantenimientoProgramadoViewSet(viewsets.ModelViewSet):
    queryset = MantenimientoProgramado.objects.select_related('tecnico').all()
    serializer_class = MantenimientoProgramadoSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'equipo_id', 'cliente_id', 'tecnico']
    search_fields = ['nombre', 'equipo_nombre', 'equipo_serial', 'cliente_nombre']
    ordering_fields = ['fecha_proximo_mantenimiento', 'creado_en']
    ordering = ['fecha_proximo_mantenimiento']
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        instance = serializer.save()
        # Calcular la primera fecha de mantenimiento al crear
        if not instance.fecha_proximo_mantenimiento:
            instance.fecha_proximo_mantenimiento = instance.calcular_proximo()
            instance.save(update_fields=['fecha_proximo_mantenimiento'])

    @extend_schema(summary='Programas que requieren atención pronto')
    @action(detail=False, methods=['get'], url_path='proximos')
    def proximos(self, request):
        programados = self.get_queryset().filter(estado=EstadoProgramado.ACTIVO)
        requieren = [p for p in programados if p.requiere_atencion]
        serializer = MantenimientoProgramadoSerializer(requieren, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary='Generar orden de trabajo desde un programa',
        responses={201: OrdenTrabajoListSerializer},
    )
    @action(detail=True, methods=['post'], url_path='generar-orden')
    def generar_orden(self, request, pk=None):
        """Crea una OT a partir del mantenimiento programado."""
        prog = self.get_object()
        orden = OrdenTrabajo.objects.create(
            tipo='PREVENTIVO',
            estado=EstadoOrden.PENDIENTE,
            prioridad='MEDIA',
            equipo_id=prog.equipo_id,
            equipo_nombre=prog.equipo_nombre,
            equipo_serial=prog.equipo_serial,
            cliente_id=prog.cliente_id,
            cliente_nombre=prog.cliente_nombre,
            tecnico=prog.tecnico,
            descripcion=prog.descripcion or f'Mantenimiento preventivo programado: {prog.nombre}',
            fecha_programada=prog.fecha_proximo_mantenimiento or date.today(),
            notas_internas=f'Generada automáticamente desde el programa: {prog.nombre}',
            creado_por='Sistema',
        )
        return Response(
            OrdenTrabajoListSerializer(orden).data,
            status=status.HTTP_201_CREATED
        )
