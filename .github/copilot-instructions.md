# Banking Logs AI Demo - Copilot Instructions

## Project Overview
Natural language banking log analysis system using Elasticsearch, Kibana, and Google Gemini LLM via MCP (Model Context Protocol) server.

**Architecture:** React/Angular UI → Gemini LLM → FastAPI MCP Server → Elasticsearch + Kibana

## Key Technologies & Patterns

### Core Stack
- **Frontend:** React/Angular single-page app with chat interface
- **LLM:** Google Gemini for natural language query interpretation
- **Backend:** FastAPI MCP server exposing Elasticsearch/Kibana tools
- **Data Store:** Elasticsearch with ECS-style banking log mappings
- **Visualization:** Kibana for log exploration and dashboards

### Data Flow Pattern
```python
# Standard query processing flow
user_query → gemini_with_context → mcp_tools → elasticsearch → kibana_links → ui_response
```

## Development Workflow

### Environment Setup
```bash
# Clone and setup
git clone <repo>
cd banking-logs-ai-demo

# Start services (Docker Compose assumed)
docker-compose up -d elasticsearch kibana

# Install Python dependencies
pip install fastapi uvicorn elasticsearch python-multipart pydantic

# For UI development
npm install  # or yarn install
npm start    # React/Angular dev server
```

### Data Seeding Scripts

**`scripts/seed_all_data.py`** - Loads sample data across all required indices:
```python
# Creates and populates these indices with realistic banking log data:
# - logs-auth-* (authentication events: login, logout, password reset)
# - logs-mobile-* (mobile app events: transactions, session activity)  
# - logs-payment-* (payment processing events: transfers, card payments)
# - meta-dictionary (field mappings, synonyms, enums for LLM context)

# Sample data includes:
# - Today's events with realistic timestamps
# - Mix of success/failure outcomes
# - Various app channels (mobile, online, ivr)
# - Geographic and device information
# - PII-safe synthetic data
```

**`scripts/seed_data.py`** - Loads data for a specific index pattern:
```bash
# Load auth logs for today
python scripts/seed_data.py --index logs-auth-2025.10.22

# Load mobile logs for yesterday  
python scripts/seed_data.py --index logs-mobile-2025.10.21
```

## Code Structure & Conventions

### Directory Layout
```
├── mcp_server/           # FastAPI MCP server
│   ├── tools/            # MCP tool implementations
│   │   ├── schema.py     # get_schema tool
│   │   ├── dictionary.py # get_dictionary tool
│   │   ├── query.py      # execute_es_query tool
│   │   └── kibana.py     # create_kibana_link tool
│   └── main.py           # FastAPI app with MCP endpoints
├── ui/                   # React/Angular frontend
│   ├── components/       # Chat UI components
│   └── services/         # API client for MCP server
├── elasticsearch/        # ES index templates & mappings
│   ├── templates/        # Index templates with _meta
│   └── data/            # Sample data seeding scripts
├── docker/              # Docker configs
└── tests/               # Test suites
    ├── integration/     # End-to-end tests
    └── unit/           # Component tests
```

### MCP Tool Implementation Pattern
```python
# Standard MCP tool structure
from mcp import Tool
from pydantic import BaseModel

class ToolArgs(BaseModel):
    index_pattern: str
    # ... other args

@tool_registry.register
class GetSchemaTool(Tool):
    name = "get_schema"
    description = "Get Elasticsearch schema and metadata"

    def execute(self, args: ToolArgs) -> dict:
        # Validate inputs against allowlists
        validate_index_pattern(args.index_pattern)

        # Query Elasticsearch
        mapping = es.indices.get_mapping(index=args.index_pattern)

        # Return curated schema + _meta
        return extract_schema_with_meta(mapping)
```

### Error Handling Pattern
```python
# Always validate inputs and handle ES errors
try:
    result = es.search(index=index, body=dsl_query)
except elasticsearch.NotFoundError:
    raise HTTPException(status_code=404, detail=f"Index {index} not found")
except elasticsearch.RequestError as e:
    logger.error(f"Invalid DSL: {e}")
    raise HTTPException(status_code=400, detail="Invalid query structure")
```

## Critical Implementation Details

### Security & Validation
- **Input Validation:** All MCP tool inputs validated against allowlists
- **RBAC Injection:** Server-side tenant/environment filters added to queries
- **PII Protection:** Raw `message` fields excluded from responses
- **Query Limits:** Max 200 results, prefer `_count` for aggregations

### Elasticsearch Patterns
```python
# Time range normalization
time_filters = {
    "today": {"gte": "now/d", "lt": "now+1d/d"},
    "last_hour": {"gte": "now-1h"}
}

# Safe query structure
query = {
    "query": {
        "bool": {
            "must": [
                {"term": {"event.outcome": "failure"}},
                {"term": {"app.channel": "mobile"}},
                {"range": {"@timestamp": time_filters["today"]}}
            ]
        }
    },
    "size": 0,  # For counts only
    "aggs": {"count": {"value_count": {"field": "event.action"}}}
}
```

### Kibana Link Generation
```python
# Discover URL pattern
kibana_url = f"{KIBANA_BASE_URL}/app/discover#/?_g=(time:(from:'{time_from}',to:'{time_to}'))&_a=(query:(language:kql,query:'{kql}'))"

# Lens URL for visualizations
lens_url = f"{KIBANA_BASE_URL}/app/lens#/?_g=(time:(from:'{time_from}',to:'{time_to}'))"
```

## Common Patterns & Gotchas

### LLM Context Management
- **Schema First:** Always fetch current schema before query construction
- **Dictionary Lookup:** Use meta-dictionary for field synonyms and enums
- **Auto-suggest:** If a field is missing in schema, return "field not found—did you mean ...?" via dictionary lookup
- **Few-shot Examples:** Include 2-3 query→DSL mappings in prompts
- **Time Defaults:** Use "now-1h" for incident queries without explicit time

### Auto-suggest Implementation
```python
# Field validation with suggestions
def validate_field_with_suggestions(field_name: str, available_fields: dict) -> dict:
    if field_name in available_fields:
        return {"valid": True, "field": field_name}
    
    # Search dictionary for similar fields
    suggestions = find_similar_fields(field_name, available_fields)
    
    if suggestions:
        return {
            "valid": False,
            "error": f"field '{field_name}' not found—did you mean {', '.join(suggestions[:3])}?"
        }
    
    return {"valid": False, "error": f"field '{field_name}' not found"}

def find_similar_fields(target_field: str, available_fields: dict) -> list:
    # Fuzzy matching against field names and synonyms
    suggestions = []
    for field, metadata in available_fields.items():
        if target_field.lower() in field.lower():
            suggestions.append(field)
        # Check synonyms in meta-dictionary
        if "synonyms" in metadata:
            for synonym in metadata["synonyms"]:
                if target_field.lower() in synonym.lower():
                    suggestions.append(field)
    return list(set(suggestions))  # Remove duplicates
```
```python
# Integration test pattern
def test_failed_login_query():
    # Setup: seed test data
    seed_sample_logs()

    # Execute: simulate full query flow
    response = client.post("/query", json={"text": "failed logins today"})

    # Assert: verify count matches Kibana
    assert response.status_code == 200
    assert "count" in response.json()
    assert response.json()["kibana_link"] is not None
```

### Docker Development
```yaml
# docker-compose.yml pattern
version: '3.8'
services:
  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports: ["9200:9200"]

  kibana:
    image: kibana:8.11.0
    depends_on: [elasticsearch]
    ports: ["5601:5601"]
```

## Key Files to Reference

### Core Implementation
- `mcp_server/main.py` - FastAPI app setup and MCP integration
- `mcp_server/tools/query.py` - Elasticsearch query execution
- `elasticsearch/templates/logs-template.json` - Index mapping with _meta
- `ui/src/services/McpClient.js` - Frontend API integration

### Configuration
- `docker-compose.yml` - Local development environment
- `.env.example` - Required environment variables
- `tests/integration/test_queries.py` - End-to-end test examples

## Development Best Practices

- **Validate Early:** Check ES connectivity and schema before implementing tools
- **Test with Kibana:** Always verify queries work in Kibana Discover first
- **Handle Time Zones:** Use Elasticsearch time zone functions, not client-side conversion
- **Log Everything:** Include user prompts, tool calls, and ES performance in logs
- **Size Limits:** Never return more than 200 documents; use aggregations for summaries

---

*Update this file as the codebase evolves. Focus on patterns that help AI agents be immediately productive.*
