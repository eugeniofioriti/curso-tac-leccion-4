import pytest
import json
import pandas as pd
import sqlite3
import os
import io
from pathlib import Path
from unittest.mock import patch
from core.file_processor import (
    convert_csv_to_sqlite,
    convert_json_to_sqlite,
    convert_jsonl_to_sqlite,
    flatten_json_object,
    discover_jsonl_schema
)


@pytest.fixture
def test_db():
    """Create an in-memory test database"""
    # Create in-memory database
    conn = sqlite3.connect(':memory:')
    
    # Patch the database connection to use our in-memory database
    with patch('core.file_processor.sqlite3.connect') as mock_connect:
        mock_connect.return_value = conn
        yield conn
    
    conn.close()


@pytest.fixture
def test_assets_dir():
    """Get the path to test assets directory"""
    return Path(__file__).parent.parent / "assets"


class TestFileProcessor:
    
    def test_convert_csv_to_sqlite_success(self, test_db, test_assets_dir):
        # Load real CSV file
        csv_file = test_assets_dir / "test_users.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "users"
        result = convert_csv_to_sqlite(csv_data, table_name)
        
        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result
        
        # Test the returned data
        assert result['row_count'] == 4  # 4 users in test file
        assert len(result['sample_data']) <= 5  # Should return up to 5 samples
        
        # Verify schema has expected columns (cleaned names)
        assert 'name' in result['schema']
        assert 'age' in result['schema'] 
        assert 'city' in result['schema']
        assert 'email' in result['schema']
        
        # Verify sample data structure and content
        john_data = next((item for item in result['sample_data'] if item['name'] == 'John Doe'), None)
        assert john_data is not None
        assert john_data['age'] == 25
        assert john_data['city'] == 'New York'
        assert john_data['email'] == 'john@example.com'
    
    def test_convert_csv_to_sqlite_column_cleaning(self, test_db, test_assets_dir):
        # Test column name cleaning with real file
        csv_file = test_assets_dir / "column_names.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "test_users"
        result = convert_csv_to_sqlite(csv_data, table_name)
        
        # Verify columns were cleaned in the schema
        assert 'full_name' in result['schema']
        assert 'birth_date' in result['schema']
        assert 'email_address' in result['schema']
        assert 'phone_number' in result['schema']
        
        # Verify sample data has cleaned column names and actual content
        sample = result['sample_data'][0]
        assert 'full_name' in sample
        assert 'birth_date' in sample
        assert 'email_address' in sample
        assert sample['full_name'] == 'John Doe'
        assert sample['birth_date'] == '1990-01-15'
    
    def test_convert_csv_to_sqlite_with_inconsistent_data(self, test_db, test_assets_dir):
        # Test with CSV that has inconsistent row lengths - should raise error
        csv_file = test_assets_dir / "invalid.csv"
        with open(csv_file, 'rb') as f:
            csv_data = f.read()
        
        table_name = "inconsistent_table"
        
        # Pandas will fail on inconsistent CSV data
        with pytest.raises(Exception) as exc_info:
            convert_csv_to_sqlite(csv_data, table_name)
        
        assert "Error converting CSV to SQLite" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_success(self, test_db, test_assets_dir):
        # Load real JSON file
        json_file = test_assets_dir / "test_products.json"
        with open(json_file, 'rb') as f:
            json_data = f.read()
        
        table_name = "products"
        result = convert_json_to_sqlite(json_data, table_name)
        
        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result
        
        # Test the returned data
        assert result['row_count'] == 3  # 3 products in test file
        assert len(result['sample_data']) == 3
        
        # Verify schema has expected columns
        assert 'id' in result['schema']
        assert 'name' in result['schema']
        assert 'price' in result['schema']
        assert 'category' in result['schema']
        assert 'in_stock' in result['schema']
        
        # Verify sample data structure and content
        laptop_data = next((item for item in result['sample_data'] if item['name'] == 'Laptop'), None)
        assert laptop_data is not None
        assert laptop_data['price'] == 999.99
        assert laptop_data['category'] == 'Electronics'
        assert laptop_data['in_stock'] == True
    
    def test_convert_json_to_sqlite_invalid_json(self):
        # Test with invalid JSON
        json_data = b'invalid json'
        table_name = "test_table"
        
        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)
        
        assert "Error converting JSON to SQLite" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_not_array(self):
        # Test with JSON that's not an array
        json_data = b'{"name": "John", "age": 25}'
        table_name = "test_table"
        
        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)
        
        assert "JSON must be an array of objects" in str(exc_info.value)
    
    def test_convert_json_to_sqlite_empty_array(self):
        # Test with empty JSON array
        json_data = b'[]'
        table_name = "test_table"

        with pytest.raises(Exception) as exc_info:
            convert_json_to_sqlite(json_data, table_name)

        assert "JSON array is empty" in str(exc_info.value)

    def test_flatten_json_object(self):
        # Test flattening of nested objects
        nested_obj = {
            "user": {
                "name": "Alice",
                "address": {
                    "city": "New York",
                    "zip": "10001"
                }
            },
            "tags": ["python", "sql"],
            "active": True
        }

        flattened = flatten_json_object(nested_obj)

        # Verify nested object flattening
        assert flattened["user__name"] == "Alice"
        assert flattened["user__address__city"] == "New York"
        assert flattened["user__address__zip"] == "10001"

        # Verify array flattening
        assert flattened["tags_0"] == "python"
        assert flattened["tags_1"] == "sql"

        # Verify primitive values
        assert flattened["active"] == True

    def test_flatten_json_object_with_nested_array_of_objects(self):
        # Test flattening arrays of objects
        obj = {
            "items": [
                {"product": "laptop", "price": 1200},
                {"product": "mouse", "price": 25}
            ]
        }

        flattened = flatten_json_object(obj)

        assert flattened["items_0__product"] == "laptop"
        assert flattened["items_0__price"] == 1200
        assert flattened["items_1__product"] == "mouse"
        assert flattened["items_1__price"] == 25

    def test_flatten_json_object_empty(self):
        # Test with empty object
        flattened = flatten_json_object({})
        assert flattened == {}

    def test_convert_jsonl_to_sqlite_success(self, test_db, test_assets_dir):
        # Load simple JSONL file
        jsonl_file = test_assets_dir / "simple.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "users"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify return structure
        assert result['table_name'] == table_name
        assert 'schema' in result
        assert 'row_count' in result
        assert 'sample_data' in result

        # Test the returned data
        assert result['row_count'] == 4
        assert len(result['sample_data']) == 4

        # Verify schema has expected columns
        assert 'name' in result['schema']
        assert 'age' in result['schema']
        assert 'city' in result['schema']
        assert 'email' in result['schema']

        # Verify sample data content
        alice_data = next((item for item in result['sample_data'] if item['name'] == 'Alice'), None)
        assert alice_data is not None
        assert alice_data['age'] == 30
        assert alice_data['city'] == 'New York'
        assert alice_data['email'] == 'alice@example.com'

    def test_convert_jsonl_to_sqlite_nested_objects(self, test_db, test_assets_dir):
        # Load nested JSONL file
        jsonl_file = test_assets_dir / "nested.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "nested_users"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify nested fields are flattened with __ delimiter
        assert 'user__name' in result['schema']
        assert 'user__address__city' in result['schema']
        assert 'user__address__state' in result['schema']
        assert 'user__address__zip' in result['schema']

        # Verify first record has nested data
        first_record = result['sample_data'][0]
        assert first_record['user__name'] == 'Alice'
        assert first_record['user__address__city'] == 'New York'
        assert first_record['user__address__state'] == 'NY'

    def test_convert_jsonl_to_sqlite_arrays(self, test_db, test_assets_dir):
        # Load nested JSONL file which contains arrays
        jsonl_file = test_assets_dir / "nested.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "array_test"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify arrays are flattened with index suffixes
        assert 'tags_0' in result['schema']
        assert 'tags_1' in result['schema']
        assert 'tags_2' in result['schema']

        # Verify first record's array data
        first_record = result['sample_data'][0]
        assert first_record['tags_0'] == 'python'
        assert first_record['tags_1'] == 'sql'
        assert first_record['tags_2'] == 'data'

    def test_convert_jsonl_to_sqlite_varying_schemas(self, test_db, test_assets_dir):
        # Load nested JSONL file which has varying schemas
        jsonl_file = test_assets_dir / "nested.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        table_name = "varying_schema"
        result = convert_jsonl_to_sqlite(jsonl_data, table_name)

        # Verify all fields from all records are in schema
        # First record has address fields
        assert 'user__address__city' in result['schema']
        assert 'user__address__state' in result['schema']
        assert 'user__address__zip' in result['schema']

        # Second record has 'active' field
        assert 'active' in result['schema']

        # Third record has 'email' field and 'items' array
        assert 'user__email' in result['schema']
        assert 'items_0__product' in result['schema']
        assert 'items_0__price' in result['schema']

        # Verify missing fields are None/NULL
        third_record = result['sample_data'][2]
        assert third_record['user__address__city'] is None

    def test_convert_jsonl_to_sqlite_invalid_jsonl(self):
        # Test with malformed JSONL data
        jsonl_data = b'{"valid": "json"}\ninvalid json line\n{"another": "valid"}'
        table_name = "test_table"

        with pytest.raises(Exception) as exc_info:
            convert_jsonl_to_sqlite(jsonl_data, table_name)

        assert "Error converting JSONL to SQLite" in str(exc_info.value)

    def test_convert_jsonl_to_sqlite_empty_file(self):
        # Test with empty file
        jsonl_data = b''
        table_name = "test_table"

        with pytest.raises(Exception) as exc_info:
            convert_jsonl_to_sqlite(jsonl_data, table_name)

        assert "JSONL file is empty" in str(exc_info.value)

    def test_discover_jsonl_schema(self, test_assets_dir):
        # Load nested JSONL file
        jsonl_file = test_assets_dir / "nested.jsonl"
        with open(jsonl_file, 'rb') as f:
            jsonl_data = f.read()

        fields = discover_jsonl_schema(jsonl_data)

        # Verify all fields are discovered
        assert 'id' in fields
        assert 'user__name' in fields
        assert 'user__address__city' in fields
        assert 'tags_0' in fields
        assert 'tags_1' in fields
        assert 'active' in fields
        assert 'user__email' in fields
        assert 'items_0__product' in fields