"""
Get Dictionary MCP Tool
Retrieves field synonyms, enums, and domain information from meta-dictionary
"""

from typing import Dict, Any, Optional, List
from elasticsearch import Elasticsearch
import logging
from .base import MCPTool
from . import tool_registry

logger = logging.getLogger(__name__)

class GetDictionaryTool(MCPTool):
    """Tool to get field dictionary and synonyms"""

    name = "get_dictionary"
    description = "Get field synonyms, enums, and domain information from meta-dictionary"

    def __init__(self):
        from ..main import ES_URL, ES_USERNAME, ES_PASSWORD
        self.es = Elasticsearch(
            ES_URL,
            basic_auth=(ES_USERNAME, ES_PASSWORD) if ES_USERNAME else None,
            verify_certs=False
        )

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get dictionary entries for specified domains or fields"""
        domain = args.get('domain')
        fields = args.get('fields', [])

        try:
            # Query meta-dictionary index
            query = self._build_dictionary_query(domain, fields)
            response = self.es.search(
                index="meta-dictionary",
                body=query,
                size=1000
            )

            # Process results
            dictionary = self._process_dictionary_results(response)

            self.log_execution(self.name, args, dictionary)
            return dictionary

        except Exception as e:
            logger.error(f"Error getting dictionary: {e}")
            raise

    def _build_dictionary_query(self, domain: Optional[str], fields: List[str]) -> Dict[str, Any]:
        """Build Elasticsearch query for dictionary lookup"""
        must_clauses = []

        if domain:
            must_clauses.append({"term": {"domain": domain}})

        if fields:
            must_clauses.append({"terms": {"field": fields}})

        if not must_clauses:
            # Return all dictionary entries if no filters specified
            return {"query": {"match_all": {}}}

        return {
            "query": {
                "bool": {
                    "must": must_clauses
                }
            }
        }

    def _process_dictionary_results(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process Elasticsearch response into dictionary format"""
        dictionary = {}

        for hit in response['hits']['hits']:
            doc = hit['_source']
            field_name = doc['field']

            dictionary[field_name] = {
                "description": doc.get("description", ""),
                "valid_values": doc.get("valid_values", []),
                "synonyms": doc.get("synonyms", []),
                "example": doc.get("example", ""),
                "domain": doc.get("domain", "")
            }

        return dictionary