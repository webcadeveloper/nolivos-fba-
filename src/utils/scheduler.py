"""
Scheduler para actualizar precios automáticamente cada 24 horas.
Usa APScheduler para ejecutar tareas en background.
"""
import sys
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
import atexit

# Añadir path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.price_tracker import PriceTracker
from src.analyzers.product_discovery import run_daily_scan

logging.basicConfig(level=logging.INFO)

class PriceScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.tracker = PriceTracker()
        
    def start(self):
        """Inicia el scheduler"""
        # Actualizar precios cada 24 horas
        self.scheduler.add_job(
            func=self.update_all_prices,
            trigger=IntervalTrigger(hours=24),
            id='price_update_job',
            name='Update all tracked product prices',
            replace_existing=True
        )

        # Escanear productos Best Sellers cada 24 horas (a las 2 AM)
        from apscheduler.triggers.cron import CronTrigger
        self.scheduler.add_job(
            func=run_daily_scan,
            trigger=CronTrigger(hour=2, minute=0),  # Todos los días a las 2 AM
            id='product_discovery_job',
            name='Daily Best Sellers scan for arbitrage opportunities',
            replace_existing=True
        )

        self.scheduler.start()
        logging.info("Scheduler started:")
        logging.info("  - Price updates: every 24 hours")
        logging.info("  - Product discovery: daily at 2:00 AM")

        # Asegurar que el scheduler se detenga al cerrar la app
        atexit.register(lambda: self.scheduler.shutdown())
    
    def update_all_prices(self):
        """Actualiza todos los precios trackeados"""
        logging.info("Running scheduled price update...")
        alerts = self.tracker.update_all_tracked_products()
        
        if alerts:
            # Aquí podrías enviar emails, notificaciones, etc.
            logging.warning(f"Price update complete. {len(alerts)} alerts generated.")
        else:
            logging.info("Price update complete. No alerts.")
    
    def stop(self):
        """Detiene el scheduler"""
        self.scheduler.shutdown()
        logging.info("Price scheduler stopped")
