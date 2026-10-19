import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load local agent .env if present
load_dotenv(BASE_DIR / '.env')

AGENT_VERSION = "1.0.0"

# Station Identity & Credentials
STATION_CODE = os.getenv("PRINTX_STATION_CODE", "STN-MAIN-01")
AGENT_SECRET = os.getenv("PRINTX_AGENT_SECRET", "printx_secret_station_2026")

# Backend API Configuration
BACKEND_BASE_URL = os.getenv("PRINTX_BACKEND_URL", "http://127.0.0.1:8000/api/v1").rstrip('/')
POLL_INTERVAL_SECONDS = int(os.getenv("PRINTX_POLL_INTERVAL", "5"))
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("PRINTX_HEARTBEAT_INTERVAL", "30"))

# Local Storage & Recovery Ledger
SPOOL_DIR = Path(os.getenv("PRINTX_SPOOL_DIR", BASE_DIR / "spool"))
LEDGER_DB_PATH = Path(os.getenv("PRINTX_LEDGER_DB", BASE_DIR / "agent_ledger.sqlite3"))

# Physical Printer Configuration & Explicit Allowlist
# Never silently print to an arbitrary default printer!
DEFAULT_PRINTER_NAME = os.getenv("PRINTX_DEFAULT_PRINTER", "Microsoft Print to PDF")
ALLOWED_PRINTERS = [
    p.strip() for p in os.getenv(
        "PRINTX_ALLOWED_PRINTERS",
        "Microsoft Print to PDF,HP LaserJet Pro,Canon iR-ADV,PDFCreator"
    ).split(',') if p.strip()
]

# Mode: 'windows_native' or 'mock' (for automated tests / headless CI)
PRINT_EXECUTION_MODE = os.getenv("PRINTX_PRINT_MODE", "mock" if os.name != 'nt' else "windows_native")
