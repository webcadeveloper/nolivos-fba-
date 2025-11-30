# Dockerfile para HECTOR FBA en producción
FROM python:3.10-slim

# Establecer directorio de trabajo
WORKDIR /app

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements (usar pip version)
COPY requirements-pip.txt requirements.txt

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p data logs

# Exponer puerto
EXPOSE 4994

# Comando de inicio
CMD ["gunicorn", "--bind", "0.0.0.0:4994", "--workers", "4", "--timeout", "120", "app:app"]
