# 🚀 NOLIVOS FBA - API DOCUMENTATION

## Sistema Completo Nivel Enterprise

---

## 📋 ÍNDICE

1. [REST API](#rest-api)
2. [Webhooks (n8n/Zapier)](#webhooks)
3. [Export CSV/Excel](#export)
4. [Email Alerts](#email-alerts)
5. [Telegram Bot](#telegram-bot)
6. [Keyword Research](#keyword-research)
7. [PPC Calculator](#ppc-calculator)

---

## 🔑 AUTENTICACIÓN

Todas las llamadas a `/api/v1/*` requieren API Key.

### Obtener API Key

Al iniciar el servidor por primera vez, se genera automáticamente una API Key que aparece en consola:

```
🔑 TU API KEY (GUÁRDALA): abc123xyz789...
```

### Usar API Key

**Headers:**
```
X-API-Key: tu_api_key_aqui
```

**O Query String:**
```
?api_key=tu_api_key_aqui
```

---

## 🌐 REST API

### Base URL
```
http://localhost:4994/api/v1
```

### Endpoints Disponibles

#### 1. Health Check
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-29T10:30:00"
}
```

---

#### 2. Obtener Oportunidades
```http
GET /api/v1/opportunities
```

**Query Params:**
- `min_roi` (default: 5) - ROI mínimo
- `min_profit` (default: 3) - Ganancia mínima
- `limit` (default: 100) - Número de resultados
- `category` (opcional) - Filtrar por categoría

**Response:**
```json
{
  "success": true,
  "count": 10,
  "data": [
    {
      "asin": "B08XYZ123",
      "product_name": "Kitchen Gadget Pro",
      "amazon_price": 29.99,
      "supplier_price": 8.50,
      "supplier_name": "AliExpress",
      "net_profit": 9.29,
      "roi_percent": 91.0,
      "competitiveness_level": "🟢 EXCELENTE"
    }
  ],
  "filters": {
    "min_roi": 5,
    "min_profit": 3
  }
}
```

**Ejemplo con curl:**
```bash
curl -H "X-API-Key: tu_api_key" \
  "http://localhost:4994/api/v1/opportunities?min_roi=30&limit=20"
```

**Ejemplo con n8n:**
```
HTTP Request Node:
  - Method: GET
  - URL: http://localhost:4994/api/v1/opportunities
  - Headers: {"X-API-Key": "tu_api_key"}
```

---

#### 3. Obtener Oportunidad por ASIN
```http
GET /api/v1/opportunities/{asin}
```

**Example:**
```bash
curl -H "X-API-Key: tu_api_key" \
  http://localhost:4994/api/v1/opportunities/B08XYZ123
```

---

#### 4. Obtener Alertas
```http
GET /api/v1/alerts
```

**Query Params:**
- `unread_only` (default: true)
- `severity` - high/medium/low
- `limit` (default: 50)

**Response:**
```json
{
  "success": true,
  "count": 3,
  "data": [
    {
      "alert_type": "high_roi",
      "severity": "high",
      "message": "🚀 ROI EXCELENTE: 91.0% - Ganancia: $9.29",
      "product_name": "Kitchen Gadget",
      "asin": "B08XYZ123",
      "created_at": "2025-11-29 10:30:00"
    }
  ]
}
```

---

#### 5. Obtener Productos en Tendencia
```http
GET /api/v1/trends
```

**Query Params:**
- `limit` (default: 20)

---

#### 6. Obtener Categorías HOT
```http
GET /api/v1/categories/hot
```

**Response:**
```json
{
  "success": true,
  "count": 8,
  "data": [
    {
      "category": "home-kitchen",
      "trending_products": 15,
      "avg_bsr_improvement": 2500,
      "avg_score": 85.5
    }
  ]
}
```

---

#### 7. Escaneo Manual
```http
POST /api/v1/scan/manual
```

**Body:**
```json
{
  "max_products_per_category": 10
}
```

---

#### 8. Analizar Producto
```http
POST /api/v1/analyze
```

**Body:**
```json
{
  "asin": "B08XYZ123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "asin": "B08XYZ123",
    "amazon_price": 29.99,
    "supplier_price": 8.50,
    "net_profit": 9.29,
    "roi_percent": 91.0
  }
}
```

---

#### 9. Estadísticas Generales
```http
GET /api/v1/stats
```

---

#### 10. Export (CSV)
```http
GET /api/v1/export/opportunities?format=csv
```

**Query Params:**
- `format` - csv o json (default: json)
- `min_roi`, `min_profit` - Filtros

---

## 🪝 WEBHOOKS (n8n / Zapier / Make)

### Registrar Webhook

```http
POST /api/v1/webhooks/register
```

**Body:**
```json
{
  "url": "https://tu-n8n.com/webhook/abc123",
  "events": ["opportunity_found", "price_alert", "bsr_change", "high_roi_alert"],
  "name": "n8n Production"
}
```

**Response:**
```json
{
  "success": true,
  "webhook_id": 1,
  "message": "Webhook registrado exitosamente"
}
```

### Eventos Disponibles

| Evento | Descripción | Datos Enviados |
|--------|-------------|----------------|
| `opportunity_found` | Nueva oportunidad encontrada | asin, roi, profit, supplier |
| `price_alert` | Cambio de precio significativo | asin, old_price, new_price, change_percent |
| `bsr_change` | Cambio importante en BSR | asin, old_bsr, new_bsr, trend |
| `high_roi_alert` | ROI > 50% detectado | asin, roi, profit, urgency |

### Payload de Webhook

```json
{
  "event": "opportunity_found",
  "timestamp": "2025-11-29T10:30:00",
  "data": {
    "asin": "B08XYZ123",
    "product_name": "Kitchen Gadget",
    "roi": 91.0,
    "profit": 9.29,
    "amazon_price": 29.99,
    "supplier_price": 8.50,
    "url": "https://www.amazon.com/dp/B08XYZ123"
  }
}
```

### Ejemplo n8n Workflow

```
1. Webhook Trigger (escucha http://localhost:4994)
2. IF Node → roi > 50%
3. Gmail Node → Enviar email
4. Google Sheets Node → Agregar fila
```

---

## 📥 EXPORT CSV/EXCEL

### Exportar Oportunidades

```http
GET /export/opportunities/csv
```

**Query Params:**
- `min_roi`, `min_profit` - Filtros

**Descarga:** `oportunidades_20251129.csv`

### Exportar Alertas

```http
GET /export/alerts/csv
```

**Descarga:** `alertas_20251129.csv`

---

## 📧 EMAIL ALERTS

### Configurar Email

```python
from src.utils.email_sender import EmailSender

EmailSender.configure_email(
    smtp_host='smtp.gmail.com',
    smtp_port=587,
    smtp_user='tu@email.com',
    smtp_password='tu_password',
    from_email='noreply@hectorfba.com'
)
```

### Enviar Alerta

```python
from src.utils.email_sender import EmailSender

sender = EmailSender()
sender.send_alert_email('destinatario@email.com', {
    'severity': 'high',
    'alert_type': 'high_roi',
    'message': 'ROI EXCELENTE: 91%',
    'product_name': 'Kitchen Gadget',
    'asin': 'B08XYZ123',
    'created_at': '2025-11-29 10:30:00'
})
```

---

## 🤖 TELEGRAM BOT

### Configurar Bot

```python
from src.utils.telegram_bot import TelegramBot

TelegramBot.configure_bot(
    bot_token='123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11',
    chat_id='123456789'
)
```

### Obtener Chat ID

```python
chat_id = TelegramBot.get_chat_id(bot_token)
print(f"Tu Chat ID: {chat_id}")
```

### Enviar Alerta

```python
bot = TelegramBot()
bot.send_alert({
    'severity': 'high',
    'message': 'ROI EXCELENTE: 91%',
    'product_name': 'Kitchen Gadget',
    'asin': 'B08XYZ123'
})
```

---

## 🔍 KEYWORD RESEARCH

### Analizar Keyword

```http
POST /keywords/research
```

**Body:**
```json
{
  "keyword": "kitchen gadgets"
}
```

**Response:**
```json
{
  "success": true,
  "keyword": "kitchen gadgets",
  "analysis": {
    "total_results": 50000,
    "avg_reviews": 850,
    "avg_rating": 4.2,
    "sponsored_ads": 6,
    "competition_score": 45,
    "competition_level": "🟡 MEDIA",
    "recommendation": "DIFÍCIL"
  },
  "suggestions": [
    "kitchen gadgets for men",
    "kitchen gadgets 2024",
    "kitchen gadgets must have"
  ],
  "long_tail": [
    "kitchen gadgets for small spaces",
    "kitchen gadgets under 20 dollars"
  ]
}
```

---

## 💰 PPC CALCULATOR

### Calcular PPC

```http
POST /ppc/calculate
```

**Body:**
```json
{
  "price": 29.99,
  "cost": 10.00,
  "category": "home-kitchen",
  "target_sales_per_day": 10,
  "conversion_rate": 0.10
}
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "acos": {
      "max_acos": 66.69,
      "target_acos": 46.68,
      "recommended_acos": 46.68
    },
    "cpc": {
      "max_cpc": 1.40,
      "recommended_bid": 1.12,
      "category_avg_cpc": 0.80,
      "competitive": "Sí"
    },
    "budget": {
      "target_sales": 10,
      "clicks_needed": 100,
      "daily_budget": 80.00,
      "monthly_budget": 2400.00
    },
    "roi_projection": {
      "monthly_ad_spend": 2400.00,
      "estimated_sales": 300,
      "estimated_revenue": 8997.00,
      "estimated_profit": 3597.00,
      "roi_percent": 149.88,
      "profitable": true
    },
    "recommendation": {
      "decision": "🟢 LANZAR PPC",
      "reason": "ROI excelente: 149.9%",
      "suggestion": "Escala el presupuesto gradualmente"
    }
  }
}
```

---

## 🔧 EJEMPLOS DE INTEGRACIÓN

### n8n - Alerta de Oportunidad

```
Trigger: Webhook
  URL: http://localhost:4994/api/v1/webhooks/register
  Events: opportunity_found

IF Node:
  Condition: {{$json.data.roi}} > 50

Gmail:
  To: tu@email.com
  Subject: Nueva Oportunidad FBA
  Body: Producto: {{$json.data.product_name}}
        ROI: {{$json.data.roi}}%

Google Sheets:
  Spreadsheet: Oportunidades FBA
  Sheet: Opportunities
  Row: {{$json.data}}
```

### Zapier - Export Diario

```
Trigger: Schedule (Diario 8AM)

HTTP Request:
  URL: http://localhost:4994/api/v1/export/opportunities?format=csv
  Headers: X-API-Key: tu_api_key

Email:
  Subject: Reporte Diario FBA
  Attachment: CSV Response
```

---

## 📊 BASES DE DATOS

El sistema usa SQLite con las siguientes DBs:

- `opportunities.db` - Oportunidades de arbitraje
- `product_history.db` - Histórico de BSR/precios
- `alerts.db` - Alertas del sistema
- `api_keys.db` - API keys
- `webhooks.db` - Webhooks registrados
- `email_settings.db` - Configuración SMTP
- `telegram_config.db` - Configuración Telegram

---

## 🚀 QUICK START

### 1. Generar API Key
```bash
python app.py
# Copia la API key que aparece en consola
```

### 2. Test API
```bash
curl -H "X-API-Key: tu_api_key" \
  http://localhost:4994/api/v1/health
```

### 3. Registrar Webhook n8n
```bash
curl -X POST \
  -H "X-API-Key: tu_api_key" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://tu-n8n.com/webhook/xxx","events":["opportunity_found"]}' \
  http://localhost:4994/api/v1/webhooks/register
```

### 4. Ejecutar Escaneo
```bash
curl -X POST \
  -H "X-API-Key: tu_api_key" \
  -d '{"max_products_per_category":10}' \
  http://localhost:4994/api/v1/scan/manual
```

---

## 🎯 FUNCIONALIDADES TOTALES

✅ REST API completa (10+ endpoints)
✅ Webhooks para n8n/Zapier/Make
✅ Export CSV/Excel
✅ Email alerts (SMTP)
✅ Telegram bot
✅ Keyword research
✅ PPC calculator
✅ BSR tracking histórico
✅ IA trend analyzer (Codex)
✅ Competition analyzer
✅ Alert system
✅ Price tracking
✅ 28 proveedores
✅ FBA fee calculator
✅ Sales estimator
✅ Profit analyzer

**VALOR TOTAL: $299/mes (Gratis!)** 🎉
