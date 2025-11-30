#!/bin/bash

# Script de deployment automático para NOLIVOS FBA
# Uso: ./deploy.sh [production|staging|local]

set -e  # Exit on error

ENV=${1:-production}

echo "═════════════════════════════════════════════════════════"
echo "  🚀 NOLIVOS FBA - Deployment Script"
echo "═════════════════════════════════════════════════════════"
echo ""
echo "Environment: $ENV"
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funciones helper
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Verificar que Docker está instalado
log_info "Verificando Docker..."
if ! command -v docker &> /dev/null; then
    log_error "Docker no está instalado"
    echo "Instala Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose no está instalado"
    echo "Instala Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

log_info "✅ Docker y Docker Compose encontrados"

# 2. Verificar archivo .env
log_info "Verificando variables de entorno..."
if [ ! -f .env ]; then
    log_warn ".env no encontrado, creando desde .env.example"
    cp .env.example .env

    # Generar SECRET_KEY aleatorio
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

    # Reemplazar en .env
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    else
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    fi

    log_info "✅ .env creado con SECRET_KEY aleatorio"
    log_warn "⚠️  IMPORTANTE: Edita .env y configura:"
    log_warn "   - SMTP_* para emails"
    log_warn "   - TELEGRAM_* para notificaciones"
    log_warn "   - Tu dominio en ALLOWED_ORIGINS"

    read -p "Presiona ENTER después de editar .env..."
else
    log_info "✅ .env encontrado"
fi

# 3. Crear directorios necesarios
log_info "Creando directorios..."
mkdir -p data logs ssl backups
chmod 755 data logs backups
log_info "✅ Directorios creados"

# 4. Pull latest code (si es git repo)
if [ -d .git ]; then
    log_info "Actualizando código desde Git..."
    git pull origin main || log_warn "No se pudo hacer git pull (puede que no haya cambios)"
    log_info "✅ Código actualizado"
fi

# 5. Stop containers existentes
log_info "Deteniendo containers existentes..."
docker-compose down || log_warn "No hay containers corriendo"

# 6. Build images
log_info "Building Docker images..."
docker-compose build --no-cache
log_info "✅ Images built"

# 7. Start services
log_info "Iniciando servicios..."

if [ "$ENV" = "production" ]; then
    # Producción: con nginx
    docker-compose --profile with-nginx up -d
else
    # Staging/local: sin nginx
    docker-compose up -d
fi

log_info "✅ Servicios iniciados"

# 8. Wait for services to be ready
log_info "Esperando que los servicios estén listos..."
sleep 10

# 9. Health checks
log_info "Verificando health de los servicios..."

# Check Splash
if curl -f http://localhost:8050/ > /dev/null 2>&1; then
    log_info "✅ Splash está funcionando"
else
    log_error "❌ Splash no responde"
    docker-compose logs splash
    exit 1
fi

# Check Flask app
if curl -f http://localhost:4994/ > /dev/null 2>&1; then
    log_info "✅ Flask app está funcionando"
else
    log_error "❌ Flask app no responde"
    docker-compose logs app
    exit 1
fi

# 10. Mostrar status
log_info "Estado de los containers:"
docker-compose ps

# 11. Mostrar logs (últimas 50 líneas)
echo ""
log_info "Últimos logs de la app:"
docker-compose logs --tail=50 app

echo ""
echo "═════════════════════════════════════════════════════════"
echo -e "  ${GREEN}✅ DEPLOYMENT COMPLETADO${NC}"
echo "═════════════════════════════════════════════════════════"
echo ""
echo "Servicios disponibles:"
echo "  - Flask App: http://localhost:4994"
echo "  - Splash: http://localhost:8050"

if [ "$ENV" = "production" ]; then
    echo "  - Nginx: http://localhost:80 (y https://localhost:443)"
fi

echo ""
echo "Comandos útiles:"
echo "  - Ver logs:        docker-compose logs -f"
echo "  - Restart:         docker-compose restart"
echo "  - Stop:            docker-compose down"
echo "  - Ver recursos:    docker stats"
echo ""
echo "🎉 ¡Listo para scrapear Amazon!"
echo ""
