# AGENTS.md — Inducascos Shaft Pro Scraper

## Propósito
Script Python que raspa la página de repuestos Shaft Pro de Inducascos cada 6 horas (via GitHub Actions), busca productos específicos por palabras clave, y envía un correo de notificación indicando si los encontró o no.

---

## Stack
- **Lenguaje:** Python 3.11
- **Scraping:** `requests` + `beautifulsoup4`
- **Notificaciones:** `smtplib` (Gmail SMTP con STARTTLS, puerto 587)
- **Scheduler:** GitHub Actions cron
- **Repositorio:** GitHub (puede ser privado)

---

## Estructura de archivos a crear

```
inducascos-scraper/
├── .github/
│   └── workflows/
│       └── scraper.yml
├── scraper.py
├── requirements.txt
└── .env               # Solo para desarrollo local — NO subir a GitHub
```

---

## Variables de entorno

Estas variables deben existir en el entorno de ejecución.  
En GitHub Actions se configuran como **Repository Secrets** (Settings → Secrets and variables → Actions).  
En local se cargan desde `.env` usando `python-dotenv`.

| Variable           | Valor                              |
|--------------------|------------------------------------|
| `INDUCASCOS_USER_AGENT` | `Mozilla/5.0`                 |
| `SMTP_HOST`        | `smtp.gmail.com`                   |
| `SMTP_PORT`        | `587`                              |
| `SMTP_USERNAME`    | `sebasascuestion123@gmail.com`     |
| `SMTP_PASSWORD`    | `weqj uvep xxgt nrtk`              |
| `EMAIL_FROM`       | `sebasascuestion123@gmail.com`     |
| `EMAIL_TO`         | `sebasascuestion123@gmail.com`     |
| `SMTP_USE_TLS`     | `true`                             |

> **Nota:** `SMTP_PASSWORD` es una contraseña de aplicación de Gmail (no la contraseña de la cuenta). Se genera en myaccount.google.com/apppasswords con verificación en dos pasos activa.

---

## Página objetivo

```
URL = "https://www.inducascos.com/repuestos/shaft-pro?map=c,b"
```

### Estructura HTML relevante
La página es una tienda VTEX. Los productos se renderizan como tarjetas con esta estructura:

```html
<article class="vtex-product-summary-2-x-element ...">
  <div class="vtex-product-summary-2-x-nameContainer">
    <span class="vtex-product-summary-2-x-productBrand">Nombre del producto</span>
  </div>
  <a href="/url-del-producto/p">...</a>
</article>
```

El texto completo de la página (incluyendo nombres de productos) es accesible con `soup.get_text()`.  
La página carga los productos en el HTML inicial — **no requiere JavaScript / Selenium**.

### Productos actualmente en catálogo (mayo 2026)
Para referencia, estos son los productos presentes al momento de escribir este documento:
- Repuesto Visor SHAFT PRO SHPRO-620C EVO
- Repuesto Visor SHAFT PRO SHPRO 610 DV EVO
- Repuesto Tapizado SHAFT PRO SHPRO-620C EVO
- Repuesto Tapizado SHAFT PRO SHPRO 610 DV EVO
- Repuesto Visor SHAFT PRO SHPRO-612 DV EVO
- Repuesto Visor SHAFT PRO 610DV
- Repuesto Spoiler SHAFT PRO SHPRO 610 DV EVO
- Repuesto Spoiler SHAFT PRO SHPRO-620C EVO
- Repuesto Visor SHAFT PRO SHPRO-240DV

**Los productos buscados (343 DV) NO están actualmente en catálogo.** El scraper debe alertar cuando aparezcan.

---

## Palabras clave a buscar

El scraper debe detectar cualquiera de estas cadenas (case-insensitive) en el texto de la página:

```python
KEYWORDS = [
    "Shaft Pro 343 DV",
    "SHPRO-343DV",
    "Tapizado Shaft Pro 343 DV",
]
```

Se considera **encontrado** si AL MENOS UNA keyword está presente en el texto de la página.

---

## Lógica del scraper (`scraper.py`)

### Flujo principal
1. Cargar variables de entorno (desde `.env` en local, desde secrets en CI).
2. Hacer GET a la URL con el User-Agent configurado y timeout de 15 segundos.
3. Parsear el HTML con BeautifulSoup.
4. Extraer el texto completo con `soup.get_text()`.
5. Buscar cada keyword (case-insensitive) en el texto.
6. Construir el resultado: lista de keywords encontradas (puede estar vacía).
7. Enviar correo con el resultado (encontrado o no encontrado).
8. Imprimir resumen en stdout para los logs de GitHub Actions.

### Manejo de errores
- Si el GET falla (timeout, error HTTP), enviar correo de error con el motivo.
- Si el envío de correo falla, imprimir el error en stderr y salir con código 1.
- Usar `try/except` en ambos bloques críticos.

### Código completo de `scraper.py`

```python
import os
import smtplib
import sys
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv  # Solo para local; en CI las vars ya están en el entorno

load_dotenv()  # No hace nada si no existe .env (seguro en CI)

# ── Configuración ────────────────────────────────────────────────────────────
URL = "https://www.inducascos.com/repuestos/shaft-pro?map=c,b"
KEYWORDS = [
    "Shaft Pro 343 DV",
    "SHPRO-343DV",
    "Tapizado Shaft Pro 343 DV",
]

USER_AGENT  = os.getenv("INDUCASCOS_USER_AGENT", "Mozilla/5.0")
SMTP_HOST   = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER   = os.getenv("SMTP_USERNAME")
SMTP_PASS   = os.getenv("SMTP_PASSWORD")
EMAIL_FROM  = os.getenv("EMAIL_FROM")
EMAIL_TO    = os.getenv("EMAIL_TO")
USE_TLS     = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
# ─────────────────────────────────────────────────────────────────────────────


def scrape() -> list[str]:
    """Devuelve la lista de keywords encontradas en la página."""
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(URL, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text()

    found = [kw for kw in KEYWORDS if kw.lower() in page_text.lower()]
    return found


def send_email(subject: str, body: str) -> None:
    """Envía un correo usando SMTP con STARTTLS."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        if USE_TLS:
            server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())


def build_email(found_keywords: list[str]) -> tuple[str, str]:
    """Construye el asunto y cuerpo del correo según resultado."""
    if found_keywords:
        subject = "✅ [Inducascos] Productos 343 DV encontrados"
        body = (
            f"Se encontraron los siguientes productos en {URL}:\n\n"
            + "\n".join(f"  • {kw}" for kw in found_keywords)
            + f"\n\nVisita la página: {URL}"
        )
    else:
        subject = "❌ [Inducascos] Productos 343 DV no disponibles aún"
        body = (
            f"Ninguna de las siguientes palabras clave fue encontrada en {URL}:\n\n"
            + "\n".join(f"  • {kw}" for kw in KEYWORDS)
            + f"\n\nSe revisará nuevamente en 6 horas."
        )
    return subject, body


if __name__ == "__main__":
    try:
        found = scrape()
    except Exception as e:
        subject = "⚠️ [Inducascos] Error en el scraper"
        body    = f"El scraper falló al intentar acceder a {URL}.\n\nError: {e}"
        print(f"ERROR al scrapear: {e}", file=sys.stderr)
        try:
            send_email(subject, body)
        except Exception as mail_err:
            print(f"ERROR al enviar correo: {mail_err}", file=sys.stderr)
        sys.exit(1)

    subject, body = build_email(found)

    try:
        send_email(subject, body)
        print(f"Correo enviado: {subject}")
    except Exception as e:
        print(f"ERROR al enviar correo: {e}", file=sys.stderr)
        sys.exit(1)
```

---

## `requirements.txt`

```
requests==2.32.3
beautifulsoup4==4.12.3
python-dotenv==1.0.1
```

---

## `.env` (solo desarrollo local — agregar a `.gitignore`)

```dotenv
INDUCASCOS_USER_AGENT=Mozilla/5.0
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sebasascuestion123@gmail.com
SMTP_PASSWORD=weqj uvep xxgt nrtk
EMAIL_FROM=sebasascuestion123@gmail.com
EMAIL_TO=sebasascuestion123@gmail.com
SMTP_USE_TLS=true
```

---

## `.github/workflows/scraper.yml`

```yaml
name: Inducascos Shaft Pro Scraper

on:
  schedule:
    - cron: "0 */6 * * *"   # Cada 6 horas: 00:00, 06:00, 12:00, 18:00 UTC
  workflow_dispatch:          # Ejecución manual desde la pestaña Actions

jobs:
  scrape:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repositorio
        uses: actions/checkout@v4

      - name: Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Instalar dependencias
        run: pip install -r requirements.txt

      - name: Ejecutar scraper
        run: python scraper.py
        env:
          INDUCASCOS_USER_AGENT: ${{ secrets.INDUCASCOS_USER_AGENT }}
          SMTP_HOST:             ${{ secrets.SMTP_HOST }}
          SMTP_PORT:             ${{ secrets.SMTP_PORT }}
          SMTP_USERNAME:         ${{ secrets.SMTP_USERNAME }}
          SMTP_PASSWORD:         ${{ secrets.SMTP_PASSWORD }}
          EMAIL_FROM:            ${{ secrets.EMAIL_FROM }}
          EMAIL_TO:              ${{ secrets.EMAIL_TO }}
          SMTP_USE_TLS:          ${{ secrets.SMTP_USE_TLS }}
```

---

## Secrets en GitHub

Ir a: **Repositorio → Settings → Secrets and variables → Actions → New repository secret**

Crear un secret por cada variable del bloque de `.env`:

| Nombre del secret          | Valor                         |
|---------------------------|-------------------------------|
| `INDUCASCOS_USER_AGENT`   | `Mozilla/5.0`                 |
| `SMTP_HOST`               | `smtp.gmail.com`              |
| `SMTP_PORT`               | `587`                         |
| `SMTP_USERNAME`           | `sebasascuestion123@gmail.com`|
| `SMTP_PASSWORD`           | `weqj uvep xxgt nrtk`         |
| `EMAIL_FROM`              | `sebasascuestion123@gmail.com`|
| `EMAIL_TO`                | `sebasascuestion123@gmail.com`|
| `SMTP_USE_TLS`            | `true`                        |

---

## Pasos para desplegar

1. Crear repositorio en GitHub (puede ser privado).
2. Subir todos los archivos respetando la estructura indicada.
3. Agregar los 8 secrets listados arriba.
4. Ir a la pestaña **Actions** y ejecutar manualmente con **"Run workflow"** para verificar que funciona.
5. El cron se activará automáticamente cada 6 horas.

> **Nota:** GitHub Actions puede tener un retraso de hasta ~10 minutos en crons con repositorios inactivos. Es normal.

---

## Prueba local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar (requiere el archivo .env en la raíz)
python scraper.py
```

---

## Comportamiento esperado

| Situación | Asunto del correo |
|---|---|
| Keyword encontrada | `✅ [Inducascos] Productos 343 DV encontrados` |
| Ninguna keyword encontrada | `❌ [Inducascos] Productos 343 DV no disponibles aún` |
| Error de red o HTTP | `⚠️ [Inducascos] Error en el scraper` |

---

## Limitaciones conocidas

- La página Inducascos usa VTEX y renderiza el catálogo inicial en HTML estático, por lo que `requests` + `bs4` es suficiente. Si en el futuro los productos se cargan dinámicamente via JavaScript (XHR/fetch), será necesario migrar a Playwright o Selenium.
- GitHub Actions no garantiza ejecución exacta en el minuto del cron; puede haber demoras de hasta 15 minutos.
- Los crons de GitHub Actions se pausan automáticamente si el repositorio no tiene actividad en **60 días**. Para reactivarlo, hacer cualquier push o ejecutar el workflow manualmente.
