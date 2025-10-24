# Banking Logs AI Demo

Natural language banking log analysis system using Elasticsearch, Kibana, and Google Gemini LLM via MCP (Model Context Protocol) server.

## Architecture

```
[React/Angular Chat UI]
        │  NL query
        ▼
     [Gemini LLM]
   (tool calls)
        │
        ▼
 [FastAPI MCP Server]
   ├─ get_schema()      → ES _mapping/_meta
   ├─ get_dictionary()  → meta-dictionary index
   ├─ execute_es_query()→ ES search/_count
   └─ create_kibana_link() → Kibana URL (Discover/Lens)
        │
        ├────────► [Elasticsearch]
        └────────► [Kibana]
```

## Quick Start

### 1. Environment Setup

```bash
# Clone and setup
git clone <repo>
cd banking-logs-ai-demo

# Start all services with Docker
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Load sample data
docker-compose exec mcp-server python scripts/seed_all_data.py
```

### 2. Access the Application

- **UI**: http://localhost:3000
- **MCP Server API**: http://localhost:8000
- **Kibana**: http://localhost:5601
- **Elasticsearch**: http://localhost:9200

### 3. Try Sample Queries

- "How many failed logins were there on mobile today?"
- "Show me payment failures from iOS devices"
- "What were the most common errors last hour?"

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for UI development)
- Python 3.11+ (for MCP server development)

### Local Development

```bash
# Start infrastructure services
docker-compose up -d elasticsearch kibana

# Install Python dependencies
pip install -r requirements.txt

# Start MCP server
uvicorn mcp_server.main:app --reload --host 0.0.0.0 --port 8000

# Install UI dependencies (in another terminal)
cd ui && npm install

# Start UI development server
npm start
```

### Data Seeding

```bash
# Load all sample data
python scripts/seed_all_data.py

# Load specific index data
python scripts/seed_data.py --index logs-auth-2025.10.22
```

## API Endpoints

### MCP Server

- `GET /` - Health check
- `GET /health` - Detailed health status
- `POST /tools/{tool_name}` - Execute MCP tool

### Available MCP Tools

1. **get_schema** - Get Elasticsearch index schema and metadata
2. **get_dictionary** - Get field synonyms and enums from meta-dictionary
3. **execute_es_query** - Execute Elasticsearch DSL queries
4. **create_kibana_link** - Generate Kibana Discover/Lens links

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional (defaults provided)
ES_URL=http://localhost:9200
KIBANA_BASE_URL=http://localhost:5601
ALLOWED_INDEX_PATTERNS=logs-*,meta-dictionary
MAX_RESULT_SIZE=200
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Project Structure

```
├── mcp_server/           # FastAPI MCP server
│   ├── tools/            # MCP tool implementations
│   └── main.py           # Server entry point
├── ui/                   # React frontend
│   ├── src/             # Source code
│   └── public/          # Static assets
├── elasticsearch/        # ES templates & config
├── scripts/             # Data seeding scripts
├── tests/               # Test suites
├── docker/              # Docker configurations
└── docker-compose.yml   # Service orchestration
```

## Security & Compliance

- PII fields automatically masked in responses
- Query validation against allowlists
- RBAC-ready architecture for tenant isolation
- Audit logging for all operations

## Contributing

1. Follow the established patterns in the codebase
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure Docker compatibility

## License

[Add your license here]