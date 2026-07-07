FROM python:3.11-slim

# Définition du dossier de travail dans le conteneur
WORKDIR /app

# Copie du fichier des dépendances nettoyé
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie de tout le code source du projet dans le conteneur
COPY . .

# Répertoires statiques / médias + collecte CSS/JS admin
RUN mkdir -p /app/staticfiles /app/media
RUN python manage.py collectstatic --noinput

# Exposition du port interne utilisé par Gunicorn
EXPOSE 8000

# Commande finale : migrations puis Gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]