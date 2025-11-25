# vcon-fadapter Ingress List Support - Changes Summary

## Overview
Added support for specifying ingress lists when posting vCons to the conserver API. This allows vCons to be automatically routed to specific processing queues based on configuration.

## Changes Made

### 1. Configuration (fax_adapter/config.py)
- Added `INGRESS_LISTS` environment variable support
- New property: `config.ingress_lists` - a list of ingress queue names
- Supports comma-separated list format (e.g., "fax_processing,main_ingress")
- Properly handles whitespace around queue names
- Defaults to empty list if not configured

### 2. HTTP Poster (fax_adapter/poster.py)
- Updated `HttpPoster.__init__()` to accept optional `ingress_lists` parameter
- Modified `post()` method to append `ingress_lists` query parameter when configured
- Added informative logging to indicate which ingress lists are being used
- Query parameter format matches API spec: `ingress_lists=queue1,queue2`

### 3. Main Application (main.py)
- Updated `FaxAdapter` to pass `config.ingress_lists` to `HttpPoster` constructor
- No other changes required - the feature integrates seamlessly

### 4. Documentation (README.md)
- Added `INGRESS_LISTS` to the Optional Settings section
- Updated example configuration to demonstrate usage
- Enhanced "How It Works" section to mention ingress queue routing

### 5. Tests
Enhanced test coverage for the new functionality:

**test_config.py:**
- `test_config_ingress_lists_empty`: Tests empty string handling
- `test_config_ingress_lists_single`: Tests single queue name
- `test_config_ingress_lists_multiple`: Tests multiple queue names
- `test_config_ingress_lists_with_spaces`: Tests whitespace trimming
- `test_config_ingress_lists_not_set`: Tests default behavior
- Updated `test_config_defaults`: Verifies empty list default

**test_poster.py:**
- `test_post_with_ingress_lists`: Tests query parameter generation
- `test_post_without_ingress_lists`: Tests backward compatibility
- `test_post_with_empty_ingress_lists`: Tests empty list handling
- Updated existing tests to match new API signature

## Usage Examples

### Basic Configuration
```env
WATCH_DIRECTORY=/var/fax/incoming
CONSERVER_URL=http://localhost:8000/api/vcon
CONSERVER_API_TOKEN=my-secret-token
INGRESS_LISTS=fax_processing,main_ingress
```

### Single Ingress Queue
```env
INGRESS_LISTS=fax_processing
```

### Multiple Ingress Queues
```env
INGRESS_LISTS=fax_processing,main_ingress,backup_queue
```

### No Ingress Routing (Backward Compatible)
```env
# Simply don't set INGRESS_LISTS or leave it empty
INGRESS_LISTS=
```

## API Behavior

When `INGRESS_LISTS` is configured, the adapter will post vCons with the query parameter:
```
POST http://conserver-url/api/vcon?ingress_lists=fax_processing,main_ingress
```

This matches the vCon server API specification documented in the API Reference.

## Testing Results
All 106 tests pass:
- 22 tests in test_config.py (5 new tests for ingress_lists)
- 15 tests in test_poster.py (3 new tests for ingress_lists)
- 69 tests in other modules (unchanged, all passing)

Note: Fixed two tests (`test_config_defaults` and `test_config_ingress_lists_not_set`) to properly mock `load_dotenv` to prevent them from loading environment variables from .env files during testing.

## Backward Compatibility
The changes are fully backward compatible:
- Existing configurations without `INGRESS_LISTS` work as before
- Default behavior (no ingress routing) is preserved
- No breaking changes to any APIs

