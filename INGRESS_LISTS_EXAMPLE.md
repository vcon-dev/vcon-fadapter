# Ingress Lists Configuration Examples

## What are Ingress Lists?

Ingress lists are processing queues in the vCon server that determine how vCons are processed after they are created. By specifying ingress lists in the fax adapter configuration, you can automatically route incoming fax vCons to specific processing chains.

## Configuration Format

The `INGRESS_LISTS` environment variable accepts a comma-separated list of ingress queue names:

```env
INGRESS_LISTS=queue1,queue2,queue3
```

## Common Use Cases

### 1. Fax-Specific Processing
Route all fax vCons to a dedicated fax processing chain:

```env
INGRESS_LISTS=fax_processing
```

This might trigger:
- Fax-specific OCR processing
- Fax metadata extraction
- Fax delivery confirmation handling

### 2. Multiple Processing Chains
Route fax vCons through multiple processing chains:

```env
INGRESS_LISTS=fax_processing,transcription,analysis
```

The vCon server will add the vCon to all specified queues, allowing parallel processing.

### 3. Priority Routing
Include priority or backup queues:

```env
INGRESS_LISTS=high_priority_fax,main_processing,backup_queue
```

### 4. No Routing (Default)
Leave empty or unset for default server behavior:

```env
INGRESS_LISTS=
```

Or simply omit the line entirely.

## Complete Configuration Example

Here's a complete `.env` file for a production fax adapter:

```env
# Required Settings
WATCH_DIRECTORY=/var/fax/incoming
CONSERVER_URL=https://vcon-server.example.com/api/vcon

# Authentication
CONSERVER_API_TOKEN=your-production-api-token-here
CONSERVER_HEADER_NAME=x-conserver-api-token

# Ingress Queue Routing
INGRESS_LISTS=fax_processing,medical_records,compliance_check

# File Management
DELETE_AFTER_SEND=true
PROCESS_EXISTING=true
STATE_FILE=/var/fax/fax_adapter_state.json

# Monitoring
POLL_INTERVAL=1.0

# Format Support
FILENAME_PATTERN=(\d+)_(\d+)\.(jpg|jpeg|png|gif|tiff|tif|bmp|webp)
SUPPORTED_FORMATS=jpg,jpeg,png,gif,tiff,tif,bmp,webp
```

## How It Works

When the adapter processes a fax image:

1. **File Detection**: Adapter detects new fax image `15085551212_15085551313.jpg`
2. **vCon Creation**: Creates vCon with sender/receiver parties and image attachment
3. **HTTP POST**: Posts to server with ingress lists parameter:
   ```
   POST https://vcon-server.example.com/api/vcon?ingress_lists=fax_processing,medical_records
   ```
4. **Server Processing**: The vCon server adds the vCon to all specified ingress queues
5. **Chain Execution**: Each processing chain processes the vCon according to its configuration

## Logging

When ingress lists are configured, the adapter logs:

```
INFO - Posting vCon 550e8400-e29b-41d4-a716-446655440000 to https://vcon-server.example.com/api/vcon with ingress_lists: fax_processing, medical_records
```

Without ingress lists:

```
INFO - Posting vCon 550e8400-e29b-41d4-a716-446655440000 to https://vcon-server.example.com/api/vcon
```

## Troubleshooting

### Issue: vCons not being processed
- **Check**: Verify the ingress queue names match exactly with server configuration
- **Check**: Ensure the queues are active and have processing chains configured
- **Check**: Review server logs to see if vCons are being added to queues

### Issue: Invalid ingress list names
- **Symptom**: Server returns 400 or 404 errors
- **Solution**: Verify queue names against server's configured chains
- **Solution**: Check for typos or extra whitespace (though adapter trims whitespace)

### Issue: Whitespace in queue names
The adapter automatically strips whitespace:

```env
# These are equivalent:
INGRESS_LISTS=fax_processing,main_ingress
INGRESS_LISTS= fax_processing , main_ingress 
```

## API Reference

This feature corresponds to the vCon server API:

```http
POST /api/vcon?ingress_lists=queue1,queue2

Headers:
  x-conserver-api-token: your-token
  Content-Type: application/json

Body:
  {vCon JSON object}
```

See the vCon server API documentation for more details on ingress queue behavior.

