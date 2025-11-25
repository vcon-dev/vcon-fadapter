# Fax Image vCon Adapter

A file system monitoring adapter that watches for fax images, extracts sender/receiver information from filenames, creates vCon objects with file metadata, and posts them to a configurable HTTP conserver endpoint.

> **Note**: After pushing to GitHub, add status badges to this README by replacing `USERNAME` and `REPO` in:
> ```markdown
> [![Tests](https://github.com/USERNAME/REPO/actions/workflows/test.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/test.yml)
> [![Lint](https://github.com/USERNAME/REPO/actions/workflows/lint.yml/badge.svg)](https://github.com/USERNAME/REPO/actions/workflows/lint.yml)
> ```

## Features

- **File System Monitoring**: Automatically detects new fax image files using `watchdog`
- **Filename Parsing**: Extracts sender and receiver phone numbers from filenames using configurable regex patterns
- **vCon Creation**: Creates standardized vCon objects with parties, attachments, and metadata
- **HTTP Posting**: Posts vCons to configurable conserver endpoints with authentication
- **State Tracking**: Prevents duplicate processing by tracking processed files
- **Flexible Configuration**: Environment-based configuration via `.env` file
- **Image Format Support**: Supports major image formats (JPG, PNG, GIF, TIFF, BMP, WebP)

## Installation

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Option 1: Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver. Install it first:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then set up the project:

```bash
# Clone or navigate to the repository
cd vcon-fadapter

# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the project and its dependencies
uv pip install -e .

# Or use uv sync (requires uv.lock - generate with: uv lock)
# uv sync
```

### Option 2: Using pip

```bash
# Clone or navigate to the repository
cd vcon-fadapter

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:

### Required Settings

- `WATCH_DIRECTORY`: Directory path to monitor for fax images
- `CONSERVER_URL`: HTTP endpoint URL for posting vCons

### Optional Settings

- `CONSERVER_API_TOKEN`: API token for authentication (if required)
- `CONSERVER_HEADER_NAME`: Header name for API token (default: `x-conserver-api-token`)
- `INGRESS_LISTS`: Comma-separated list of ingress queue names to route vCons to (e.g., `fax_processing,main_ingress`)
- `FILENAME_PATTERN`: Regex pattern for parsing filenames (default: `(\d+)_(\d+)\.(jpg|jpeg|png|gif|tiff|tif|bmp|webp)`)
- `SUPPORTED_FORMATS`: Comma-separated list of image extensions (default: `jpg,jpeg,png,gif,tiff,tif,bmp,webp`)
- `DELETE_AFTER_SEND`: Delete files after successful HTTP post (default: `false`)
- `PROCESS_EXISTING`: Process existing files on startup (default: `true`)
- `STATE_FILE`: Path to state tracking file (default: `.fax_adapter_state.json`)
- `POLL_INTERVAL`: File system polling interval in seconds (default: `1.0`)

## Usage

### Basic Usage

```bash
python main.py
```

The adapter will:
1. Process any existing image files in the watch directory
2. Monitor for new image files
3. Create vCons and post them to the conserver endpoint

### Filename Format

By default, the adapter expects filenames in the format:
```
sender_receiver.extension
```

Example: `15085551212_15085551313.jpg`

- `15085551212` is the sender phone number
- `15085551313` is the receiver phone number
- `jpg` is the file extension

You can customize the filename pattern using the `FILENAME_PATTERN` environment variable. The regex must have at least 2 capture groups:
- Group 1: Sender
- Group 2: Receiver
- Group 3 (optional): File extension

### Example Configuration

```env
WATCH_DIRECTORY=/var/fax/incoming
CONSERVER_URL=http://localhost:8000/api/vcon
CONSERVER_API_TOKEN=my-secret-token
INGRESS_LISTS=fax_processing,main_ingress
DELETE_AFTER_SEND=true
PROCESS_EXISTING=true
```

## How It Works

1. **File Detection**: The adapter monitors the configured directory for new image files matching supported formats.

2. **Filename Parsing**: When a new file is detected, the filename is parsed using the configured regex pattern to extract sender and receiver phone numbers.

3. **vCon Creation**: A vCon object is created with:
   - Two parties (sender and receiver) with telephone numbers
   - Image file attached as base64-encoded attachment
   - Metadata tags including:
     - Source: "fax_adapter"
     - Original filename
     - File size
     - Image dimensions (if available)
     - Sender and receiver phone numbers
   - Creation time set from file modification time

4. **HTTP Posting**: The vCon is posted to the configured conserver endpoint with authentication headers. If ingress lists are configured, the vCon is automatically routed to the specified processing queues.

5. **State Tracking**: Processed files are tracked in a JSON state file to prevent reprocessing.

6. **File Deletion**: If `DELETE_AFTER_SEND=true` and the HTTP post succeeds, the original file is deleted.

## Error Handling

- **Invalid Filenames**: Files that don't match the pattern are logged and skipped
- **Image Read Errors**: Files that can't be read are logged and skipped
- **HTTP Post Failures**: Failed posts are logged, files are kept, and status is tracked
- **File Deletion Errors**: Deletion failures are logged but don't stop processing

## State File

The adapter maintains a JSON state file (default: `.fax_adapter_state.json`) that tracks:
- Processed file paths
- Associated vCon UUIDs
- Processing timestamps
- Processing status (success/failed)

This prevents reprocessing the same files and allows tracking of created vCons.

## Logging

The adapter uses Python's standard logging. Log levels can be controlled via environment variables or by modifying the logging configuration in `main.py`.

## Development

### Project Structure

```
vcon-fadapter/
├── fax_adapter/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── parser.py          # Filename parsing
│   ├── builder.py         # vCon creation
│   ├── poster.py          # HTTP posting
│   ├── tracker.py         # State tracking
│   └── monitor.py         # File system monitoring
├── .env.example           # Example configuration
├── .python-version        # Python version specification
├── pyproject.toml         # Project configuration and dependencies
├── requirements.txt       # Dependencies (legacy, use pyproject.toml)
├── README.md             # This file
└── main.py               # Entry point
```

### Development Setup with uv

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run the adapter
python main.py
```

### Running Tests

```bash
# Run all tests (using uv to ensure correct environment)
uv run pytest

# Run tests with coverage
uv run pytest --cov=fax_adapter --cov-report=html

# Run specific test file
uv run pytest tests/test_config.py

# Run tests in verbose mode
uv run pytest -v

# Or activate the virtual environment first
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pytest
```

### Continuous Integration

This project uses GitHub Actions to automatically run tests on:
- Push to `main`, `master`, or `develop` branches
- Pull requests to `main`, `master`, or `develop` branches

The CI workflow:
- Tests on multiple Python versions (3.10, 3.11, 3.12)
- Tests on Ubuntu and macOS
- Runs code coverage reports
- Runs linting checks (ruff and black)

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

