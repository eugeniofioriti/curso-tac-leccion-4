import json
import pandas as pd
import sqlite3
import io
import re
from typing import Dict, Any, List, Set
from .sql_security import (
    execute_query_safely,
    validate_identifier,
    SQLSecurityError
)
from .constants import NESTED_FIELD_DELIMITER, ARRAY_INDEX_DELIMITER

def sanitize_table_name(table_name: str) -> str:
    """
    Sanitize table name for SQLite by removing/replacing bad characters
    and validating against SQL injection
    """
    # Remove file extension if present
    if '.' in table_name:
        table_name = table_name.rsplit('.', 1)[0]
    
    # Replace bad characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', table_name)
    
    # Ensure it starts with a letter or underscore
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = '_' + sanitized
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'table'
    
    # Validate the sanitized name
    try:
        validate_identifier(sanitized, "table")
    except SQLSecurityError:
        # If validation fails, use a safe default
        sanitized = f"table_{hash(table_name) % 100000}"
    
    return sanitized

def convert_csv_to_sqlite(csv_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert CSV file content to SQLite table
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)
        
        # Read CSV into pandas DataFrame
        df = pd.read_csv(io.BytesIO(csv_content))
        
        # Clean column names
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Connect to SQLite database
        conn = sqlite3.connect("db/database.db")
        
        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()
        
        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type
        
        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]
        
        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]
        
        conn.close()
        
        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }
        
    except Exception as e:
        raise Exception(f"Error converting CSV to SQLite: {str(e)}")

def convert_json_to_sqlite(json_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert JSON file content to SQLite table
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)
        
        # Parse JSON
        data = json.loads(json_content.decode('utf-8'))
        
        # Ensure it's a list of objects
        if not isinstance(data, list):
            raise ValueError("JSON must be an array of objects")
        
        if not data:
            raise ValueError("JSON array is empty")
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(data)
        
        # Clean column names
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Connect to SQLite database
        conn = sqlite3.connect("db/database.db")
        
        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()
        
        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type
        
        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]
        
        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]
        
        conn.close()
        
        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }
        
    except Exception as e:
        raise Exception(f"Error converting JSON to SQLite: {str(e)}")

def flatten_json_object(obj: Dict[str, Any], parent_key: str = '') -> Dict[str, Any]:
    """
    Recursively flatten a nested JSON object into a flat dictionary.

    Nested objects are flattened using NESTED_FIELD_DELIMITER (__).
    Arrays are flattened with indexed keys using ARRAY_INDEX_DELIMITER (_).

    Args:
        obj: The JSON object (dictionary) to flatten
        parent_key: The parent key for nested recursion (used internally)

    Returns:
        A flattened dictionary with all keys at the top level

    Examples:
        {"user": {"name": "John"}} -> {"user__name": "John"}
        {"tags": ["a", "b"]} -> {"tags_0": "a", "tags_1": "b"}
        {"items": [{"id": 1}, {"id": 2}]} -> {"items_0__id": 1, "items_1__id": 2}
    """
    items = {}

    for key, value in obj.items():
        # Create the new key
        new_key = f"{parent_key}{NESTED_FIELD_DELIMITER}{key}" if parent_key else key

        if isinstance(value, dict):
            # Recursively flatten nested dictionaries
            items.update(flatten_json_object(value, new_key))
        elif isinstance(value, list):
            # Flatten arrays with indexed keys
            for i, item in enumerate(value):
                array_key = f"{new_key}{ARRAY_INDEX_DELIMITER}{i}"
                if isinstance(item, dict):
                    # Array of objects - recursively flatten each object
                    items.update(flatten_json_object(item, array_key))
                else:
                    # Array of primitives - store directly
                    items[array_key] = item
        else:
            # Primitive value - store directly
            items[new_key] = value

    return items

def discover_jsonl_schema(jsonl_content: bytes) -> Set[str]:
    """
    Discover all unique field names across all records in a JSONL file.

    This function scans the entire JSONL file to collect all possible field names
    that appear in any record, ensuring no data is lost due to schema variations.

    Args:
        jsonl_content: The raw bytes content of the JSONL file

    Returns:
        A set of all unique field names found across all records

    Raises:
        ValueError: If the file is empty or contains invalid JSON
    """
    all_fields = set()
    lines_processed = 0

    # Decode bytes to string and process line by line
    content_str = jsonl_content.decode('utf-8')
    lines = content_str.strip().split('\n')

    if not lines or (len(lines) == 1 and not lines[0].strip()):
        raise ValueError("JSONL file is empty")

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        try:
            # Parse JSON object
            obj = json.loads(line)

            if not isinstance(obj, dict):
                raise ValueError(f"Line {line_num}: Each line must be a JSON object, got {type(obj).__name__}")

            # Flatten the object and collect all field names
            flattened = flatten_json_object(obj)
            all_fields.update(flattened.keys())
            lines_processed += 1

        except json.JSONDecodeError as e:
            raise ValueError(f"Line {line_num}: Invalid JSON - {str(e)}")

    if lines_processed == 0:
        raise ValueError("No valid JSON objects found in JSONL file")

    return all_fields

def convert_jsonl_to_sqlite(jsonl_content: bytes, table_name: str) -> Dict[str, Any]:
    """
    Convert JSONL file content to SQLite table.

    This function:
    1. Discovers all possible fields across all records
    2. Flattens nested objects and arrays using delimiters
    3. Creates a SQLite table with all discovered columns
    4. Handles missing fields gracefully (stores as None/NULL)

    Args:
        jsonl_content: The raw bytes content of the JSONL file
        table_name: The desired name for the SQLite table

    Returns:
        Dictionary containing:
            - table_name: Sanitized table name
            - schema: Column name to type mapping
            - row_count: Number of rows inserted
            - sample_data: First 5 rows as list of dictionaries

    Raises:
        Exception: If file processing or database operations fail
    """
    try:
        # Sanitize table name
        table_name = sanitize_table_name(table_name)

        # Discover all fields across all records
        all_fields = discover_jsonl_schema(jsonl_content)

        # Parse JSONL and create list of flattened dictionaries
        records = []
        content_str = jsonl_content.decode('utf-8')
        lines = content_str.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            obj = json.loads(line)
            flattened = flatten_json_object(obj)

            # Create record with all fields, filling missing ones with None
            record = {field: flattened.get(field) for field in all_fields}
            records.append(record)

        # Convert to pandas DataFrame
        df = pd.DataFrame(records)

        # Clean column names (lowercase, replace spaces and hyphens with underscores)
        df.columns = [col.lower().replace(' ', '_').replace('-', '_') for col in df.columns]

        # Connect to SQLite database
        conn = sqlite3.connect("db/database.db")

        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)

        # Get schema information using safe query execution
        cursor_info = execute_query_safely(
            conn,
            "PRAGMA table_info({table})",
            identifier_params={'table': table_name}
        )
        columns_info = cursor_info.fetchall()

        schema = {}
        for col in columns_info:
            schema[col[1]] = col[2]  # column_name: data_type

        # Get sample data using safe query execution
        cursor_sample = execute_query_safely(
            conn,
            "SELECT * FROM {table} LIMIT 5",
            identifier_params={'table': table_name}
        )
        sample_rows = cursor_sample.fetchall()
        column_names = [col[1] for col in columns_info]
        sample_data = [dict(zip(column_names, row)) for row in sample_rows]

        # Get row count using safe query execution
        cursor_count = execute_query_safely(
            conn,
            "SELECT COUNT(*) FROM {table}",
            identifier_params={'table': table_name}
        )
        row_count = cursor_count.fetchone()[0]

        conn.close()

        return {
            'table_name': table_name,
            'schema': schema,
            'row_count': row_count,
            'sample_data': sample_data
        }

    except Exception as e:
        raise Exception(f"Error converting JSONL to SQLite: {str(e)}")