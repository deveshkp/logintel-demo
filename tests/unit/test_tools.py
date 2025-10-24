"""
Unit tests for MCP tools
"""

import pytest
from unittest.mock import Mock, patch
from mcp_server.tools.schema import GetSchemaTool
from mcp_server.tools.dictionary import GetDictionaryTool
from mcp_server.tools.query import ExecuteESQueryTool
from mcp_server.tools.kibana import CreateKibanaLinkTool


class TestGetSchemaTool:
    """Test cases for GetSchemaTool"""

    @pytest.fixture
    def tool(self):
        return GetSchemaTool()

    @patch('mcp_server.tools.schema.Elasticsearch')
    def test_execute_success(self, mock_es_class, tool):
        """Test successful schema retrieval"""
        # Mock Elasticsearch client
        mock_es = Mock()
        mock_es_class.return_value = mock_es

        # Mock index mapping response
        mock_mapping = {
            "logs-auth-2025.10.22": {
                "mappings": {
                    "_meta": {
                        "default_time_field": "@timestamp",
                        "primary_facets": ["event.outcome"]
                    },
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "event.action": {"type": "keyword"}
                    }
                }
            }
        }
        mock_es.indices.get_mapping.return_value = mock_mapping

        result = tool.execute({"index_pattern": "logs-auth-*"})

        assert "fields" in result
        assert "@timestamp" in result["fields"]
        assert "event.action" in result["fields"]
        assert result["meta"]["default_time_field"] == "@timestamp"

    def test_validate_index_pattern_valid(self, tool):
        """Test valid index pattern validation"""
        # Should not raise exception
        tool.validate_index_pattern("logs-auth-*")

    def test_validate_index_pattern_invalid(self, tool):
        """Test invalid index pattern validation"""
        with pytest.raises(ValueError, match="not allowed"):
            tool.validate_index_pattern("invalid-index")


class TestGetDictionaryTool:
    """Test cases for GetDictionaryTool"""

    @pytest.fixture
    def tool(self):
        return GetDictionaryTool()

    @patch('mcp_server.tools.dictionary.Elasticsearch')
    def test_execute_with_domain_filter(self, mock_es_class, tool):
        """Test dictionary retrieval with domain filter"""
        mock_es = Mock()
        mock_es_class.return_value = mock_es

        mock_response = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "field": "event.action",
                            "domain": "authentication",
                            "valid_values": ["login", "logout"],
                            "synonyms": ["signin"]
                        }
                    }
                ]
            }
        }
        mock_es.search.return_value = mock_response

        result = tool.execute({"domain": "authentication"})

        assert "event.action" in result
        assert result["event.action"]["domain"] == "authentication"
        assert "login" in result["event.action"]["valid_values"]


class TestExecuteESQueryTool:
    """Test cases for ExecuteESQueryTool"""

    @pytest.fixture
    def tool(self):
        return ExecuteESQueryTool()

    @patch('mcp_server.tools.query.Elasticsearch')
    def test_execute_count_query(self, mock_es_class, tool):
        """Test successful query execution"""
        mock_es = Mock()
        mock_es_class.return_value = mock_es

        mock_response = {
            "took": 15,
            "timed_out": False,
            "hits": {
                "total": {"value": 0},
                "hits": []
            },
            "aggregations": {
                "count": {"value": 1294}
            }
        }
        mock_es.search.return_value = mock_response

        dsl = {
            "query": {"match_all": {}},
            "size": 0,
            "aggs": {"count": {"value_count": {"field": "event.action"}}}
        }

        result = tool.execute({"index": "logs-*", "dsl": dsl})

        assert result["took"] == 15
        assert result["total"] == 0
        assert result["count"] == 1294
        assert len(result["hits"]) == 0

    def test_validate_query_safety_valid(self, tool):
        """Test valid query safety validation"""
        dsl = {
            "query": {"term": {"event.outcome": "failure"}},
            "size": 10,
            "aggs": {"count": {"value_count": {"field": "event.action"}}}
        }

        # Should not raise exception
        tool._validate_query_safety(dsl)

    def test_validate_query_safety_script_injection(self, tool):
        """Test script injection prevention"""
        dsl = {
            "query": {
                "script": {
                    "script": "doc['field'].value == 'malicious'"
                }
            }
        }

        with pytest.raises(ValueError, match="Script operations not allowed"):
            tool._validate_query_safety(dsl)

    def test_validate_query_safety_too_many_aggs(self, tool):
        """Test aggregation limit validation"""
        dsl = {
            "aggs": {f"agg_{i}": {"terms": {"field": "field"}} for i in range(10)}
        }

        with pytest.raises(ValueError, match="Maximum 5 aggregations"):
            tool._validate_query_safety(dsl)


class TestCreateKibanaLinkTool:
    """Test cases for CreateKibanaLinkTool"""

    @pytest.fixture
    def tool(self):
        return CreateKibanaLinkTool()

    def test_create_discover_link(self, tool):
        """Test Kibana Discover link creation"""
        result = tool.execute({
            "kql": "event.outcome:failure",
            "time_from": "now/d",
            "time_to": "now+1d/d",
            "view": "discover"
        })

        assert "link" in result
        assert result["view"] == "discover"
        assert "localhost:5601" in result["link"]
        assert "_g=" in result["link"]  # Time range parameter
        assert "_a=" in result["link"]  # Query parameters

    def test_create_lens_link(self, tool):
        """Test Kibana Lens link creation"""
        result = tool.execute({
            "kql": "event.outcome:failure",
            "time_from": "now-1h",
            "time_to": "now",
            "view": "lens"
        })

        assert "link" in result
        assert result["view"] == "lens"
        assert "localhost:5601" in result["link"]
        assert "app/lens" in result["link"]


class TestToolValidation:
    """Test input validation across tools"""

    def test_required_fields_validation(self):
        """Test required fields validation"""
        tool = GetSchemaTool()

        # Should raise for missing required field
        with pytest.raises(ValueError, match="Missing required fields"):
            tool.validate_input({}, ["index_pattern"])

        # Should pass with required field
        tool.validate_input({"index_pattern": "logs-*"}, ["index_pattern"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])