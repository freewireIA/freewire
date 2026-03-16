"""
FREE WIRE — Agente 3: Redactor (powered by Claude)
====================================================
Lee freewire_curated.json, usa Claude API para redactar
cada noticia en formato Free Wire y guarda freewire_edition.json
listo para publicar en Telegram y newsletter.

Instalación:
    pip install anthropic apscheduler

Uso:
    python freewire_agent3_writer.py

Variables de entorno requeridas:
    ANTHROPIC_API_KEY
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from anthropic import Anthropic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("freewire.writer")

INPUT_FILE  = "freewire_curated.json"
OUTPUT_FILE = "freewire_edition.json"

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ─── PROMPT EDITORIAL ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the editor of FREE WIRE, an AI-powered news outlet with one mission: 
deliver the world's most important news with zero ideological bias, zero agenda, and maximum clarity.

FREE WIRE editorial rules:
- Never editorialize. Report facts only.
- No adjectives that carry political weight (e.g. "controversial", "radical", "far-right", "far-left")
- Always cite the original source
- Write for a global English-speaking audience
- Be concise and direct — no filler words
- Format: headline + 3 bullet points + one-line source attribution

Tone: authoritative, neutral, precise. Think Reuters meets a sharp newsletter."""

def write_article(article: dict) -> dict:
    """Usa Claude para redactar una noticia en formato Free Wire."""

    user_prompt = f"""Write a FREE WIRE news brief for this article:

Title: {article['title']}
Summary: {article.get('summary', 'No summary available')}
Source: {article['source']}
Category: {article['category']}
URL: {article['url']}

Format your response EXACTLY like this:
HEADLINE: [punchy, neutral, max 12 words]
• [Key fact 1 — most important development]
• [Key fact 2 — context or cause]
• [Key fact 3 — impact or what happens next]
SOURCE: {article['source']} | {article['url']}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        content = response.content[0].text.strip()

        # Parsear el output estructurado
        lines = content.split("\n")
        headline = ""
        bullets = []
        source_line = ""

        for line in lines:
            line = line.strip()
            if line.startswith("HEADLINE:"):
                headline = line.replace("HEADLINE:", "").strip()
            elif line.startswith("•"):
                bullets.append(line)
            elif line.startswith("SOURCE:"):
                source_line = line.replace("SOURCE:", "").strip()

        return {
            "headline":    headline,
            "bullets":     bullets,
            "source_line": source_line,
            "category":    article["category"],
            "score":       article.get("score", 0),
            "url":         article["url"],
            "raw":         content,
        }

    except Exception as e:
        log.warning(f"Error redactando '{article['title']}': {e}")
        return None


def write_all():
    """Lee el curated, redacta todos los artículos y guarda la edición."""
    log.info("═══ FREE WIRE — Agente 3 iniciando redacción ═══")

    if not os.path.exists(INPUT_FILE):
        log.warning(f"{INPUT_FILE} no encontrado. ¿Corrió el Agente 2?")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    log.info(f"Artículos a redactar: {len(articles)}")

    edition = []
    for i, article in enumerate(articles, 1):
        log.info(f"Redactando {i}/{len(articles)}: {article['title'][:60]}...")
        result = write_article(article)
        if result:
            edition.append(result)
            log.info(f"  OK: {result['headline']}")
        time.sleep(0.5)  # Rate limit suave

    # Guardar edición
    output = {
        "edition_date": datetime.now(timezone.utc).strftime("%B %d, %Y"),
        "written_at":   datetime.now(timezone.utc).isoformat(),
        "total":        len(edition),
        "articles":     edition,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log.info(f"Edición guardada en {OUTPUT_FILE} con {len(edition)} artículos")
    log.info("═══ Redacción completa ═══")

    # Preview en consola
    log.info("\n" + "="*60)
    log.info(f"FREE WIRE — Edition {output['edition_date']}")
    log.info("="*60)
    for a in edition[:5]:
        log.info(f"\n{a['headline']}")
        for b in a["bullets"]:
            log.info(f"  {b}")
        log.info(f"  {a['source_line']}")
    log.info("="*60)


if __name__ == "__main__":
    write_all()
