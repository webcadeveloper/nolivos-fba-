# 🚀 n8n Workflows para NOLIVOS FBA

## 📋 Workflows Incluidos

| Archivo | Descripción | Trigger | Acciones |
|---------|-------------|---------|----------|
| `1-oportunidad-a-email.json` | Nueva oportunidad → Email + Google Sheets | Webhook | Gmail, Google Sheets |
| `2-roi-alto-telegram.json` | ROI Alto → Telegram + Notion | Webhook | Telegram, Notion |
| `3-reporte-diario.json` | Reporte diario automático | Schedule (8 AM) | Gmail, Telegram |

---

## 🔧 Instalación Rápida

### 1. Importar Workflow en n8n

1. Abre n8n (https://tu-n8n.com o localhost:5678)
2. Click en el menú hamburguesa (☰) → **Import from file**
3. Selecciona uno de los archivos `.json` de esta carpeta
4. El workflow se importará automáticamente

### 2. Configurar Credenciales

Cada workflow necesita credenciales específicas:

#### Gmail (Workflows 1, 3)
1. Click en el nodo **Gmail**
2. Click en **Create New Credential**
3. Sigue el proceso de OAuth con Google
4. Autoriza n8n a enviar emails

#### Google Sheets (Workflow 1)
1. Click en el nodo **Google Sheets**
2. Crea nueva credencial OAuth
3. Autoriza acceso a tus hojas de cálculo
4. Reemplaza `REEMPLAZAR_CON_TU_SHEET_ID` con el ID de tu hoja

**¿Cómo obtener Sheet ID?**
```
URL: https://docs.google.com/spreadsheets/d/ABC123XYZ/edit
                                            ^^^^^^^^
                                            Sheet ID
```

#### Telegram (Workflows 2, 3)
1. Habla con [@BotFather](https://t.me/BotFather) en Telegram
2. Crea un nuevo bot: `/newbot`
3. Copia el **Bot Token**
4. Obtén tu **Chat ID**:
   - Habla con [@userinfobot](https://t.me/userinfobot)
   - Te dará tu Chat ID
5. Configura en n8n:
   - Bot Token: El token de BotFather
   - Chat ID: Tu Chat ID

#### Notion (Workflow 2)
1. Ve a [Notion Integrations](https://www.notion.so/my-integrations)
2. Crea nueva integración → Copia el **Internal Integration Token**
3. Comparte tu database con la integración
4. Obtén el **Database ID**:
```
URL: https://notion.so/workspace/ABC123XYZ?v=def456
                              ^^^^^^^^
                              Database ID
```

#### API Key (Workflow 3)
1. En n8n, crea credencial **Header Auth**
2. Header Name: `X-API-Key`
3. Header Value: Tu API key de NOLIVOS FBA

**¿Dónde está mi API Key?**
```bash
# Aparece en la consola al iniciar el servidor
python app.py

# Salida:
# 🔑 TU API KEY (GUÁRDALA): abc123xyz789...
```

---

## 📝 Configuración Específica por Workflow

### Workflow 1: Oportunidad a Email

**Paso 1: Obtener URL del Webhook**
1. Abre el workflow importado
2. Click en el nodo **Webhook - Nueva Oportunidad**
3. Copia la **Production URL**:
```
https://tu-n8n.com/webhook/abc-123-xyz
```

**Paso 2: Registrar Webhook en NOLIVOS FBA**
```bash
curl -X POST \
  -H "X-API-Key: tu_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://tu-n8n.com/webhook/abc-123-xyz",
    "events": ["opportunity_found"],
    "name": "n8n - Oportunidad a Email"
  }' \
  http://localhost:4994/api/v1/webhooks/register
```

**Paso 3: Configurar Email y Google Sheets**
- Reemplaza `tu@email.com` con tu email real
- Configura credenciales de Gmail
- Crea hoja de Google Sheets con columnas:
  - ASIN | Producto | Precio Amazon | Precio Proveedor | ROI % | Ganancia | Proveedor | Fecha

**Paso 4: Activar Workflow**
- Click en el switch de **Active** (arriba a la derecha)
- El workflow ahora escuchará eventos

**Paso 5: Probar**
```bash
# Desde NOLIVOS FBA dashboard
# Ve a http://localhost:4994/webhooks
# Click en "Disparar Prueba" para el evento opportunity_found
```

---

### Workflow 2: ROI Alto a Telegram

**Configuración:**

1. **Obtener Webhook URL** (igual que Workflow 1)

2. **Registrar Webhook**
```bash
curl -X POST \
  -H "X-API-Key: tu_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://tu-n8n.com/webhook/def-456-xyz",
    "events": ["high_roi_opportunity", "ultra_high_roi"],
    "name": "n8n - ROI Alto a Telegram"
  }' \
  http://localhost:4994/api/v1/webhooks/register
```

3. **Configurar Telegram Bot**
   - Reemplaza `TU_CHAT_ID` con tu Chat ID real
   - Configura credenciales de Telegram

4. **Configurar Notion (Opcional)**
   - Crea database en Notion con propiedades:
     - Name (Title)
     - ASIN (Text)
     - ROI (Number)
     - Ganancia (Number)
     - Precio Amazon (Number)
     - Precio Proveedor (Number)
     - Urgencia (Select: HIGH, MEDIUM, LOW)
     - URL (URL)
   - Reemplaza `REEMPLAZAR_CON_TU_DATABASE_ID`

5. **Activar y Probar**

---

### Workflow 3: Reporte Diario

**Sin Webhook - Usa Schedule**

**Configuración:**

1. **Configurar API Key**
   - Crea credencial **Header Auth**
   - Header: `X-API-Key`
   - Value: Tu API key

2. **Personalizar Filtros (Opcional)**
   - En el nodo **Obtener Oportunidades**
   - Modifica query params:
     - `min_roi`: Cambiar de 20 a lo que quieras
     - `limit`: Máximo de oportunidades (default: 10)

3. **Configurar Email y Telegram**
   - Reemplaza `tu@email.com`
   - Reemplaza `TU_CHAT_ID`

4. **Cambiar Horario (Opcional)**
   - Nodo **Schedule Trigger**
   - Cron Expression: `0 8 * * *` (8 AM diario)
   - Otros ejemplos:
     - `0 20 * * *` → 8 PM diario
     - `0 8 * * 1` → 8 AM solo lunes
     - `0 8,20 * * *` → 8 AM y 8 PM

5. **Activar Workflow**
   - Se ejecutará automáticamente según schedule

---

## 🧪 Testing de Workflows

### Opción 1: Desde n8n

1. Con el workflow abierto, click en **Execute Workflow** (arriba)
2. Esto simula el trigger y ejecuta el workflow
3. Verás los resultados en tiempo real

### Opción 2: Desde NOLIVOS FBA Dashboard

1. Ve a http://localhost:4994/webhooks
2. Verás todos los webhooks registrados
3. Click en **"🧪 Probar"** junto a tu webhook
4. Se enviará evento de prueba

### Opción 3: Disparar Evento Manualmente

1. En dashboard de webhooks
2. Sección "Eventos Disponibles"
3. Click en **"⚡ Disparar Prueba"** para cualquier evento
4. Se enviará a TODOS los webhooks suscritos

---

## 🔍 Debugging

### Ver Logs en n8n

1. Abre el workflow
2. Click en **Executions** (panel izquierdo)
3. Ve el historial de todas las ejecuciones
4. Click en cualquiera para ver detalles

### Ver Logs en NOLIVOS FBA

1. Ve a http://localhost:4994/webhooks
2. Sección "Logs Recientes"
3. Muestra últimos 50 envíos de webhooks
4. ✓ Exitoso o ✗ Error con detalles

### Problemas Comunes

**Error: "Webhook not found"**
- Verifica que el webhook esté registrado en NOLIVOS FBA
- Check: `http://localhost:4994/webhooks`

**Error: "API Key invalid"**
- Verifica X-API-Key en las credenciales
- Obtén nueva key reiniciando el servidor

**Email no llega**
- Verifica credenciales de Gmail
- Revisa carpeta de spam
- Asegúrate que el workflow esté **Active**

**Telegram no envía**
- Verifica Bot Token y Chat ID
- Asegúrate de haber hablado con el bot primero (envía /start)

---

## 💡 Tips Pro

### 1. Filtrar Eventos en n8n

Usa **IF** nodes para filtrar:

```javascript
// Solo ROI > 50%
{{ $json.data.roi > 50 }}

// Solo categorías específicas
{{ ["home-kitchen", "toys"].includes($json.data.category) }}

// Combinar condiciones
{{ $json.data.roi > 30 && $json.data.profit > 10 }}
```

### 2. Formatear Números

```javascript
// En Function Node
const roi = parseFloat($json.data.roi);
return {
  json: {
    roi_formatted: roi.toFixed(2) + '%'
  }
};
```

### 3. Múltiples Destinos

Conecta **múltiples nodos** desde el IF:
```
Webhook → IF → Email
               ├─ Google Sheets
               ├─ Telegram
               ├─ Slack
               └─ Notion
```

### 4. Error Handling

Agrega nodo **Error Trigger** para capturar errores:
```
Error Trigger → Telegram → "⚠️ Error en workflow!"
```

---

## 📚 Eventos Disponibles

| Evento | Cuándo se Dispara | Urgencia |
|--------|-------------------|----------|
| `opportunity_found` | Nueva oportunidad detectada | Normal |
| `high_roi_opportunity` | ROI > 50% | Alta |
| `ultra_high_roi` | ROI > 100% | Crítica |
| `low_competition_opportunity` | < 10 sellers | Media |
| `price_drop` | Precio bajó | Media |
| `price_drop_significant` | Precio bajó > 20% | Alta |
| `bsr_improved` | BSR mejoró | Media |
| `bsr_improved_significant` | BSR mejoró > 1000 | Alta |
| `demand_increasing` | Demanda aumentando | Media |
| `competition_decreased` | Competencia bajó | Alta |
| `hot_category_detected` | Categoría caliente | Media |
| `scan_completed` | Escaneo completado | Normal |
| `daily_scan_completed` | Escaneo diario terminado | Normal |

**Ver todos los eventos:** http://localhost:4994/webhooks

---

## 🎯 Próximos Pasos

1. **Importa los 3 workflows**
2. **Configura credenciales** (Gmail, Sheets, Telegram)
3. **Registra webhooks** en NOLIVOS FBA
4. **Prueba cada workflow** usando "🧪 Probar"
5. **Activa los workflows**
6. **Ejecuta un escaneo** en NOLIVOS FBA
7. **Observa las notificaciones** llegar! 🎉

---

## 🆘 Soporte

- **Documentación completa:** Ver `../N8N_WORKFLOWS.md`
- **API Docs:** Ver `../API_DOCUMENTATION.md`
- **Dashboard de Webhooks:** http://localhost:4994/webhooks
- **n8n Docs:** https://docs.n8n.io

---

**¡Ahora tienes automatización total de FBA con n8n!** 🚀
