from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TecnicoViewSet, OrdenTrabajoViewSet, MantenimientoProgramadoViewSet

router = DefaultRouter()
router.register(r'tecnicos', TecnicoViewSet, basename='tecnico')
router.register(r'ordenes', OrdenTrabajoViewSet, basename='orden')
router.register(r'programados', MantenimientoProgramadoViewSet, basename='programado')

urlpatterns = [
    path('', include(router.urls)),
]
