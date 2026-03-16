"""
FREE WIRE — Orquestador Principal
==================================
Corre Agente 1 (Recolector) y Agente 2 (Curador) en secuencia
cada 2 horas. Un solo proceso, sin dependencias externas de storage.

Instalación:
    pip install feedparser apscheduler requests

Uso:
    python freewire_main.py
"""

import logging
from apscheduler.schedulers.blocking import BlockingScheduler

from freewire_agent1_collector import collect_all, save as save_raw
from freewire_agent2_curator import curate
from freewire_agent3_writer import write_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("freewire.main")

INTERVAL_HOURS = 2


def run_pipeline():
    """Pipeline completo: recolectar → curar."""
    log.info("╔══════════════════════════════════════╗")
    log.info("║   FREE WIRE — Pipeline iniciando     ║")
    log.info("╚══════════════════════════════════════╝")

    # Agente 1: Recolectar
    articles = collect_all()
    save_raw(articles)

    # Agente 2: Curar
    curate()

    # Agente 3: Redactar
    write_all()

    log.info("╔══════════════════════════════════════╗")
    log.info("║   FREE WIRE — Pipeline completo      ║")
    log.info("╚══════════════════════════════════════╝")


if __name__ == "__main__":
    run_pipeline()  # Correr inmediatamente al iniciar

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_pipeline, "interval", hours=INTERVAL_HOURS)
    log.info(f"Scheduler activo — próxima corrida en {INTERVAL_HOURS}hs")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Pipeline detenido.")
