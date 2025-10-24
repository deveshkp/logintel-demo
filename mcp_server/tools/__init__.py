"""
MCP Tools Registry
Manages registration and discovery of all MCP tools
"""

from typing import Dict, Type, Any
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Registry for MCP tools"""

    def __init__(self):
        self._tools: Dict[str, Type[Any]] = {}

    def register(self, tool_class: Type[Any]) -> None:
        """Register an MCP tool class"""
        tool_name = getattr(tool_class, 'name', tool_class.__name__.lower())
        self._tools[tool_name] = tool_class
        logger.info(f"Registered MCP tool: {tool_name}")

    def get_tool(self, tool_name: str) -> Type[Any]:
        """Get a tool class by name"""
        return self._tools.get(tool_name)

    def get_all_tools(self) -> list:
        """Get all registered tool classes"""
        return list(self._tools.values())

    def list_tools(self) -> Dict[str, str]:
        """List all registered tools with descriptions"""
        return {
            name: getattr(tool_class, 'description', 'No description')
            for name, tool_class in self._tools.items()
        }

# Global tool registry instance
tool_registry = ToolRegistry()

# Import all tools to register them
from . import schema
from . import dictionary
from . import query
from . import kibana

# Manually register tools
tool_registry.register(schema.GetSchemaTool)
tool_registry.register(dictionary.GetDictionaryTool)
tool_registry.register(query.ExecuteESQueryTool)
tool_registry.register(kibana.CreateKibanaLinkTool)