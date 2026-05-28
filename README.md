# ScrapperInducascos

Scraper en Python para revisar la categoría Shaft Pro de Inducascos cada 6 horas con GitHub Actions y enviar un correo cuando encuentre alguno de los productos buscados.
Ahora usa Playwright para pulsar "Mostrar más" tantas veces como exista antes de extraer los productos visibles.

## Estructura

- scraper.py: lógica de scraping, carga dinámica y envío de correo.
- requirements.txt: dependencias del proyecto.
- .github/workflows/scraper.yml: workflow de GitHub Actions.
- .env.example: plantilla para desarrollo local.

## Ejecución local

1. Copia .env.example a .env y completa la contraseña de aplicación de Gmail.
2. Instala dependencias con pip install -r requirements.txt.
3. Instala Chromium para Playwright con python -m playwright install chromium.
4. Ejecuta python scraper.py.

## GitHub Actions

El workflow se puede ejecutar manualmente desde la pestaña Actions con workflow_dispatch y también queda programado cada 6 horas con cron.

Antes de correrlo por primera vez, crea estos secrets en el repositorio:

- INDUCASCOS_USER_AGENT
- SMTP_HOST
- SMTP_PORT
- SMTP_USERNAME
- SMTP_PASSWORD
- EMAIL_FROM
- EMAIL_TO
- SMTP_USE_TLS
