import os
import logging

JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_key")
ALGORITHM = "HS256"
MAX_MSG_LENGTH = 2000
WS_HEARTBEAT_TIMEOUT = 60.0

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
