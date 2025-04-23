import os
import sys
import traceback
import logging
from datetime import datetime

# Log yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bollinger_scheduler")

def run_scanner():
    try:
        logger.info("Starting Bollinger Band scan scheduler job...")
        # cron_scanner modülünü import et
        from cron_scanner import main
        # Ana işlevi çalıştır
        main()
        logger.info("Scan complete!")
        return True
    except Exception as e:
        # Hata durumunda detaylı log kaydet
        error_msg = f"Error during scan: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Heroku Scheduler tarafından çalıştırılacak
    start_time = datetime.now()
    logger.info(f"Scheduler started at {start_time}")
    
    success = run_scanner()
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info(f"Scheduler completed at {end_time}, Duration: {duration}, Success: {success}") 