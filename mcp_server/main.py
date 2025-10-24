"""
LogIntel - Banking Logs Intelligence Platform
FastAPI server exposing Elasticsearch and Kibana tools via Model Context Protocol
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import os
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Banking Logs MCP Server",
    description="Model Context Protocol server for banking log analysis",
    version="1.0.0"
)

# Add CORS middleware for UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # React dev server + production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment configuration
ES_URL = os.getenv("ES_URL", "http://elasticsearch:9200")
ES_USERNAME = os.getenv("ES_USERNAME", "")
ES_PASSWORD = os.getenv("ES_PASSWORD", "")
KIBANA_BASE_URL = os.getenv("KIBANA_BASE_URL", "http://localhost:5601")
KIBANA_DATA_VIEW_ID = os.getenv("KIBANA_DATA_VIEW_ID", "logs-*")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ALLOWED_INDEX_PATTERNS = os.getenv("ALLOWED_INDEX_PATTERNS", "logs-*").split(",")
MAX_RESULT_SIZE = int(os.getenv("MAX_RESULT_SIZE", "200"))

# Import MCP tools
from .tools import tool_registry
from .tools import schema  # Explicit import
from .tools import dictionary
from .tools import query
from .tools import kibana
from .tools import gemini

print("TOOLS IMPORTED IN MAIN")

# Register all MCP tools
for tool_class in tool_registry.get_all_tools():
    tool_instance = tool_class()
    logger.info(f"Registering MCP tool: {tool_instance.name}")

@app.get("/")
async def root():
    """Health check endpoint"""
    tools = tool_registry.list_tools()
    return {"status": "healthy", "service": "banking-logs-mcp-server", "tools": tools}

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "elasticsearch_url": ES_URL,
        "kibana_url": KIBANA_BASE_URL,
        "allowed_indices": ALLOWED_INDEX_PATTERNS,
        "max_result_size": MAX_RESULT_SIZE
    }

@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, request: Dict[str, Any]):
    """Execute an MCP tool"""
    # Log start of request processing with emojis for visibility
    logger.info(f"🔄 REQUEST: Execute tool '{tool_name}'")
    logger.debug(f"Request data: {request}")
    
    try:
        # Log tool initialization
        logger.info(f"🔍 Finding tool implementation for '{tool_name}'")
        tool_class = tool_registry.get_tool(tool_name)
        
        if not tool_class:
            logger.error(f"❌ Tool '{tool_name}' not found")
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

        logger.info(f"Instantiating tool: {tool_class}")
        tool_instance = tool_class()
        logger.info(f"Executing tool with request: {request}")
        result = await tool_instance.execute(request)

        logger.info(f"Executed tool {tool_name} with result: {type(result)}")
        return {"result": result}

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)