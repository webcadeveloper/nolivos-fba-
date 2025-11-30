# 🚀 n8n Workflow Templates for NOLIVOS FBA

## Índice

1. [Configuración Inicial](#configuración-inicial)
2. [Workflow 1: Nueva Oportunidad → Email + Google Sheets](#workflow-1-nueva-oportunidad--email--google-sheets)
3. [Workflow 2: ROI Alto → Telegram + Notion](#workflow-2-roi-alto--telegram--notion)
4. [Workflow 3: Cambio de Precio → Slack Alert](#workflow-3-cambio-de-precio--slack-alert)
5. [Workflow 4: Reporte Diario Automático](#workflow-4-reporte-diario-automático)
6. [Workflow 5: BSR Mejorando → Añadir a Watchlist](#workflow-5-bsr-mejorando--añadir-a-watchlist)
7. [Workflow 6: Categoría Caliente → Twitter Post](#workflow-6-categoría-caliente--twitter-post)

---

## Configuración Inicial

### 1. Registrar Webhook en NOLIVOS FBA

```bash
curl -X POST \
  -H "X-API-Key: tu_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://tu-n8n-url.com/webhook/hector-fba",
    "events": [
      "opportunity_found",
      "high_roi_opportunity",
      "ultra_high_roi",
      "price_drop",
      "bsr_improved",
      "hot_category_detected"
    ],
    "name": "n8n Production"
  }' \
  http://localhost:4994/api/v1/webhooks/register
```

### 2. URL del Webhook en n8n

Cuando crees un nodo **Webhook** en n8n, obtendrás una URL como:
```
https://tu-n8n.com/webhook/abc-123-xyz
```

Usa esta URL en el paso anterior.

---

## Workflow 1: Nueva Oportunidad → Email + Google Sheets

**Objetivo:** Cuando se encuentre una nueva oportunidad, enviar email y guardar en Google Sheets.

### Nodos:

```
1. Webhook Trigger
   ├─ Escucha: opportunity_found
   └─ URL: https://tu-n8n.com/webhook/hector-fba

2. IF Node
   ├─ Condición: {{ $json.data.roi }} > 30
   └─ True → Continuar

3. Gmail Node
   ├─ To: tu@email.com
   ├─ Subject: 🚀 Nueva Oportunidad FBA - ROI {{ $json.data.roi }}%
   └─ Body:
       Producto: {{ $json.data.product_name }}
       ASIN: {{ $json.data.asin }}

       💰 Precio Amazon: ${{ $json.data.amazon_price }}
       🏪 Precio Proveedor: ${{ $json.data.supplier_price }}

       📈 ROI: {{ $json.data.roi }}%
       💵 Ganancia: ${{ $json.data.profit }}

       Ver en Amazon: {{ $json.data.url }}
       Dashboard: {{ $json.data.dashboard_url }}

4. Google Sheets Node
   ├─ Spreadsheet: Oportunidades FBA
   ├─ Sheet: Opportunities
   └─ Columns:
       - ASIN: {{ $json.data.asin }}
       - Producto: {{ $json.data.product_name }}
       - Precio Amazon: {{ $json.data.amazon_price }}
       - Precio Proveedor: {{ $json.data.supplier_price }}
       - ROI: {{ $json.data.roi }}
       - Ganancia: {{ $json.data.profit }}
       - Proveedor: {{ $json.data.supplier }}
       - URL: {{ $json.data.url }}
       - Fecha: {{ $now }}
```

---

## Workflow 2: ROI Alto → Telegram + Notion

**Objetivo:** Oportunidades con ROI > 50% se envían a Telegram y se guardan en Notion.

### Nodos:

```
1. Webhook Trigger
   ├─ Escucha: high_roi_opportunity, ultra_high_roi
   └─ URL: https://tu-n8n.com/webhook/high-roi

2. Telegram Node
   ├─ Chat ID: tu_chat_id
   └─ Message:
       🚨 ALERTA ROI ALTO 🚨

       {{ $json.data.product_name }}

       💰 ROI: {{ $json.data.roi }}%
       💵 Ganancia: ${{ $json.data.profit }}

       Amazon: ${{ $json.data.amazon_price }}
       Proveedor: ${{ $json.data.supplier_price }}

       ⚡ {{ $json.data.urgency }}
       📋 {{ $json.data.action_required }}

       🔗 {{ $json.data.url }}

3. Notion Node
   ├─ Database: High ROI Opportunities
   └─ Properties:
       - Name: {{ $json.data.product_name }}
       - ASIN: {{ $json.data.asin }}
       - ROI: {{ $json.data.roi }}
       - Profit: {{ $json.data.profit }}
       - Amazon Price: {{ $json.data.amazon_price }}
       - Supplier Price: {{ $json.data.supplier_price }}
       - Urgency: {{ $json.data.urgency }}
       - URL: {{ $json.data.url }}
       - Date Added: {{ $now }}
```

---

## Workflow 3: Cambio de Precio → Slack Alert

**Objetivo:** Notificar en Slack cuando un precio baje significativamente.

### Nodos:

```
1. Webhook Trigger
   ├─ Escucha: price_drop, price_drop_significant
   └─ URL: https://tu-n8n.com/webhook/price-drop

2. Slack Node
   ├─ Channel: #fba-alerts
   └─ Message:
       📉 *PRECIO BAJÓ*

       Producto: {{ $json.data.product_name }}
       ASIN: {{ $json.data.asin }}

       Precio Anterior: ${{ $json.data.old_price }}
       Precio Nuevo: ${{ $json.data.new_price }}
       Ahorro: ${{ $json.data.change_amount }} ({{ $json.data.change_percent }}%)

       🔴 Urgencia: {{ $json.data.urgency }}

       <{{ $json.data.url }}|Ver Producto>

3. HTTP Request Node (opcional)
   ├─ Method: POST
   ├─ URL: http://localhost:4994/api/v1/analyze
   └─ Body: { "asin": "{{ $json.data.asin }}" }
   (Re-analizar oportunidad con nuevo precio)
```

---

## Workflow 4: Reporte Diario Automático

**Objetivo:** Enviar reporte diario con resumen de oportunidades.

### Nodos:

```
1. Schedule Trigger
   └─ Cron: 0 8 * * * (Todos los días 8 AM)

2. HTTP Request Node
   ├─ Method: GET
   ├─ URL: http://localhost:4994/api/v1/opportunities
   ├─ Headers: X-API-Key: tu_api_key
   └─ Query: min_roi=20&limit=10

3. Function Node
   └─ Code:
       const opportunities = $input.all()[0].json.data;
       const totalOpps = opportunities.length;
       const avgROI = opportunities.reduce((sum, o) => sum + o.roi_percent, 0) / totalOpps;
       const bestOpp = opportunities[0];

       return {
         json: {
           total: totalOpps,
           avgROI: avgROI.toFixed(2),
           best: bestOpp,
           list: opportunities
         }
       };

4. Gmail Node
   ├─ To: tu@email.com
   ├─ Subject: 📊 Reporte Diario FBA - {{ $json.total }} Oportunidades
   └─ Body:
       Buenos días!

       📈 RESUMEN DIARIO

       Total Oportunidades: {{ $json.total }}
       ROI Promedio: {{ $json.avgROI }}%

       🥇 MEJOR OPORTUNIDAD:
       {{ $json.best.product_name }}
       ROI: {{ $json.best.roi_percent }}%
       Ganancia: ${{ $json.best.net_profit }}

       Ver Dashboard: http://localhost:4994/opportunities

5. Google Sheets Node
   ├─ Append rows with all opportunities
```

---

## Workflow 5: BSR Mejorando → Añadir a Watchlist

**Objetivo:** Cuando un producto mejore su BSR, añadirlo a una lista de seguimiento.

### Nodos:

```
1. Webhook Trigger
   ├─ Escucha: bsr_improved, bsr_improved_significant
   └─ URL: https://tu-n8n.com/webhook/bsr-change

2. Airtable Node
   ├─ Table: Watchlist
   └─ Fields:
       - ASIN: {{ $json.data.asin }}
       - Product Name: {{ $json.data.product_name }}
       - Old BSR: {{ $json.data.old_bsr }}
       - New BSR: {{ $json.data.new_bsr }}
       - Change: {{ $json.data.change }}
       - Trend: {{ $json.data.trend }}
       - Interpretation: {{ $json.data.interpretation }}
       - Added: {{ $now }}

3. IF Node
   ├─ Condición: {{ $json.data.change }} > 5000
   └─ True → Telegram Alert

4. Telegram Node
   └─ Message:
       📊 BSR MEJORANDO RÁPIDO

       {{ $json.data.product_name }}

       BSR Anterior: #{{ $json.data.old_bsr }}
       BSR Nuevo: #{{ $json.data.new_bsr }}
       Mejoró: {{ $json.data.change }} posiciones

       {{ $json.data.interpretation }}

       🔗 {{ $json.data.url }}
```

---

## Workflow 6: Categoría Caliente → Twitter Post

**Objetivo:** Cuando se detecte una categoría caliente, publicar en Twitter.

### Nodos:

```
1. Webhook Trigger
   ├─ Escucha: hot_category_detected
   └─ URL: https://tu-n8n.com/webhook/hot-category

2. Twitter Node
   └─ Tweet:
       🔥 CATEGORÍA CALIENTE DETECTADA

       📦 {{ $json.data.category }}

       {{ $json.data.trending_products }} productos en tendencia
       ROI promedio: {{ $json.data.avg_roi }}%

       💡 {{ $json.data.action }}

       #FBA #AmazonSeller #Arbitrage

3. Discord Webhook (opcional)
   └─ Notificar comunidad
```

---

## Workflow 7: Pipeline Completo de Oportunidad

**Objetivo:** Pipeline automático para cada oportunidad encontrada.

### Nodos:

```
1. Webhook Trigger (opportunity_found)

2. HTTP Request - Analizar Competencia
   ├─ URL: http://localhost:4994/api/v1/competition/{{$json.data.asin}}

3. HTTP Request - Keyword Research
   ├─ URL: http://localhost:4994/api/v1/keywords/research
   └─ Body: { "keyword": "{{$json.data.product_name}}" }

4. HTTP Request - PPC Calculator
   ├─ URL: http://localhost:4994/api/v1/ppc/calculate
   └─ Body: {
       "price": "{{$json.data.amazon_price}}",
       "cost": "{{$json.data.supplier_price}}"
     }

5. Function - Combinar Datos
   └─ Merge all analysis results

6. IF - Evaluar Viabilidad Total
   ├─ ROI > 30
   ├─ Competition < 20 sellers
   ├─ PPC profitable
   └─ True → Continuar

7. Notion - Crear Página Completa
   └─ Con todo el análisis

8. Gmail - Enviar Reporte Detallado

9. Google Calendar - Agendar Revisión
   └─ Evento en 3 días para revisar
```

---

## Eventos Disponibles

| Evento | Cuándo se Dispara | Datos |
|--------|-------------------|-------|
| `opportunity_found` | Nueva oportunidad detectada | asin, roi, profit, supplier |
| `high_roi_opportunity` | ROI > 50% | urgency, action_required |
| `ultra_high_roi` | ROI > 100% | recommended_quantity |
| `low_competition_opportunity` | < 10 sellers | seller_count, reason |
| `price_drop` | Precio bajó | old_price, new_price, change_percent |
| `price_drop_significant` | Precio bajó > 20% | urgency |
| `bsr_improved` | BSR mejoró | old_bsr, new_bsr, trend |
| `bsr_improved_significant` | BSR mejoró > 1000 posiciones | change, interpretation |
| `demand_increasing` | Demanda aumentando | direction, magnitude |
| `competition_decreased` | Competencia bajó | old_seller_count, new_seller_count |
| `hot_category_detected` | Categoría caliente | trending_products, avg_roi |
| `scan_completed` | Escaneo completado | total_scanned, opportunities_found |
| `daily_scan_completed` | Escaneo diario terminado | top_opportunities, best_roi |

---

## Tips de n8n

### 1. Filtros Útiles

```javascript
// Solo ROI > 50%
{{ $json.data.roi > 50 }}

// Solo proveedores específicos
{{ $json.data.supplier === "AliExpress" }}

// Solo categorías específicas
{{ ["home-kitchen", "toys"].includes($json.data.category) }}

// Combinar condiciones
{{ $json.data.roi > 30 && $json.data.profit > 10 }}
```

### 2. Formatear Mensajes

```javascript
// En Function Node
const data = $input.first().json.data;

return {
  json: {
    subject: `🚀 Nueva Oportunidad - ${data.product_name}`,
    body: `
      Producto: ${data.product_name}
      ROI: ${data.roi}%
      Ganancia: $${data.profit.toFixed(2)}

      Ver: ${data.url}
    `
  }
};
```

### 3. Guardar en Multiple Destinos

Usa **Split in Batches** para enviar la misma oportunidad a:
- Google Sheets
- Airtable
- Notion
- Email
- Telegram

En paralelo!

---

## Ejemplo Completo JSON (Importar en n8n)

```json
{
  "name": "NOLIVOS FBA - Oportunidad a Email",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "hector-fba-opportunity",
        "responseMode": "onReceived",
        "options": {}
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "conditions": {
          "number": [
            {
              "value1": "={{ $json.data.roi }}",
              "operation": "larger",
              "value2": 30
            }
          ]
        }
      },
      "name": "IF ROI > 30%",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [450, 300]
    },
    {
      "parameters": {
        "sendTo": "tu@email.com",
        "subject": "🚀 Nueva Oportunidad FBA - ROI {{ $json.data.roi }}%",
        "message": "=Producto: {{ $json.data.product_name }}\nASIN: {{ $json.data.asin }}\n\n💰 Precio Amazon: ${{ $json.data.amazon_price }}\n🏪 Precio Proveedor: ${{ $json.data.supplier_price }}\n\n📈 ROI: {{ $json.data.roi }}%\n💵 Ganancia: ${{ $json.data.profit }}\n\nVer: {{ $json.data.url }}"
      },
      "name": "Gmail",
      "type": "n8n-nodes-base.gmail",
      "typeVersion": 1,
      "position": [650, 200],
      "credentials": {
        "gmailOAuth2": {
          "id": "1",
          "name": "Gmail account"
        }
      }
    }
  ],
  "connections": {
    "Webhook": {
      "main": [
        [
          {
            "node": "IF ROI > 30%",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "IF ROI > 30%": {
      "main": [
        [
          {
            "node": "Gmail",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

---

## Próximos Pasos

1. **Importa un workflow** en n8n
2. **Copia tu webhook URL** del nodo Webhook
3. **Regístralo** en NOLIVOS FBA usando el endpoint `/api/v1/webhooks/register`
4. **Ejecuta un escaneo** y observa las notificaciones!

🎉 **¡Ahora tienes automatización total!**
