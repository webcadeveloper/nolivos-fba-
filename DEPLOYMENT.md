# NOLIVOS FBA - Gu\u00eda de Deployment a Servidor

## Preparaci\u00f3n antes del deployment

### 1. Requisitos del servidor

- **Sistema Operativo**: Ubuntu 20.04 LTS o superior
- **Python**: 3.9+
- **Node.js**: 18+ y npm
- **RAM**: M\u00ednimo 2GB
- **Disco**: M\u00ednimo 10GB
- **Puertos**: 5000 (backend), 80/443 (frontend con nginx)

### 2. Archivos de configuraci\u00f3n

Se han creado los siguientes archivos de ejemplo:

```
.env.example          # Variables de entorno del backend
frontend/src/environments/environment.ts  # Variables de entorno del frontend
```

---

## Instalaci\u00f3n en Servidor

### PASO 1: Preparar el servidor

```bash
# Actualizar paquetes
sudo apt update && sudo apt upgrade -y

# Instalar dependencias del sistema
sudo apt install -y python3-pip python3-venv nginx git

# Instalar Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verificar versiones
python3 --version
node --version
npm --version
```

### PASO 2: Clonar/Subir el proyecto

Opci\u00f3n A - Usando Git:
```bash
cd /var/www
sudo git clone <tu-repositorio> amz-review-analyzer
sudo chown -R $USER:$USER amz-review-analyzer
```

Opci\u00f3n B - Subir archivos manualmente:
```bash
# Desde tu computadora local, comprimir el proyecto
cd "/mnt/c/Users/Admin/OneDrive - Nolivos Law/Aplicaciones/AMAZON"
tar -czf amz-review-analyzer.tar.gz amz-review-analyzer/

# Subir al servidor usando scp
scp amz-review-analyzer.tar.gz usuario@TU_SERVIDOR_IP:/tmp/

# En el servidor, descomprimir
sudo mkdir -p /var/www
cd /var/www
sudo tar -xzf /tmp/amz-review-analyzer.tar.gz
sudo chown -R $USER:$USER amz-review-analyzer
```

### PASO 3: Configurar Backend (Flask)

```bash
cd /var/www/amz-review-analyzer

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias Python
pip install --upgrade pip
pip install -r requirements.txt

# Crear archivo .env con configuraci\u00f3n del servidor
cp .env.example .env
nano .env
```

Editar `.env` con la IP del servidor:
```env
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=False

DB_PATH=data/opportunities.db

# Reemplazar con la IP/dominio de tu servidor
CORS_ORIGINS=http://TU_SERVIDOR_IP,http://TU_DOMINIO.com

FRONTEND_URL=http://TU_SERVIDOR_IP
```

### PASO 4: Configurar Frontend (Angular)

```bash
cd /var/www/amz-review-analyzer/frontend

# Editar environment.ts con la IP del servidor
nano src/environments/environment.ts
```

Configurar con la IP del servidor:
```typescript
export const environment = {
  production: false,
  apiUrl: 'http://TU_SERVIDOR_IP:5000/api'
};
```

Instalar dependencias y compilar:
```bash
npm install
npm run build
```

### PASO 5: Configurar Nginx

Crear archivo de configuraci\u00f3n:
```bash
sudo nano /etc/nginx/sites-available/nolivos-fba
```

Contenido del archivo nginx:
```nginx
server {
    listen 80;
    server_name TU_SERVIDOR_IP;  # Cambiar por tu IP o dominio

    # Frontend Angular
    root /var/www/amz-review-analyzer/frontend/dist/frontend/browser;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy para el backend
    location /api/ {
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Activar configuraci\u00f3n:
```bash
sudo ln -s /etc/nginx/sites-available/nolivos-fba /etc/nginx/sites-enabled/
sudo nginx -t  # Verificar configuraci\u00f3n
sudo systemctl reload nginx
```

### PASO 6: Crear servicio systemd para el backend

```bash
sudo nano /etc/systemd/system/nolivos-fba-api.service
```

Contenido:
```ini
[Unit]
Description=NOLIVOS FBA API Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/amz-review-analyzer
Environment="PATH=/var/www/amz-review-analyzer/venv/bin"
ExecStart=/var/www/amz-review-analyzer/venv/bin/python api_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Iniciar servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable nolivos-fba-api
sudo systemctl start nolivos-fba-api
sudo systemctl status nolivos-fba-api
```

---

## Verificaci\u00f3n del Deployment

### 1. Verificar Backend
```bash
# Verificar que el servicio est\u00e1 corriendo
sudo systemctl status nolivos-fba-api

# Probar endpoint de salud
curl http://localhost:5000/api/health
```

### 2. Verificar Frontend
```bash
# Verificar nginx
sudo systemctl status nginx

# Abrir en navegador
# http://TU_SERVIDOR_IP
```

### 3. Ver logs
```bash
# Logs del backend
sudo journalctl -u nolivos-fba-api -f

# Logs de nginx
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

---

## Actualizaci\u00f3n de la aplicaci\u00f3n

```bash
cd /var/www/amz-review-analyzer

# Actualizar backend
source venv/bin/activate
git pull  # o subir nuevos archivos
pip install -r requirements.txt
sudo systemctl restart nolivos-fba-api

# Actualizar frontend
cd frontend
npm install
npm run build
sudo systemctl reload nginx
```

---

## Seguridad (Opcional pero recomendado)

### 1. Configurar Firewall
```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 2. Instalar SSL con Let's Encrypt (si tienes dominio)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com
```

---

## Troubleshooting

### Backend no arranca
```bash
# Verificar logs
sudo journalctl -u nolivos-fba-api -n 50

# Verificar permisos
sudo chown -R www-data:www-data /var/www/amz-review-analyzer/data

# Reiniciar servicio
sudo systemctl restart nolivos-fba-api
```

### Frontend muestra error de conexi\u00f3n
```bash
# Verificar que environment.ts tenga la IP correcta
cat frontend/src/environments/environment.ts

# Reconstruir frontend
cd frontend
npm run build
sudo systemctl reload nginx
```

### Error de CORS
- Verificar que CORS_ORIGINS en `.env` incluya la IP/dominio del frontend
- Reiniciar el backend: `sudo systemctl restart nolivos-fba-api`

---

## Comandos \u00fatiles

```bash
# Reiniciar todo
sudo systemctl restart nolivos-fba-api
sudo systemctl reload nginx

# Ver estado
sudo systemctl status nolivos-fba-api
sudo systemctl status nginx

# Ver logs en tiempo real
sudo journalctl -u nolivos-fba-api -f

# Ver base de datos
cd /var/www/amz-review-analyzer
source venv/bin/activate
sqlite3 data/opportunities.db "SELECT COUNT(*) FROM opportunities;"
```
