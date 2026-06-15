# ms-mantenimiento — PrintControl

Microservicio de órdenes de trabajo, mantenimientos programados e historial de piezas.

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET/POST | `/api/v1/tecnicos/` | Gestión de técnicos (internos y externos) |
| GET/POST | `/api/v1/ordenes/` | Crear / listar órdenes de trabajo |
| GET | `/api/v1/ordenes/resumen/` | Métricas para dashboard |
| POST | `/api/v1/ordenes/{id}/iniciar/` | Iniciar una orden |
| POST | `/api/v1/ordenes/{id}/completar/` | Completar una orden |
| GET | `/api/v1/ordenes/equipo/{id}/` | Historial de un equipo |
| GET/POST | `/api/v1/programados/` | Mantenimientos preventivos programados |
| GET | `/api/v1/programados/proximos/` | Los que requieren atención pronto |
| POST | `/api/v1/programados/{id}/generar-orden/` | Crear OT desde un programa |
| GET | `/api/docs/` | Swagger UI |

## Levantar con Docker

```bash
cd ms-mantenimiento
Copy-Item .env.example .env   # Windows PowerShell
docker-compose up --build
```

Accede a:
- API: http://localhost:8004/api/v1/
- Swagger: http://localhost:8004/api/docs/
- Admin: http://localhost:8004/admin/

## Flujo típico

```
1. Registrar técnicos  →  POST /api/v1/tecnicos/
2. Crear programa      →  POST /api/v1/programados/
3. Generar OT          →  POST /api/v1/programados/{id}/generar-orden/
4. Iniciar trabajo     →  POST /api/v1/ordenes/{id}/iniciar/
5. Completar + piezas  →  POST /api/v1/ordenes/{id}/completar/
6. Ver historial       →  GET  /api/v1/ordenes/equipo/{equipo_id}/
```
