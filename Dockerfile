############################################
# 1️⃣ BUILD FRONTEND (React)
############################################
FROM node:20-alpine AS build_frontend

WORKDIR /app   

COPY frontend/package*.json ./
RUN npm install --silent

# Copiar el resto del código del frontend
COPY frontend/ ./
RUN npm run build


############################################
# 2️⃣ BUILD BACKEND (Django + dependencias)
############################################
FROM python:3.11-slim-bookworm AS build_backend

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app/backend

# ===========================
# 🔧 Repositorios + dependencias del sistema
# ===========================
RUN set -eux; \
    rm -f /etc/apt/sources.list.d/debian.sources; \
    echo "deb https://deb.debian.org/debian bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list; \
    echo "deb https://deb.debian.org/debian bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list; \
    echo "deb https://deb.debian.org/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list; \
    apt-get update && apt-get install -y curl gnupg apt-transport-https ca-certificates; \
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

# ===========================
# 🐍 Instalar dependencias de Python
# ===========================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===========================
# 📦 Copiar código Django y recolectar estáticos
# ===========================
COPY backend/ .
RUN python manage.py collectstatic --noinput || true


############################################
# 3️⃣ IMAGEN FINAL (Nginx)
############################################
FROM nginx:1.25-alpine AS final

# 📂 Copiar build del frontend (React)
COPY --from=build_frontend /app/build /usr/share/nginx/html  

# Copiar los estáticos de Django al Nginx final
COPY --from=build_backend /app/backend/staticfiles /usr/share/nginx/html/static

# ⚙️ Copiar configuración de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 🌐 Exponer puerto
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
