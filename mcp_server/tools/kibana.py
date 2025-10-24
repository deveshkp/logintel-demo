"""
Create Kibana Link MCP Tool
Generates Kibana Discover and Lens links with filters applied
"""

from typing import Dict, Any, Optional
from urllib.parse import quote
import logging
from .base import MCPTool
from . import tool_registry

logger = logging.getLogger(__name__)

class CreateKibanaLinkTool(MCPTool):
    """Tool to create Kibana links with applied filters"""

    name = "create_kibana_link"
    description = "Create Kibana Discover or Lens links with filters and time range applied"

    def __init__(self):
        from ..main import KIBANA_BASE_URL, KIBANA_DATA_VIEW_ID
        self.kibana_base_url = KIBANA_BASE_URL
        self.data_view_id = KIBANA_DATA_VIEW_ID

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create Kibana link with applied filters"""
        # Handle UI parameters
        kql = args.get('kql_query', args.get('kql', ''))
        time_range = args.get('time_range', 'last_hour')
        view = args.get('view', 'discover')  # 'discover' or 'lens'

        # Convert time_range string to actual time bounds
        time_from, time_to = self._parse_time_range(time_range)

        try:
            if view == 'discover':
                link = self._create_discover_link(kql, time_from, time_to)
            elif view == 'lens':
                link = self._create_lens_link(kql, time_from, time_to)
            else:
                raise ValueError(f"Unsupported view type: {view}")

            result = {
                "kibana_link": link,  # UI expects kibana_link
                "view": view,
                "kql": kql,
                "time_range": {"from": time_from, "to": time_to}
            }

            self.log_execution(self.name, args, result)
            return result

        except Exception as e:
            logger.error(f"Error creating Kibana link: {e}")
            raise

    def _create_discover_link(self, kql: str, time_from: str, time_to: str) -> str:
        """Create Kibana Discover link"""
        # Time range parameters
        time_g = f"({{time:({{from:'{time_from}',to:'{time_to}'}})}})"

        # Query parameters with query, columns, and sort (no specific index to use default data view)
        query_a = "({{query:({{language:kql,query:'{0}'}}),columns:['@timestamp','event.action','event.outcome','app.channel','source.ip'],sort:[['@timestamp','desc']]}})".format(
            quote(kql)
        )

        return f"{self.kibana_base_url}/app/discover#/?_g={time_g}&_a={query_a}"

    def _create_lens_link(self, kql: str, time_from: str, time_to: str) -> str:
        """Create Kibana Lens link"""
        # Time range parameters
        time_g = f"({{time:({{from:'{time_from}',to:'{time_to}'}})}})"

        # For Lens, we use a simpler approach - can be extended for specific visualizations
        return f"{self.kibana_base_url}/app/lens#/?_g={time_g}"

    def _parse_time_range(self, time_range: str) -> tuple[str, str]:
        """Parse time_range string into from/to dates for Kibana URL"""
        if time_range == 'today':
            # From start of today to end of today
            return 'now/d', 'now/d+1d'
        elif time_range == 'last_hour':
            return 'now-1h', 'now'
        elif time_range == 'last_24h':
            return 'now-24h', 'now'
        elif time_range == 'all_time':
            # For banking logs, show last 90 days as "all time"
            return 'now-90d', 'now'
        else:
            # Default to last hour
            return 'now-1h', 'now'