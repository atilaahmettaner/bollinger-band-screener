import os
import sys
from cron_scanner import main

if __name__ == "__main__":
    # Heroku Scheduler tarafından çalıştırılacak
    print("Starting Bollinger Band scan scheduler job...")
    main()
    print("Scan complete!") 