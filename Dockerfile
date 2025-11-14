############################################
# 1️⃣ BUILD FRONTEND (React)
############################################
FROM node:20-bullseye AS build_frontend   
ENV TZ=America/Santiago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# Dependencias necesarias
RUN sed -i 's|http://deb.debian.org/debian|https://deb.debian.org/debian|g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y python3 make g++ bash && \
    rm -rf /var/lib/apt/lists/*


# Configuración robusta NPM (evita tus errores de TLS)
RUN npm config set registry https://registry.npmjs.org \
    && npm config set strict-ssl false \
    && npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm config set prefer-online true \
    && npm config set progress=false \
    && npm config set fund=false \
    && npm config set audit=false

COPY frontend/package*.json ./ 
RUN npm install --silent

COPY frontend/ ./

ARG REACT_APP_API_BASE=/visor_apa_portal_2/api
ENV REACT_APP_API_BASE=$REACT_APP_API_BASE

RUN npm run build



############################################
# 2️⃣ BUILD BACKEND (Django)
############################################
FROM python:3.11 AS build_backend

# 🔹 Configurar repositorios oficiales y limpiar duplicados
RUN echo "deb https://deb.debian.org/debian bookworm main" > /etc/apt/sources.list \
    && echo "deb https://security.debian.org/debian-security bookworm-security main" >> /etc/apt/sources.list \
    && echo "deb https://deb.debian.org/debian bookworm-updates main" >> /etc/apt/sources.list \
    && rm -f /etc/apt/sources.list.d/debian.sources

# 🔹 Instalar dependencias del sistema + driver ODBC 17 (sin usar apt-key)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    ca-certificates \
    unixodbc \
    unixodbc-dev \
    libodbc1 \
    libpq-dev \
    gcc \
    g++ \
    libffi-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libfreetype6 \
    libfontconfig1 \
    shared-mime-info \
    fonts-liberation \
 && mkdir -p /etc/apt/keyrings \
 && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg \
 && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
 && rm -rf /var/lib/apt/lists/*


WORKDIR /app/backend

# 🔹 Copiar y preparar el proyecto
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt && pip install gunicorn

COPY backend/ .
COPY --from=build_frontend /app/build ./backend/static/visor_apa_portal_2

ENV DJANGO_SETTINGS_MODULE=backend.settings

# Crear la carpeta static si no existe
RUN mkdir -p /app/backend/static

# Recolectar archivos estáticos (evitar error si no hay migraciones)
RUN python manage.py collectstatic --noinput || true
RUN python backend/manage.py collectstatic --noinput || true


############################################
# 3️⃣ IMAGEN FINAL (Nginx)
############################################
FROM nginx:1.25-alpine AS final

COPY --from=build_frontend /app/build /usr/share/nginx/html
COPY --from=build_backend /app/backend/static /usr/share/nginx/html/static

# Copiar estáticos locales al contenedor
COPY backend/backend/static /app/backend/static

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
