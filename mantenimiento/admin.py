from django.contrib import admin
from django.utils.html import format_html
from .models import Tecnico, OrdenTrabajo, PiezaReemplazada, MantenimientoProgramado


class PiezaInline(admin.TabularInline):
    model = PiezaReemplazada
    extra = 0
    fields = ['nombre_pieza', 'numero_parte', 'marca_pieza', 'cantidad', 'costo_unitario']


@admin.register(Tecnico)
class TecnicoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'empresa', 'email', 'telefono', 'activo']
    list_filter = ['tipo', 'activo']
    search_fields = ['nombre', 'empresa', 'especialidad']


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = [
        'numero_orden', 'tipo', 'estado_badge', 'prioridad_badge',
        'equipo_nombre', 'cliente_nombre', 'tecnico',
        'fecha_programada', 'duracion_display'
    ]
    list_filter = ['tipo', 'estado', 'prioridad']
    search_fields = ['numero_orden', 'equipo_nombre', 'equipo_serial', 'cliente_nombre']
    inlines = [PiezaInline]
    readonly_fields = ['numero_orden', 'creado_en', 'actualizado_en']

    def estado_badge(self, obj):
        colors = {
            'PENDIENTE': '#EF9F27',
            'EN_PROCESO': '#185FA5',
            'COMPLETADA': '#639922',
            'CANCELADA': '#888',
            'REPROGRAMADA': '#9B59B6',
        }
        color = colors.get(obj.estado, '#888')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'

    def prioridad_badge(self, obj):
        colors = {'BAJA': '#888', 'MEDIA': '#185FA5', 'ALTA': '#EF9F27', 'URGENTE': '#E24B4A'}
        color = colors.get(obj.prioridad, '#888')
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            color, obj.get_prioridad_display()
        )
    prioridad_badge.short_description = 'Prioridad'

    def duracion_display(self, obj):
        mins = obj.duracion_minutos
        if mins is None:
            return '—'
        horas = mins // 60
        minutos = mins % 60
        return f'{horas}h {minutos}m' if horas else f'{minutos}m'
    duracion_display.short_description = 'Duración'


@admin.register(MantenimientoProgramado)
class MantenimientoProgramadoAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'equipo_nombre', 'cliente_nombre',
        'frecuencia_meses', 'fecha_proximo_mantenimiento',
        'dias_display', 'estado'
    ]
    list_filter = ['estado', 'frecuencia_meses']
    search_fields = ['nombre', 'equipo_nombre', 'cliente_nombre']
    readonly_fields = ['creado_en', 'actualizado_en']

    def dias_display(self, obj):
        dias = obj.dias_para_proximo
        if dias is None:
            return '—'
        if dias < 0:
            return format_html('<span style="color:red">Vencido hace {} días</span>', abs(dias))
        if dias <= obj.dias_anticipacion:
            return format_html('<span style="color:orange">En {} días</span>', dias)
        return format_html('<span style="color:green">En {} días</span>', dias)
    dias_display.short_description = 'Próximo en'
