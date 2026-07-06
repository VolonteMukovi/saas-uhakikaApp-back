FROM python:3.11-slim

# Configuration des variables indispensables pour mysqlclient
ENV MYSQLCLIENT_CFLAGS="-I/usr/include/mysql"
ENV MYSQLCLIENT_LDFLAGS="-L/usr/lib/x86_64-linux-gnu -lmariadb"

# Installation des dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# On copie le fichier des dépendances
COPY requirements.txt .

# FIX : On retire "--upgrade pip" pour éviter le crash lié à Pip 26+
RUN pip install --no-cache-dir -r requirements.txt

# Copie du reste du code du projet
COPY . .

# Exposer le port par défaut
EXPOSE 8000

# Commande finale propre (Format Exec)
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]