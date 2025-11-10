# Fax Image vCon Adapter

A file system monitoring adapter that watches for fax images, extracts sender/receiver information from filenames, creates vCon objects with file metadata, and posts them to a configurable HTTP conserver endpoint.

## Features

- **File System Monitoring**: Automatically detects new fax image files using `watchdog`
- **Filename Parsing**: Extracts sender and receiver phone numbers from filenames using configurable regex patterns
- **vCon Creation**: Creates standardized vCon objects with parties, attachments, and metadata
- **HTTP Posting**: Posts vCons to configurable conserver endpoints with authentication
- **State Tracking**: Prevents duplicate processing by tracking processed files
- **Flexible Configuration**: Environment-based configuration via `.env` file
- **Image Format Support**: Supports major image formats (JPG, PNG, GIF, TIFF, BMP, WebP)

## Installation

1. Clone or navigate to the repository:
```bash
cd vcon-fadapter
```

2. Install dependencies:
```bash
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

4. **HTTP Posting**: The vCon is posted to the configured conserver endpoint with authentication headers.

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
├── requirements.txt       # Dependencies
├── README.md             # This file
└── main.py               # Entry point
```

## License

[Add your license information here]

