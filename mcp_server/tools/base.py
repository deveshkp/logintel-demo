"""
Base MCP Tool Class
All MCP tools inherit from this base class
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class MCPTool(ABC):
    """Base class for all MCP tools"""

    name: str
    description: str

    @abstractmethod
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments"""
        pass

    def validate_input(self, args: Dict[str, Any], required_fields: list) -> None:
        """Validate that required fields are present in args"""
        missing = [field for field in required_fields if field not in args]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

    def validate_index_pattern(self, index_pattern: str) -> None:
        """Validate that index pattern is allowed"""
        from ..main import ALLOWED_INDEX_PATTERNS
        # Allow patterns that start with any allowed prefix
        allowed = False
        for pattern in ALLOWED_INDEX_PATTERNS:
            if pattern.endswith('*'):
                # For wildcard patterns, check if the pattern (without *) is a prefix
                prefix = pattern[:-1]
                if index_pattern.startswith(prefix):
                    allowed = True
                    break
            elif pattern == index_pattern:
                allowed = True
                break
        
        if not allowed:
            raise ValueError(f"Index pattern '{index_pattern}' not allowed. Allowed: {ALLOWED_INDEX_PATTERNS}")

    def log_execution(self, tool_name: str, args: Dict[str, Any], result: Any) -> None:
        """Log tool execution for audit purposes"""
        # Redact sensitive information from logs
        safe_args = {k: v for k, v in args.items() if k not in ['password', 'token']}
        
        # Log start of execution
        logger.info(f"🔧 MCP Tool '{tool_name}' STARTED")
        logger.debug(f"Arguments: {safe_args}")
        
        # Log result summary
        if isinstance(result, dict):
            summary = {k: v if not isinstance(v, (dict, list)) else f"[{type(v).__name__}]" 
                      for k, v in result.items()}
            logger.info(f"✅ MCP Tool '{tool_name}' COMPLETED - Result: {summary}")
        else:
            logger.info(f"✅ MCP Tool '{tool_name}' COMPLETED - Result type: {type(result)}")