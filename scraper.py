import os
import smtplib
import sys
from email.mime.text import MIMEText

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - only needed for local development
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()


URL = "https://www.inducascos.com/repuestos/shaft-pro?map=c,b"
KEYWORDS = [
    "Shaft Pro 343 DV",
    "SHPRO-343DV",
    "Tapizado Shaft Pro 343 DV",
]

USER_AGENT = os.getenv("INDUCASCOS_USER_AGENT", "Mozilla/5.0")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USERNAME")
SMTP_PASS = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"


def load_full_page_html() -> str:
    """Abre la página y pulsa 'Mostrar más' hasta que ya no exista."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1440, "height": 2200},
        )
        page = context.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)

        while True:
            button = page.get_by_role("button", name="Mostrar más")
            try:
                if button.count() == 0:
                    break

                button.first.click(timeout=5000)
                page.wait_for_load_state("networkidle", timeout=30000)
                page.wait_for_timeout(1000)
            except PlaywrightTimeoutError:
                break

        html = page.content()
        context.close()
        browser.close()
        return html


def scrape() -> tuple[list[str], list[str]]:
    """Devuelve las keywords encontradas y los productos visibles."""
    html = load_full_page_html()
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text()

    found_keywords = [keyword for keyword in KEYWORDS if keyword.lower() in page_text.lower()]
    visible_products = extract_products(soup)

    return found_keywords, visible_products


def extract_products(soup: BeautifulSoup) -> list[str]:
    """Extrae los nombres visibles de productos dentro de la sección."""
    products: list[str] = []

    for node in soup.select("article .vtex-product-summary-2-x-productBrand"):
        product_name = " ".join(node.get_text(" ", strip=True).split())
        if product_name and product_name not in products:
            products.append(product_name)

    if products:
        return products

    for node in soup.select("article"):
        text = " ".join(node.get_text(" ", strip=True).split())
        if text and text not in products:
            products.append(text)

    return products


def send_email(subject: str, body: str) -> None:
    """Envía un correo usando SMTP con STARTTLS."""
    if not all([SMTP_USER, SMTP_PASS, EMAIL_FROM, EMAIL_TO]):
        raise ValueError("Faltan variables de entorno para el correo")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        if USE_TLS:
            server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())


def build_email(found_keywords: list[str], visible_products: list[str]) -> tuple[str, str]:
    """Construye el asunto y cuerpo del correo según el resultado."""
    if found_keywords:
        subject = "✅ [Inducascos] Productos 343 DV encontrados"
        body = (
            f"Se encontraron los siguientes productos en {URL}:\n\n"
            + "\n".join(f"- {keyword}" for keyword in found_keywords)
            + "\n\nProductos visibles en la sección:\n"
            + "\n".join(f"- {product}" for product in visible_products)
            + f"\n\nVisita la página: {URL}"
        )
    else:
        subject = "❌ [Inducascos] Productos 343 DV no disponibles aún"
        body = (
            f"Ninguna de las siguientes palabras clave fue encontrada en {URL}:\n\n"
            + "\n".join(f"- {keyword}" for keyword in KEYWORDS)
            + "\n\nProductos visibles en la sección:\n"
            + "\n".join(f"- {product}" for product in visible_products)
            + "\n\nSe revisará nuevamente en 6 horas."
        )

    return subject, body


if __name__ == "__main__":
    try:
        found_keywords, visible_products = scrape()
    except Exception as error:
        subject = "⚠️ [Inducascos] Error en el scraper"
        body = f"El scraper falló al intentar acceder a {URL}.\n\nError: {error}"
        print(f"ERROR al scrapear: {error}", file=sys.stderr)
        try:
            send_email(subject, body)
        except Exception as mail_error:
            print(f"ERROR al enviar correo: {mail_error}", file=sys.stderr)
            sys.exit(1)
        sys.exit(1)

    subject, body = build_email(found_keywords, visible_products)

    try:
        send_email(subject, body)
        print(f"Correo enviado: {subject}")
        print(f"Keywords encontradas: {found_keywords if found_keywords else 'ninguna'}")
    except Exception as error:
        print(f"ERROR al enviar correo: {error}", file=sys.stderr)
        sys.exit(1)