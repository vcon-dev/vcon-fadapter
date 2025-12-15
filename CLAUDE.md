# CLAUDE.md - AI Assistant Context for vCon Fax Adapter

This file provides context for AI assistants (like Claude) working on the vCon Fax Adapter project.

## Project Overview

**vCon Fax Adapter** is a file system monitoring application that watches a directory for incoming fax image files, extracts metadata from filenames, creates standardized vCon (Virtual Conversation) objects, and posts them to a configurable HTTP conserver endpoint.

### Key Purpose
Automate the conversion of fax images into structured vCon format for integration with communication systems.

### Technology Stack
- **Language**: Python 3.10+
- **Package Manager**: uv (recommended) or pip
- **Key Dependencies**:
  - `vcon` - vCon object creation and manipulation
  - `watchdog` - File system monitoring
  - `python-dotenv` - Environment configuration
  - `Pillow` - Image processing and metadata extraction
- **Testing**: pytest with coverage reporting
- **Linting**: ruff and black
- **Build System**: hatchling

## Architecture

### Component Overview

The project follows a modular architecture with single-responsibility components:

```
main.py (FaxAdapter orchestrator)
    |
    +-- config.py (Config) - Configuration management
    +-- parser.py (FilenameParser) - Extract sender/receiver from filenames
    +-- builder.py (VconBuilder) - Create vCon objects from files
    +-- poster.py (HttpPoster) - POST vCons to conserver endpoint
    +-- tracker.py (StateTracker) - Track processed files to prevent duplicates
    +-- monitor.py (FileSystemMonitor) - Watch directory for new files
```

### Processing Flow

1. **Initialization**: Load config, initialize components
2. **Existing Files**: Optionally process files already in watch directory
3. **Monitoring**: Start watchdog observer for new file events
4. **Detection**: New image file appears in watch directory
5. **Parsing**: Extract sender/receiver from filename using regex
6. **Building**: Create vCon with parties, attachments, metadata
7. **Posting**: Send vCon to conserver via HTTP POST
8. **Tracking**: Record processing state
9. **Cleanup**: Optionally delete file after successful post

### Module Details

#### `config.py` (Config)
- Loads environment variables from `.env` file
- Validates required settings (WATCH_DIRECTORY, CONSERVER_URL)
- Provides defaults for optional settings
- Generates HTTP headers including API token

**Key Methods**:
- `get_headers()` - Returns dict of HTTP headers
- `get_filename_regex()` - Returns compiled regex pattern

#### `parser.py` (FilenameParser)
- Uses regex to extract sender/receiver phone numbers from filenames
- Default pattern: `(\d+)_(\d+)\.(jpg|jpeg|png|gif|tiff|tif|bmp|webp)`
- Returns tuple: (sender, receiver, extension) or None

#### `builder.py` (VconBuilder)
- Creates vCon objects using the `vcon` library
- Adds two parties (sender and receiver) with telephone numbers
- Encodes image as base64 attachment
- Extracts file metadata (size, dimensions, timestamps)
- Tags vCon with metadata for searchability

**MIME Type Mapping**: Maps file extensions to proper MIME types

#### `poster.py` (HttpPoster)
- Posts vCon JSON to conserver endpoint
- Handles authentication headers
- Logs success/failure for monitoring

#### `tracker.py` (StateTracker)
- Maintains JSON file of processed files
- Prevents duplicate processing
- Records vCon UUID and processing status
- Allows querying processing history

#### `monitor.py` (FileSystemMonitor)
- Uses watchdog library to monitor directory
- Filters by supported image extensions
- Calls callback function for each new file
- Provides method to get existing files

### Main Entry Point (`main.py`)

**FaxAdapter class**:
- Orchestrates all components
- Implements `_process_file()` - core processing logic
- Handles graceful shutdown via signal handlers
- Manages state across components

## Coding Conventions

### Style Guidelines
- **Line Length**: 100 characters (enforced by ruff and black)
- **Python Version**: 3.10+ (uses modern type hints)
- **Formatting**: Use black for automatic formatting
- **Linting**: Use ruff for fast Python linting
- **Type Hints**: Use where appropriate (see existing code)
- **Docstrings**: Google-style docstrings for classes and functions
- **Logging**: Use Python logging module (logger per module)

### Naming Conventions
- **Classes**: PascalCase (e.g., `VconBuilder`, `FileSystemMonitor`)
- **Functions/Methods**: snake_case (e.g., `process_file`, `get_headers`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MIME_TYPES`)
- **Private Methods**: Prefix with underscore (e.g., `_process_file`)

### Error Handling
- Log errors at appropriate levels (ERROR, WARNING, INFO, DEBUG)
- Return None for recoverable failures
- Raise ValueError for configuration errors
- Use try/except blocks around external operations (file I/O, HTTP, image processing)
- Don't crash on single file processing failure - continue monitoring

### Configuration
- All configuration via environment variables
- Use `.env` file for local development
- Required settings must raise ValueError if missing
- Provide sensible defaults for optional settings
- Document all settings in README.md

## Testing

### Test Structure
- **Location**: `tests/` directory
- **Naming**: `test_*.py` files, `test_*` functions
- **Framework**: pytest with coverage
- **Fixtures**: Defined in `conftest.py`

### Test Files
- `test_config.py` - Configuration loading and validation
- `test_parser.py` - Filename parsing logic
- `test_builder.py` - vCon creation
- `test_poster.py` - HTTP posting (mocked)
- `test_tracker.py` - State tracking
- `test_monitor.py` - File system monitoring
- `test_main.py` - Integration tests

### Running Tests
```bash
uv run pytest                           # All tests
uv run pytest --cov=fax_adapter        # With coverage
uv run pytest tests/test_config.py     # Specific file
uv run pytest -v                        # Verbose output
```

### Test Coverage
- Aim for high coverage (90%+ is typical)
- HTML coverage reports generated in `htmlcov/`
- CI runs coverage checks automatically

## Common Development Tasks

### Adding a New Configuration Option
1. Add to Config class `__init__` with default
2. Document in README.md configuration section
3. Add test in `test_config.py`
4. Update `.env.example` if it exists

### Supporting a New Image Format
1. Add extension to MIME_TYPES dict in `builder.py`
2. Add to default SUPPORTED_FORMATS in `config.py`
3. Update README.md supported formats list
4. Add test case with new format

### Modifying Filename Pattern
1. Update FILENAME_PATTERN environment variable
2. Ensure regex has at least 2 capture groups (sender, receiver)
3. Optional 3rd group for extension
4. Test with `FilenameParser`

### Adding New vCon Metadata
1. Modify `VconBuilder.build()` method
2. Use `vcon.add_tag(key, value)` for metadata
3. Document metadata fields in README.md
4. Add test to verify metadata presence

## Key Dependencies

### vcon Library
- Core library for creating vCon objects
- Methods used:
  - `Vcon.build_new()` - Create new vCon
  - `vcon.add_party(party)` - Add participant
  - `vcon.add_attachment(...)` - Add image data
  - `vcon.add_tag(key, value)` - Add metadata
  - `vcon.dumps()` - Serialize to JSON

### watchdog Library
- File system event monitoring
- Classes used:
  - `Observer` - Monitor file system
  - `FileSystemEventHandler` - Handle events
  - `FileCreatedEvent` - New file detection

### Party Objects
- Created with `Party(tel="phone_number")`
- Represents participants in conversation

## Important Considerations

### State Management
- State file prevents reprocessing files
- Important for crash recovery
- Location configurable via STATE_FILE
- JSON format for human readability

### File Deletion
- Only delete after successful HTTP POST
- Controlled by DELETE_AFTER_SEND config
- Log deletion errors but don't fail
- Consider backup/archive strategy

### Error Recovery
- Failed posts do not delete files
- State tracking allows retry logic
- Monitor logs for patterns
- Network issues should not lose data

### Performance
- Process files sequentially (current design)
- Watchdog is efficient for monitoring
- Base64 encoding increases size ~33%
- Large images may need chunking for HTTP

### Security
- API tokens via environment variables
- Never commit tokens to repository
- Use HTTPS for conserver endpoint
- Validate file types before processing

## Development Workflow

### Setup
```bash
git clone <repository>
cd vcon-fadapter
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env  # Edit with your settings
```

### Before Committing
```bash
black fax_adapter tests     # Format code
ruff fax_adapter tests      # Lint code
pytest --cov=fax_adapter    # Run tests
```

### CI/CD
- GitHub Actions runs on push and PR
- Tests on Python 3.10, 3.11, 3.12
- Tests on Ubuntu and macOS
- Linting and coverage checks

## Future Enhancement Ideas

- Parallel file processing for high volume
- Retry logic with exponential backoff
- Metrics/monitoring integration (Prometheus, etc.)
- OCR integration for fax content extraction
- Database backend for state tracking
- REST API for querying processed files
- Docker containerization
- Multi-directory monitoring
- File type validation (magic number checking)
- Compression for large images

## Debugging Tips

### Common Issues

**Files not being processed**:
- Check WATCH_DIRECTORY path is correct
- Verify file extensions match SUPPORTED_FORMATS
- Check filename matches FILENAME_PATTERN regex
- Look for "already processed" messages in logs

**HTTP posting fails**:
- Verify CONSERVER_URL is accessible
- Check API token is valid
- Inspect HTTP response status/body
- Test endpoint with curl

**vCon creation fails**:
- Ensure file is readable
- Check file is valid image format
- Verify Pillow can open the image
- Check for sufficient disk space

**State file issues**:
- Verify STATE_FILE path is writable
- Check JSON syntax if manually edited
- Delete state file to reprocess all files

### Logging Levels
- Adjust logging level in `main.py` for more/less detail
- Use DEBUG for verbose troubleshooting
- Use INFO for normal operation
- Use WARNING/ERROR for issues only

## Related Documentation

- **README.md** - User-facing documentation and setup guide
- **CONTRIBUTING.md** - Contribution guidelines
- **CODE_OF_CONDUCT.md** - Community guidelines
- **pyproject.toml** - Project metadata and dependencies
- **LICENSE** - MIT License

## Contact and Resources

- vCon Specification: Research vCon standards for data format
- Watchdog Documentation: https://pythonhosted.org/watchdog/
- Python Pillow: https://pillow.readthedocs.io/

---

**Note for AI Assistants**: When modifying this project, always consider backwards compatibility, maintain test coverage, follow the established patterns, and update documentation alongside code changes.

