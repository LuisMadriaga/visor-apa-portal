##############################
# 1️⃣ Etapa base: Python + dependencias del backend
##############################
FROM python:3.11-slim-bookworm AS backend

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app/backend

# 🔧 Configurar repositorios HTTPS (evita error 403) y agregar ODBC de Microsoft
RUN set -eux; \
    # limpiar fuentes conflictivas
    rm -f /etc/apt/sources.list.d/debian.sources; \
    echo "deb https://deb.debian.org/debian bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list; \
    echo "deb https://deb.debian.org/debian bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list; \
    echo "deb https://deb.debian.org/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list; \
    apt-get update && apt-get install -y curl gnupg apt-transport-https ca-certificates; \
    # 🔑 importar llave y repo Microsoft sin apt-key
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft.gpg; \
    echo "deb [signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list; \
    apt-get update; \
    ACCEPT_EULA=Y apt-get install -y \
        msodbcsql17 \
        unixodbc \
        unixodbc-dev \
        libodbc1 \
        gcc g++ \
        libffi-dev \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf2.0-0 \
        libfreetype6 \
        libfontconfig1 \
        shared-mime-info \
        fonts-dejavu \
        fonts-liberation \
        curl; \
    apt-get clean && rm -rf /var/lib/apt/lists/*




# Instalar dependencias del backend
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del backend
COPY backend/ /app/backend/
COPY static ./static

# Generar los estáticos de Django
RUN python backend/manage.py collectstatic --noinput || true


##############################
# 2️⃣ Etapa de build del frontend React (CRA)
##############################
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./
RUN npm run build


##############################
# 3️⃣ Imagen final con Nginx
##############################
FROM nginx:1.25-alpine AS final

# Copiar los archivos estáticos del frontend (CRA usa /build)
COPY --from=frontend /app/build /usr/share/nginx/html

# Copiar configuración de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exponer el puerto 80
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]



