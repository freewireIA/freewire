"""
FREE WIRE — Agente 2: Curador de Noticias
==========================================
Lee freewire_raw.json, elimina duplicados, rankea por relevancia
y guarda freewire_curated.json listo para el Agente 3 (Redactor).

Instalación:
    pip install apscheduler

Uso:
    python freewire_agent2_curator.py
"""

import json
import logging
import re
import os
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("freewire.curator")

INPUT_FILE  = "freewire_raw.json"
OUTPUT_FILE = "freewire_curated.json"
INTERVAL_HOURS = 2
MAX_OUTPUT = 20  # Máximo de noticias en la edición diaria

# ─── PESOS POR CATEGORÍA ────────────────────────────────────────────────────

CATEGORY_WEIGHT = {
    "global":      1.5,
    "geopolitics": 1.4,
    "economy":     1.3,
    "defense":     1.2,
    "middleeast":  1.2,
    "asia":        1.1,
    "us":          1.1,
    "science":     1.0,
    "tech":        1.0,
    "crypto":      0.8,
}

# ─── KEYWORDS DE ALTA RELEVANCIA ────────────────────────────────────────────

HIGH_RELEVANCE_KEYWORDS = [
    "war", "ceasefire", "attack", "missile", "nuclear", "crisis",
    "election", "president", "congress", "senate", "vote",
    "recession", "inflation", "fed", "rate", "gdp", "crash",
    "earthquake", "flood", "hurricane", "disaster",
    "assassination", "coup", "protest", "sanctions",
    "ai", "artificial intelligence", "breakthrough",
    "pandemic", "outbreak", "virus",
]

# ─── FUNCIONES ──────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """Normaliza texto para comparación: minúsculas, sin puntuación."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def word_overlap(a: str, b: str) -> float:
    """Score de similitud entre dos títulos basado en palabras compartidas."""
    stopwords = {"the", "a", "an", "in", "on", "at", "to", "of", "and",
                 "or", "is", "are", "was", "were", "for", "with", "as"}
    words_a = set(normalize(a).split()) - stopwords
    words_b = set(normalize(b).split()) - stopwords
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def deduplicate(articles: list) -> list:
    """Elimina artículos duplicados o muy similares (Jaccard > 0.55)."""
    unique = []
    for article in articles:
        is_dup = False
        for kept in unique:
            if word_overlap(article["title"], kept["title"]) > 0.55:
                # Si es duplicado, incrementamos el conteo de fuentes del que ya está
                kept["source_count"] = kept.get("source_count", 1) + 1
                is_dup = True
                break
        if not is_dup:
            article["source_count"] = 1
            unique.append(article)
    return unique


def score_article(article: dict) -> float:
    """
    Calcula score de relevancia (0-100) basado en:
    - Frescura (hasta 40 pts)
    - Cobertura múltiple de fuentes (hasta 30 pts)
    - Keywords de alta relevancia (hasta 20 pts)
    - Peso por categoría (multiplicador)
    """
    score = 0.0

    # 1. Frescura — artículos de las últimas 6hs valen más
    try:
        pub = datetime.fromisoformat(article["published"])
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
        if age_hours <= 2:
            score += 40
        elif age_hours <= 6:
            score += 30
        elif age_hours <= 12:
            score += 20
        elif age_hours <= 24:
            score += 10
    except Exception:
        score += 5

    # 2. Cobertura múltiple — si más fuentes cubren lo mismo, es importante
    source_count = article.get("source_count", 1)
    score += min(source_count * 10, 30)

    # 3. Keywords de alta relevancia en título o summary
    text = normalize(article.get("title", "") + " " + article.get("summary", ""))
    keyword_hits = sum(1 for kw in HIGH_RELEVANCE_KEYWORDS if kw in text)
    score += min(keyword_hits * 5, 20)

    # 4. Multiplicador por categoría
    category = article.get("category", "global")
    multiplier = CATEGORY_WEIGHT.get(category, 1.0)
    score *= multiplier

    return round(score, 2)


def balance_categories(articles: list, max_total: int) -> list:
    """
    Selecciona artículos asegurando diversidad de categorías.
    Ninguna categoría ocupa más del 40% de la edición.
    """
    max_per_category = max(1, int(max_total * 0.4))
    category_counts = {}
    selected = []

    for article in articles:
        cat = article.get("category", "global")
        count = category_counts.get(cat, 0)
        if count < max_per_category:
            selected.append(article)
            category_counts[cat] = count + 1
        if len(selected) >= max_total:
            break

    return selected


def curate():
    """Ciclo completo: leer, deduplicar, rankear, balancear y guardar."""
    log.info("═══ FREE WIRE — Agente 2 iniciando curaduría ═══")

    # Leer raw
    if not os.path.exists(INPUT_FILE):
        log.warning(f"{INPUT_FILE} no encontrado. ¿Corrió el Agente 1?")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    log.info(f"Artículos crudos: {len(articles)}")

    # Deduplicar
    articles = deduplicate(articles)
    log.info(f"Tras deduplicación: {len(articles)}")

    # Scoring
    for article in articles:
        article["score"] = score_article(article)

    # Ordenar por score descendente
    articles.sort(key=lambda x: x["score"], reverse=True)

    # Balancear categorías y tomar top MAX_OUTPUT
    selected = balance_categories(articles, MAX_OUTPUT)
    log.info(f"Edición final: {len(selected)} artículos seleccionados")

    for i, a in enumerate(selected, 1):
        log.info(f"  {i:2}. [{a['category'].upper():12} | score: {a['score']:5.1f} | sources: {a.get('source_count',1)}] {a['title'][:70]}")

    # Guardar output
    output = {
        "curated_at":    datetime.now(timezone.utc).isoformat(),
        "total_raw":     len(data.get("articles", [])),
        "total_unique":  len(articles),
        "total_edition": len(selected),
        "articles":      selected,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log.info(f"Guardado en {OUTPUT_FILE}")
    log.info("═══ Curaduría completa ═══")


# ─── SCHEDULER ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    curate()

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(curate, "interval", hours=INTERVAL_HOURS)
    log.info(f"Scheduler activo — próxima curaduría en {INTERVAL_HOURS}hs")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Agente detenido.")
