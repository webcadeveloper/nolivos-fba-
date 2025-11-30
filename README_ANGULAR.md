# NOLIVOS FBA - Angular + Flask

## 🚀 Cómo arrancar la aplicación

### Opción 1: Scripts automáticos (RECOMENDADO)

**Terminal 1 - Backend:**
```bash
bash START_BACKEND.sh
```

**Terminal 2 - Frontend:**
```bash
bash START_FRONTEND.sh
```

### Opción 2: Manual

**Terminal 1 - Backend API:**
```bash
cd "/mnt/c/Users/Admin/OneDrive - Nolivos Law/Aplicaciones/AMAZON/amz-review-analyzer"
source venv/bin/activate
python api_app.py
```

**Terminal 2 - Frontend Angular:**
```bash
cd "/mnt/c/Users/Admin/OneDrive - Nolivos Law/Aplicaciones/AMAZON/amz-review-analyzer/frontend"
ng serve --open
```

## 📋 Puertos

- **Backend API**: http://localhost:5000
- **Frontend Angular**: http://localhost:4200

## 🔧 Arquitectura

```
┌─────────────────────┐         ┌──────────────────────┐
│  Angular Frontend   │ ◄─────► │   Flask Backend      │
│  (Puerto 4200)      │  HTTP   │   REST API           │
│                     │  JSON   │   (Puerto 5000)      │
│  - TypeScript       │         │   - Python           │
│  - Components       │         │   - SQLite           │
│  - Services         │         │   - Scrapers         │
│  - Reactive Forms   │         │   - CJDropshipping   │
└─────────────────────┘         └──────────────────────┘
```

## 📁 Estructura de archivos

```
amz-review-analyzer/
├── api_app.py              # Backend REST API
├── app.py                  # Backend antiguo (mantener por ahora)
├── .env                    # Variables de entorno (API keys)
├── src/                    # Código Python (scrapers, analyzers)
├── frontend/               # Aplicación Angular
│   ├── src/
│   │   ├── app/
│   │   │   ├── models/           # TypeScript interfaces
│   │   │   ├── services/         # API services
│   │   │   └── components/       # Angular components
│   │   └── environments/
│   └── angular.json
├── START_BACKEND.sh        # Script para arrancar backend
└── START_FRONTEND.sh       # Script para arrancar frontend
```

## ✅ Lo que ya está configurado

1. ✅ Backend REST API (`api_app.py`)
2. ✅ Flask-CORS para peticiones cross-origin
3. ✅ Proyecto Angular con routing
4. ✅ Modelos TypeScript (Opportunity, Stats)
5. ✅ Servicio API (ApiService)
6. ✅ Base de datos con 4 proveedores
7. ✅ CJDropshipping API key en .env

## 🎯 Estado actual del proyecto

### ✅ Completado:
- Backend REST API funcionando (`api_app.py`)
- Flask-CORS configurado
- Angular project creado con routing
- HttpClient configurado en `app.config.ts`
- Modelos TypeScript (`models/opportunity.ts`)
- Servicio API (`services/api.service.ts`)
- Scripts de arranque automático

### 🔨 Pendiente (cuando necesites UI completa):
Para completar el frontend Angular con interfaz visual, puedes crear:

```bash
cd frontend
ng generate component components/opportunities
ng generate component components/dashboard
ng generate component components/scanner
```

Luego configurar routing y añadir templates HTML/CSS.

### 🧪 Probar la API ahora mismo:
Aunque no tengas componentes visuales, puedes probar que la API funciona:

1. Arrancar backend: `bash START_BACKEND.sh`
2. Abrir en navegador: http://localhost:5000/api/health
3. Ver oportunidades: http://localhost:5000/api/opportunities
4. Ver estadísticas: http://localhost:5000/api/stats

## 🔐 Seguridad

- `.env` está en `.gitignore` (no se sube a GitHub)
- API keys protegidas
- CORS configurado solo para localhost

## 📞 Soporte

Author: Hector Nolivos
Email: hector@nolivos.cloud
Website: https://nolivos.cloud
