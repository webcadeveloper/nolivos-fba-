#!/bin/bash
# Script para arrancar el backend Flask API

echo "=========================================="
echo "NOLIVOS FBA - Iniciando Backend API"
echo "=========================================="
echo ""

cd "/mnt/c/Users/Admin/OneDrive - Nolivos Law/Aplicaciones/AMAZON/amz-review-analyzer"

# Activar virtualenv
source venv/bin/activate

# Matar procesos anteriores en puerto 5000
echo "Limpiando puerto 5000..."
fuser -k 5000/tcp 2>/dev/null || true
sleep 2

# Arrancar API
echo ""
echo "Arrancando Flask API en puerto 5000..."
echo ""
python api_app.py
