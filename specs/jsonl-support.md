# Feature: JSONL File Upload Support

## Feature Description
Add support for uploading JSONL (JSON Lines) files to the Natural Language SQL Interface application. JSONL files contain newline-delimited JSON objects, with each line representing a separate JSON object. This feature will enable users to upload JSONL files alongside the existing CSV and JSON formats, with automatic flattening of nested objects and arrays into a single SQLite table. The implementation will scan the entire JSONL file to discover all possible fields across all objects before creating the schema, ensuring no data is lost due to schema variations across different records.

## User Story
As a data analyst
I want to upload JSONL files to the Natural Language SQL Interface
So that I can query semi-structured data with nested fields and varying schemas using natural language, just like I do with CSV and JSON files

## Problem Statement
Currently, the application only supports CSV and JSON array formats for file uploads. However, JSONL is a widely-used format for streaming data, logs, and API responses, where each line is an independent JSON object. Many users work with JSONL files from various sources (API exports, log aggregators, data pipelines) and need a way to analyze this data without manually converting it to JSON arrays or CSV format. Additionally, JSONL files often contain nested objects and arrays that need to be flattened in a consistent, queryable way.

## Solution Statement
Implement JSONL file processing by creating a new `convert_jsonl_to_sqlite()` function that reads the file line-by-line, parses each JSON object, and flattens nested structures using a configurable delimiter (`__` for nested fields, `_0`, `_1`, etc. for array indices). The solution will:

1. Parse the entire JSONL file first to collect all possible field names across all records (handling schema variations)
2. Flatten nested objects by concatenating field names with `__` delimiter (e.g., `user.address.city` becomes `user__address__city`)
3. Flatten arrays by appending index-based suffixes with the delimiter (e.g., `tags[0]` becomes `tags_0`, `tags[1]` becomes `tags_1`)
4. Store the delimiter configuration in a new constants module for easy customization
5. Create a SQLite table with all discovered columns, handling missing fields gracefully
6. Update the UI to indicate JSONL support in file upload instructions
7. Create comprehensive test JSONL files to validate the implementation

## Relevant Files
Use these files to implement the feature:

- `app/server/core/file_processor.py` - Contains the CSV and JSON conversion functions; will add the new JSONL conversion function here following the same pattern
- `app/server/server.py` - Contains the `/api/upload` endpoint that validates file types; needs to accept `.jsonl` extension
- `app/server/tests/core/test_file_processor.py` - Contains tests for file processing; will add JSONL-specific tests here
- `app/client/src/main.ts` - Contains file upload logic and UI initialization; needs to update file type validation and display JSONL support in the UI
- `README.md` - Contains user documentation about supported file types; needs to mention `.jsonl` support

### New Files

- `app/server/core/constants.py` - New constants module to store configurable values like the nested field delimiter (`NESTED_FIELD_DELIMITER = "__"`) and the array index delimiter (`ARRAY_INDEX_DELIMITER = "_"`)
- `app/server/tests/assets/simple.jsonl` - Simple test JSONL file with flat objects for basic functionality testing
- `app/server/tests/assets/nested.jsonl` - Complex test JSONL file with nested objects, arrays, and varying schemas to test flattening logic and schema discovery

## Implementation Plan

### Phase 1: Foundation
Create the constants module and establish the configuration for field flattening. This provides a single source of truth for delimiter configuration that can be easily updated if requirements change.

### Phase 2: Core Implementation
Implement the JSONL parsing and flattening logic in the file processor. This is the core functionality that reads JSONL files, discovers all fields, flattens nested structures, and creates SQLite tables following the same patterns as existing CSV/JSON converters.

### Phase 3: Integration
Update the API endpoint, frontend UI, tests, and documentation to fully integrate JSONL support into the application. This makes the feature accessible to users and ensures it's properly tested and documented.

## Step by Step Tasks

### 1. Create Constants Module
- Create `app/server/core/constants.py` file
- Define `NESTED_FIELD_DELIMITER = "__"` constant for nested object field separation
- Define `ARRAY_INDEX_DELIMITER = "_"` constant for array index suffix separation
- Add docstring explaining the purpose and usage of these constants

### 2. Implement JSONL Flattening Helper Function
- In `app/server/core/file_processor.py`, create `flatten_json_object()` helper function
- Function signature: `flatten_json_object(obj: Dict[str, Any], parent_key: str = '') -> Dict[str, Any]`
- Implement recursive logic to flatten nested dictionaries using `NESTED_FIELD_DELIMITER`
- Implement array handling to create separate fields for each index using `ARRAY_INDEX_DELIMITER` and index (e.g., `tags_0`, `tags_1`)
- Handle edge cases: null values, empty objects, empty arrays, deeply nested structures
- Return flattened dictionary with all keys at the top level

### 3. Implement JSONL Schema Discovery Function
- In `app/server/core/file_processor.py`, create `discover_jsonl_schema()` helper function
- Function signature: `discover_jsonl_schema(jsonl_content: bytes) -> Set[str]`
- Read through entire JSONL file line by line
- Parse each JSON object and flatten it using `flatten_json_object()`
- Collect all unique field names across all objects into a set
- Return the complete set of field names found in the file
- Handle malformed lines gracefully with proper error messages

### 4. Implement JSONL to SQLite Conversion Function
- In `app/server/core/file_processor.py`, create `convert_jsonl_to_sqlite()` function
- Function signature: `convert_jsonl_to_sqlite(jsonl_content: bytes, table_name: str) -> Dict[str, Any]`
- Sanitize table name using existing `sanitize_table_name()` function
- Call `discover_jsonl_schema()` to get all possible fields first
- Read through JSONL file again, flattening each object with `flatten_json_object()`
- Create a list of dictionaries with all discovered fields (filling missing fields with None)
- Convert to pandas DataFrame with all columns
- Clean column names (lowercase, replace spaces and hyphens with underscores) matching existing pattern
- Write DataFrame to SQLite using `to_sql()` with `if_exists='replace'` and `index=False`
- Use `execute_query_safely()` for all database queries (PRAGMA, SELECT, COUNT)
- Return dictionary with `table_name`, `schema`, `row_count`, and `sample_data` matching existing functions
- Wrap in try/except with descriptive error message

### 5. Update API Endpoint File Validation
- In `app/server/server.py`, locate the `/api/upload` endpoint (line 72-109)
- Update file type validation on line 77 to accept `.jsonl` extension: `if not file.filename.endswith(('.csv', '.json', '.jsonl')):`
- Update error message on line 78 to include JSONL: `"Only .csv, .json, and .jsonl files are supported"`
- Add conditional branch for JSONL files in the conversion logic (after line 89)
- Import `convert_jsonl_to_sqlite` from `core.file_processor`
- Call `convert_jsonl_to_sqlite()` when file ends with `.jsonl`

### 6. Create Test JSONL Files
- Create `app/server/tests/assets/simple.jsonl` with 4 flat JSON objects (name, age, city, email fields)
- Create `app/server/tests/assets/nested.jsonl` with 3 complex objects including:
  - Nested objects (e.g., user with address containing city, state, zip)
  - Arrays of primitives (e.g., tags array)
  - Varying schemas across records (some fields present in some objects but not others)
  - At least one object with nested array containing objects

### 7. Write Unit Tests for JSONL Processing
- In `app/server/tests/core/test_file_processor.py`, add test class or methods for JSONL
- Test `test_convert_jsonl_to_sqlite_success()`: Load simple.jsonl, verify table creation, schema, row count, sample data
- Test `test_convert_jsonl_to_sqlite_nested_objects()`: Load nested.jsonl, verify nested fields are flattened with `__` delimiter
- Test `test_convert_jsonl_to_sqlite_arrays()`: Verify arrays are flattened with index suffixes (e.g., `tags_0`, `tags_1`)
- Test `test_convert_jsonl_to_sqlite_varying_schemas()`: Verify all fields from all records are discovered and included in schema
- Test `test_convert_jsonl_to_sqlite_invalid_jsonl()`: Test with malformed JSONL data, verify proper error handling
- Test `test_convert_jsonl_to_sqlite_empty_file()`: Test with empty file, verify appropriate error
- Test `test_flatten_json_object()`: Unit test the flattening function with various nested structures
- Follow existing test patterns using fixtures and assertions

### 8. Update Frontend File Upload UI
- In `app/client/src/main.ts`, locate the `handleFileUpload()` function (lines 93-106)
- No code changes needed here as the function already accepts any File type
- Locate the drop zone UI definition in `app/client/index.html` or wherever the upload modal is defined
- Update the file upload instructions text to mention JSONL files
- Change text from "drag and drop your own .csv or .json files" to "drag and drop your own .csv, .json, or .jsonl files"
- Update any other UI text that mentions supported file types

### 9. Update Frontend Type Definitions (if needed)
- Check `app/client/src/types.d.ts` for any file type restrictions
- If there are TypeScript type definitions restricting file extensions, update them to include `.jsonl`
- Ensure the `FileUploadResponse` and related types remain unchanged

### 10. Update README Documentation
- In `README.md`, locate the Features section (line 5-11)
- Update line 8 from "📁 Drag-and-drop file upload (.csv and .json)" to "📁 Drag-and-drop file upload (.csv, .json, and .jsonl)"
- Locate the Usage section (line 82-92)
- Update line 86 from "Or drag and drop your own .csv or .json files" to "Or drag and drop your own .csv, .json, or .jsonl files"
- Add a new subsection under "Usage" or "Features" explaining JSONL flattening behavior:
  - Nested objects are flattened with `__` delimiter
  - Array items are indexed with `_N` suffix
  - All fields across all records are discovered and included
- Update API Endpoints section (line 136-142) if needed to clarify the upload endpoint accepts JSONL

### 11. Run All Tests to Validate Implementation
- Execute the validation commands listed below
- Ensure all existing tests still pass (no regressions)
- Ensure all new JSONL tests pass
- Fix any failing tests before proceeding

### 12. Manual End-to-End Testing
- Start the application using `./scripts/start.sh`
- Upload simple.jsonl through the UI and verify table creation
- Upload nested.jsonl and verify nested fields are properly flattened
- Run natural language queries against the JSONL-created tables
- Verify the table schema display shows flattened field names correctly
- Test uploading a JSONL file with the same name twice (should replace the table)
- Test edge cases: very large JSONL file, JSONL with special characters in field names

## Testing Strategy

### Unit Tests
- **Flattening Logic**: Test `flatten_json_object()` with various nested structures (nested objects, arrays, mixed types, edge cases)
- **Schema Discovery**: Test `discover_jsonl_schema()` with files containing varying schemas across records
- **Conversion Function**: Test `convert_jsonl_to_sqlite()` with valid JSONL files, verifying table creation, schema correctness, and data integrity
- **Error Handling**: Test invalid JSONL (malformed JSON, empty files, invalid characters)
- **Column Name Cleaning**: Verify special characters in field names are properly sanitized
- **SQL Security**: Ensure all database operations use `execute_query_safely()` and follow security best practices

### Integration Tests
- **API Endpoint**: Test the `/api/upload` endpoint with JSONL files via HTTP requests
- **File Type Validation**: Verify JSONL files are accepted and other types are rejected
- **End-to-End Upload Flow**: Upload JSONL file, retrieve schema, query the data, verify results
- **UI Integration**: Test file upload through the frontend interface (manual testing)

### Edge Cases
- **Empty JSONL file**: Should return appropriate error message
- **Single-line JSONL**: Should work correctly with just one object
- **Malformed JSON lines**: Should handle parse errors gracefully with descriptive messages
- **Very deep nesting**: Objects nested 5+ levels deep should flatten correctly
- **Large arrays**: Arrays with 100+ items should create corresponding indexed fields
- **Missing fields**: Objects missing fields that exist in other objects should have NULL values
- **Special characters in field names**: Should be sanitized following existing patterns
- **Mixed data types in same field**: Should handle pandas' type inference gracefully
- **Unicode characters**: Should properly handle UTF-8 encoded content
- **Large files**: Files with 10,000+ lines should process efficiently
- **Duplicate field names after flattening**: Should handle collisions if they occur

## Acceptance Criteria
1. Users can successfully upload `.jsonl` files through the web interface
2. JSONL files are parsed correctly, with each line treated as a separate record
3. Nested objects are flattened using the `__` delimiter (configurable via constants)
4. Arrays are flattened with indexed suffixes using the `_` delimiter and index number
5. Schema discovery identifies all unique fields across all records in the file
6. Records with missing fields populate those columns with NULL values in SQLite
7. The created SQLite table follows the same structure and behavior as CSV/JSON uploads
8. All existing functionality (CSV, JSON uploads) continues to work without regression
9. Natural language queries work correctly on tables created from JSONL files
10. The UI clearly indicates that JSONL files are supported
11. Appropriate error messages are shown for invalid JSONL files
12. All unit tests pass with >90% code coverage for new functions
13. Documentation is updated to reflect JSONL support
14. The delimiter configuration is stored in a constants file for easy modification

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest tests/core/test_file_processor.py -v` - Run file processor tests including new JSONL tests
- `cd app/server && uv run pytest tests/ -v` - Run all server tests to ensure no regressions
- `cd app/server && uv run pytest tests/core/test_file_processor.py::TestFileProcessor::test_convert_jsonl_to_sqlite_success -v` - Run specific JSONL success test
- `cd app/server && uv run pytest tests/core/test_file_processor.py::TestFileProcessor::test_convert_jsonl_to_sqlite_nested_objects -v` - Run nested objects flattening test
- `cd app/server && uv run pytest tests/core/test_file_processor.py::TestFileProcessor::test_flatten_json_object -v` - Run flattening function unit test
- `./scripts/start.sh` - Start the application for manual end-to-end testing (run in background, test for 5 minutes, then stop)

## Notes

### JSONL Format Background
JSONL (JSON Lines) is a convenient format for storing structured data that may be processed one record at a time. Each line is a valid JSON value, typically an object. This format is ideal for streaming, logging, and processing large datasets that don't fit in memory as a single JSON array.

### Flattening Strategy
The flattening strategy uses delimiters to create unique column names:
- **Nested objects**: `user.address.city` → `user__address__city`
- **Array items**: `tags[0]` → `tags_0`, `tags[1]` → `tags_1`
- **Nested arrays**: `items[0].name` → `items_0__name`

This strategy ensures all data is queryable via SQL while maintaining clear field provenance.

### Schema Discovery Rationale
Unlike CSV (fixed schema) and JSON arrays (typically uniform), JSONL files often have varying schemas across records. Some records may have fields that others lack. By scanning the entire file first, we ensure no data is lost and all fields are represented in the table schema. Missing fields in individual records are stored as NULL.

### Performance Considerations
For very large JSONL files (millions of lines), reading the file twice (once for schema discovery, once for data loading) may impact performance. However, this trade-off ensures correctness and complete schema coverage. Future optimizations could include:
- Streaming schema discovery and data loading in a single pass
- Sampling-based schema discovery for extremely large files
- Configurable schema discovery depth

### Alternative Approaches Considered
- **Single-pass processing**: Would require dynamic schema expansion, complicating SQLite table creation
- **Sample-based schema discovery**: Could miss fields that appear only in later records
- **User-provided schema**: Would require additional UI and increase complexity

The chosen approach prioritizes correctness and simplicity over raw performance.

### Future Enhancements
- Support for nested arrays of objects (currently flattened but may create many columns)
- Configurable maximum nesting depth to prevent schema explosion
- Option to keep nested JSON as TEXT columns instead of flattening
- Progress indicator for large file uploads
- Schema preview before final table creation
