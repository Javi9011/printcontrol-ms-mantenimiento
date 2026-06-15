from rest_framework import serializers
from .models import Tecnico, OrdenTrabajo, PiezaReemplazada, MantenimientoProgramado


class TecnicoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Tecnico
        fields = [
            'id', 'nombre', 'tipo', 'tipo_display',
            'empresa', 'telefono', 'email', 'especialidad',
            'activo', 'creado_en',
        ]
        read_only_fields = ['creado_en']


class PiezaReemplazadaSerializer(serializers.ModelSerializer):
    costo_total = serializers.ReadOnlyField()

    class Meta:
        model = PiezaReemplazada
        fields = [
            'id', 'orden', 'nombre_pieza', 'numero_parte',
            'marca_pieza', 'cantidad', 'costo_unitario', 'costo_total', 'notas',
        ]


class OrdenTrabajoListSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    tecnico_nombre = serializers.CharField(source='tecnico.nombre', read_only=True)
    duracion_minutos = serializers.ReadOnlyField()
    piezas = PiezaReemplazadaSerializer(many=True, read_only=True)

    class Meta:
        model = OrdenTrabajo
        fields = [
            'id', 'numero_orden',
            'tipo', 'tipo_display',
            'estado', 'estado_display',
            'prioridad', 'prioridad_display',
            'equipo_id', 'equipo_nombre', 'equipo_serial',
            'cliente_id', 'cliente_nombre', 'ubicacion',
            'tecnico', 'tecnico_nombre',
            'descripcion', 'diagnostico', 'solucion_aplicada',
            'fecha_programada', 'fecha_inicio', 'fecha_fin',
            'contador_al_servicio', 'duracion_minutos',
            'costo', 'piezas',
            'notas_internas', 'creado_por',
            'creado_en', 'actualizado_en',
        ]


class OrdenTrabajoWriteSerializer(serializers.ModelSerializer):
    piezas = PiezaReemplazadaSerializer(many=True, required=False)

    class Meta:
        model = OrdenTrabajo
        fields = [
            'numero_orden', 'tipo', 'estado', 'prioridad',
            'equipo_id', 'equipo_nombre', 'equipo_serial',
            'cliente_id', 'cliente_nombre', 'ubicacion',
            'tecnico', 'descripcion', 'diagnostico', 'solucion_aplicada',
            'fecha_programada', 'fecha_inicio', 'fecha_fin',
            'contador_al_servicio', 'costo', 'piezas',
            'notas_internas', 'creado_por',
        ]

    def create(self, validated_data):
        piezas_data = validated_data.pop('piezas', [])
        orden = OrdenTrabajo.objects.create(**validated_data)
        for p in piezas_data:
            PiezaReemplazada.objects.create(orden=orden, **p)
        return orden

    def update(self, instance, validated_data):
        piezas_data = validated_data.pop('piezas', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if piezas_data is not None:
            instance.piezas.all().delete()
            for p in piezas_data:
                PiezaReemplazada.objects.create(orden=instance, **p)
        return instance


class MantenimientoProgramadoSerializer(serializers.ModelSerializer):
    tecnico_nombre = serializers.CharField(source='tecnico.nombre', read_only=True)
    dias_para_proximo = serializers.ReadOnlyField()
    requiere_atencion = serializers.ReadOnlyField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = MantenimientoProgramado
        fields = [
            'id', 'equipo_id', 'equipo_nombre', 'equipo_serial',
            'cliente_id', 'cliente_nombre',
            'nombre', 'descripcion', 'frecuencia_meses',
            'tecnico', 'tecnico_nombre',
            'estado', 'estado_display',
            'fecha_inicio_programa',
            'fecha_ultimo_mantenimiento',
            'fecha_proximo_mantenimiento',
            'dias_anticipacion', 'dias_para_proximo',
            'requiere_atencion', 'notas',
            'creado_en', 'actualizado_en',
        ]
        read_only_fields = ['creado_en', 'actualizado_en']


class ResumenMantenimientoSerializer(serializers.Serializer):
    ordenes_pendientes = serializers.IntegerField()
    ordenes_en_proceso = serializers.IntegerField()
    ordenes_completadas_mes = serializers.IntegerField()
    programados_proximos = serializers.IntegerField()
    programados_vencidos = serializers.IntegerField()
    tecnicos_activos = serializers.IntegerField()
