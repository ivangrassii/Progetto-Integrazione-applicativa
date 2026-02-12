# Usa un'immagine leggera di Python
FROM python:3.9-slim

# Imposta la cartella di lavoro nel container
WORKDIR /app

# Copia il file delle dipendenze e installale
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del progetto
COPY . .

# Espone la porta che usa la tua app Flask
EXPOSE 5001

# Comando per avviare l'app
CMD ["python", "app.py"]