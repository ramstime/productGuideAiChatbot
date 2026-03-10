__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import logging
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
