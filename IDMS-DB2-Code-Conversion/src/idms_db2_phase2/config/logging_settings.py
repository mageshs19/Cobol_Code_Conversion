"""
Logging settings.

Log files are written to the project logs folder with date-time names.
"""

LOG_FILE_PREFIX = "idms_db2_conversion"

LOG_DATE_TIME_FORMAT = "%d-%m-%Y_%H%M%S"

LOG_MESSAGE_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

LOG_DATE_FORMAT = "%d-%m-%Y %H:%M:%S"

DEFAULT_LOG_LEVEL = "INFO"