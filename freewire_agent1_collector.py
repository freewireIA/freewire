"""
FREE WIRE — Agente 1: Recolector de Noticias
=============================================
Scrapea RSS de 25 fuentes internacionales cada 2 horas.
Guarda los resultados en freewire_raw.json para el Agente 2 (Curador).

Instalación:
    pip install feedparser apscheduler requests

Uso:
    python freewire_agent1_collector.py
"""

import feedparser
import json
import logging
import os
from datetime import datetime, timezone
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("freewire.collector")

OUTPUT_FILE = "freewire_raw.json"
INTERVAL_HOURS = 12

# ─── FUENTES RSS ────────────────────────────────────────────────────────────

SOURCES = [
    # Agencias globales
    {"name": "Reuters",         "url": "https://feeds.reuters.com/reuters/topNews",             "category": "global"},
    {"name": "AP News",         "url": "https://rsshub.app/apnews/topics/apf-topnews",          "category": "global"},
    {"name": "BBC World",       "url": "http://feeds.bbci.co.uk/news/world/rss.xml",            "category": "global"},
    {"name": "Al Jazeera",      "url": "https://www.aljazeera.com/xml/rss/all.xml",             "category": "global"},
    {"name": "France 24",       "url": "https://www.france24.com/en/rss",                       "category": "global"},
    {"name": "Deutsche Welle",  "url": "https://rss.dw.com/rdf/rss-en-all",                     "category": "global"},
    {"name": "Euronews",        "url": "https://www.euronews.com/rss?format=mrss&level=theme&name=news", "category": "global"},

    # Medios anglosajones
    {"name": "The Guardian",    "url": "https://www.theguardian.com/world/rss",                 "category": "global"},
    {"name": "NPR",             "url": "https://feeds.npr.org/1001/rss.xml",                    "category": "us"},
    {"name": "Axios",           "url": "https://api.axios.com/feed/",                           "category": "us"},
    {"name": "Politico",        "url": "https://rss.politico.com/politics-news.xml",            "category": "us"},

    # Economía y finanzas
    {"name": "Bloomberg",       "url": "https://feeds.bloomberg.com/markets/news.rss",          "category": "economy"},
    {"name": "Financial Times", "url": "https://www.ft.com/rss/home",                           "category": "economy"},
    {"name": "The Economist",   "url": "https://www.economist.com/latest/rss.xml",              "category": "economy"},

    # Asia y Medio Oriente
    {"name": "SCMP",            "url": "https://www.scmp.com/rss/91/feed",                      "category": "asia"},
    {"name": "Times of India",  "url": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "category": "asia"},
    {"name": "Haaretz",         "url": "https://www.haaretz.com/srv/haaretz-en-rss.xml",        "category": "middleeast"},

    # Geopolítica y defensa
    {"name": "Foreign Policy",  "url": "https://foreignpolicy.com/feed/",                      "category": "geopolitics"},
    {"name": "Defense News",    "url": "https://www.defensenews.com/arc/outboundfeeds/rss/",    "category": "defense"},

    # Tecnología
    {"name": "TechCrunch",      "url": "https://techcrunch.com/feed/",                         "category": "tech"},
    {"name": "Wired",           "url": "https://www.wired.com/feed/rss",                        "category": "tech"},
    {"name": "Ars Technica",    "url": "https://feeds.arstechnica.com/arstechnica/index",       "category": "tech"},

    # Ciencia y clima
    {"name": "Nature News",     "url": "https://www.nature.com/nature.rss",                    "category": "science"},
    {"name": "BBC Science",     "url": "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "category": "science"},

    # Crypto / Finanzas alternativas
    {"name": "CoinDesk",        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",       "category": "crypto"},
]

# ─── FUNCIONES ──────────────────────────────────────────────────────────────

def parse_date(entry):
    """Extrae la fecha del artículo en formato ISO 8601."""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def fetch_source(source: dict) -> list:
    """Parsea un feed RSS y devuelve una lista de artículos limpios."""
    articles = []
    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries[:15]:  # máx 15 artículos por fuente
            title = getattr(entry, "title", "").strip()
            summary = getattr(entry, "summary", "").strip()
            link = getattr(entry, "link", "").strip()

            if not title or not link:
                continue

            articles.append({
                "title":     title,
                "summary":   summary[:500] if summary else "",
                "url":       link,
                "source":    source["name"],
                "category":  source["category"],
                "published": parse_date(entry),
            })

        log.info(f"[OK] {source['name']}: {len(articles)} artículos")
    except Exception as e:
        log.warning(f"[FAIL] {source['name']}: {e}")

    return articles


def collect_all() -> list:
    """Recorre todas las fuentes y devuelve artículos combinados."""
    all_articles = []
    for source in SOURCES:
        all_articles.extend(fetch_source(source))
    log.info(f"Total recolectado: {len(all_articles)} artículos de {len(SOURCES)} fuentes")
    return all_articles


def save(articles: list):
    """Guarda los artículos en JSON con metadata de la corrida."""
    output = {
        "run_at":        datetime.now(timezone.utc).isoformat(),
        "total":         len(articles),
        "sources_count": len(SOURCES),
        "articles":      articles,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    log.info(f"Guardado en {OUTPUT_FILE}")


def run():
    """Ciclo completo: recolectar y guardar."""
    log.info("═══ FREE WIRE — Agente 1 iniciando corrida ═══")
    articles = collect_all()
    save(articles)
    log.info("═══ Corrida completa ═══")


# ─── SCHEDULER ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run()  # Correr inmediatamente al iniciar

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run, "interval", hours=INTERVAL_HOURS)
    log.info(f"Scheduler activo — próxima corrida en {INTERVAL_HOURS}hs")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Agente detenido.")
