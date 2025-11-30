# SP-API Setup Instructions

## 1. Registrar App en Amazon Developer Console

1. Ve a https://developer.amazon.com/
2. Inicia sesión con tu cuenta de Amazon Seller
3. Ve a "Developer Console" → "Login with Amazon"
4. Crea una nueva "Security Profile"
5. Anota:
   - **LWA App ID** (Client ID)
   - **LWA Client Secret**

## 2. Registrar App en Seller Central

1. Ve a https://sellercentral.amazon.com/
2. Settings → User Permissions → "Manage Your Apps"
3. "Authorize new developer" → Ingresa tu Developer ID
4. Selecciona permisos necesarios:
   - Orders
   - Product Fees
   - Catalog Items
   - (Opcional) Advertising
5. Copia el **Refresh Token** generado

## 3. Configurar AWS IAM Role

1. Ve a AWS Console → IAM
2. Crea un nuevo Role con política:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "execute-api:Invoke",
    "Resource": "arn:aws:execute-api:*:*:*"
  }]
}
```
3. Anota el **Role ARN**

## 4. Configurar Credenciales

Copia `config/sp_api_config.json.template` a `config/sp_api_config.json` y completa:

```json
{
  "lwa_app_id": "amzn1.application-oa2-client.TU_APP_ID",
  "lwa_client_secret": "TU_CLIENT_SECRET",
  "refresh_token": "TU_REFRESH_TOKEN",
  
  "aws_access_key": "TU_AWS_ACCESS_KEY",
  "aws_secret_key": "TU_AWS_SECRET_KEY",
  "role_arn": "arn:aws:iam::TU_CUENTA:role/TU_ROLE",
  
  "marketplace_id": "ATVPDKIKX0DER",
  "region": "us-east-1"
}
```

**IMPORTANTE**: Añade `config/sp_api_config.json` a `.gitignore`

## 5. Variables de Entorno (Alternativa)

En lugar de archivo JSON, puedes usar variables de entorno:

```bash
export SP_API_LWA_APP_ID="amzn1.application-oa2-client...."
export SP_API_LWA_CLIENT_SECRET="..."
export SP_API_REFRESH_TOKEN="..."
export SP_API_AWS_ACCESS_KEY="..."
export SP_API_AWS_SECRET_KEY="..."
export SP_API_ROLE_ARN="arn:aws:iam::..."
```

## 6. Verificar Configuración

```bash
curl http://localhost:4994/sp-api/status
```

Debería retornar:
```json
{
  "success": true,
  "configured": true,
  "message": "SP-API is configured"
}
```

## 7. Endpoints Disponibles

### Verificar Status
```
GET /sp-api/status
```

### Obtener Órdenes
```
GET /sp-api/orders?days=7
```

### Obtener Fees Oficiales
```
GET /sp-api/fees/B07PXGQC1Q?price=29.99&is_fba=true
```

### Obtener Info de Catálogo
```
GET /sp-api/catalog/B07PXGQC1Q
```

## Rate Limits

- **Orders API**: 1 request / 60 seconds
- **Catalog API**: 2 requests / second
- **Fees API**: 1 request / second

El cliente implementa rate limiting automático y cache de 1-24 horas.

## Troubleshooting

### Error: "SP-API not configured"
- Verifica que `config/sp_api_config.json` existe
- O que las variables de entorno están definidas

### Error: "Authentication failed"
- Verifica que el refresh_token es válido
- Regenera el token en Seller Central si expiró

### Error: "Rate limit exceeded"
- El cliente implementa backoff automático
- Espera unos segundos y reintenta

## Integración con FBACalculator

Para usar fees reales de SP-API en lugar de estimaciones:

```python
# En FBACalculator
try:
    sp_client = SPAPIClient()
    fees_data = sp_client.get_product_fees(asin, price, is_fba=True)
    # Usar fees_data en lugar de cálculos estimados
except:
    # Fallback a cálculos estimados
    pass
```
