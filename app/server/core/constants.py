"""
Constants for file processing and data flattening.

This module contains configurable constants used across the application
for consistent data transformation and schema generation.
"""

# Delimiter for flattening nested object fields
# Example: {"user": {"address": {"city": "NYC"}}} -> "user__address__city"
NESTED_FIELD_DELIMITER = "__"

# Delimiter for flattening array indices
# Example: {"tags": ["python", "sql"]} -> "tags_0", "tags_1"
ARRAY_INDEX_DELIMITER = "_"
