"""
Integration tests for Banking Logs AI Demo
Tests end-to-end functionality from UI to Elasticsearch
"""

import pytest
import requests
import time
import json
from elasticsearch import Elasticsearch


class TestBankingLogsIntegration:
    """Integration tests for the complete banking logs AI system"""

    @pytest.fixture(scope="class")
    def es_client(self):
        """Elasticsearch client fixture"""
        es = Elasticsearch("http://localhost:9200", verify_certs=False)
        # Wait for ES to be ready
        for _ in range(30):
            try:
                if es.ping():
                    break
            except:
                time.sleep(1)
        else:
            pytest.skip("Elasticsearch not available")
        return es

    @pytest.fixture(scope="class")
    def mcp_client(self):
        """MCP server client fixture"""
        base_url = "http://localhost:8000"
        # Wait for MCP server to be ready
        for _ in range(30):
            try:
                response = requests.get(f"{base_url}/health")
                if response.status_code == 200:
                    break
            except:
                time.sleep(1)
        else:
            pytest.skip("MCP server not available")
        return base_url

    def test_elasticsearch_connection(self, es_client):
        """Test Elasticsearch connectivity"""
        assert es_client.ping(), "Elasticsearch should be reachable"

    def test_mcp_server_health(self, mcp_client):
        """Test MCP server health endpoint"""
        response = requests.get(f"{mcp_client}/health")
        assert response.status_code == 200

        data = response.json()
        assert "elasticsearch_url" in data
        assert "kibana_url" in data
        assert "allowed_indices" in data

    def test_get_schema_tool(self, mcp_client, es_client):
        """Test get_schema MCP tool"""
        # First ensure we have some data
        if not es_client.indices.exists(index="logs-auth-*"):
            pytest.skip("No test data available - run seed_all_data.py first")

        payload = {"index_pattern": "logs-auth-*"}
        response = requests.post(
            f"{mcp_client}/tools/get_schema",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()["result"]

        assert "fields" in data
        assert "@timestamp" in data["fields"]
        assert "event.action" in data["fields"]
        assert "meta" in data

    def test_get_dictionary_tool(self, mcp_client):
        """Test get_dictionary MCP tool"""
        payload = {"domain": "authentication"}
        response = requests.post(
            f"{mcp_client}/tools/get_dictionary",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()["result"]

        # Should contain authentication-related fields
        assert isinstance(data, dict)
        # At minimum should have some fields if meta-dictionary is seeded

    def test_execute_query_tool(self, mcp_client, es_client):
        """Test execute_es_query MCP tool"""
        if not es_client.indices.exists(index="logs-*"):
            pytest.skip("No test data available - run seed_all_data.py first")

        # Simple count query
        dsl = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"event.outcome": "failure"}},
                        {"range": {"@timestamp": {"gte": "now/d", "lt": "now+1d/d"}}}
                    ]
                }
            },
            "size": 0,
            "aggs": {"count": {"value_count": {"field": "event.action"}}}
        }

        payload = {
            "index": "logs-*",
            "dsl": dsl
        }

        response = requests.post(
            f"{mcp_client}/tools/execute_es_query",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()["result"]

        assert "total" in data
        assert "aggregations" in data
        assert isinstance(data["total"], int)

    def test_create_kibana_link_tool(self, mcp_client):
        """Test create_kibana_link MCP tool"""
        payload = {
            "kql": "event.outcome:failure AND app.channel:mobile",
            "time_from": "now/d",
            "time_to": "now+1d/d",
            "view": "discover"
        }

        response = requests.post(
            f"{mcp_client}/tools/create_kibana_link",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()["result"]

        assert "link" in data
        assert "view" in data
        assert "kql" in data
        assert "time_range" in data
        assert data["link"].startswith("http://localhost:5601")

    def test_query_validation(self, mcp_client):
        """Test query safety validation"""
        # Try to execute a potentially unsafe query
        dsl = {
            "query": {"match_all": {}},
            "size": 10000  # Too large
        }

        payload = {
            "index": "logs-*",
            "dsl": dsl
        }

        response = requests.post(
            f"{mcp_client}/tools/execute_es_query",
            json=payload
        )

        # Should either succeed with size limits applied or fail safely
        assert response.status_code in [200, 400]

    def test_index_allowlist(self, mcp_client):
        """Test index pattern allowlist validation"""
        # Try to access a disallowed index
        payload = {"index_pattern": "secret-index"}
        response = requests.post(
            f"{mcp_client}/tools/get_schema",
            json=payload
        )

        # Should fail due to allowlist validation
        assert response.status_code == 500  # Internal server error from validation

    @pytest.mark.parametrize("query_type", [
        "failed_login_mobile_today",
        "payment_failures_ios",
        "errors_last_hour"
    ])
    def test_end_to_end_query_flow(self, mcp_client, es_client, query_type):
        """Test complete query flow simulation"""
        if not es_client.indices.exists(index="logs-*"):
            pytest.skip("No test data available - run seed_all_data.py first")

        # Simulate different query types
        query_configs = {
            "failed_login_mobile_today": {
                "dsl": {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"event.outcome": "failure"}},
                                {"term": {"app.channel": "mobile"}},
                                {"range": {"@timestamp": {"gte": "now/d", "lt": "now+1d/d"}}}
                            ]
                        }
                    },
                    "size": 0,
                    "aggs": {"count": {"value_count": {"field": "event.action"}}}
                },
                "expected_count": True
            },
            "payment_failures_ios": {
                "dsl": {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"event.outcome": "failure"}},
                                {"term": {"event.action": "payment_failed"}},
                                {"term": {"device.os.name": "iOS"}}
                            ]
                        }
                    },
                    "size": 10
                },
                "expected_count": False
            },
            "errors_last_hour": {
                "dsl": {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"event.outcome": "failure"}},
                                {"range": {"@timestamp": {"gte": "now-1h"}}}
                            ]
                        }
                    },
                    "size": 0,
                    "aggs": {"error_types": {"terms": {"field": "event.reason"}}}
                },
                "expected_count": True
            }
        }

        config = query_configs[query_type]

        # Execute query
        payload = {
            "index": "logs-*",
            "dsl": config["dsl"]
        }

        response = requests.post(
            f"{mcp_client}/tools/execute_es_query",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()["result"]

        # Validate response structure
        assert "total" in data
        assert "hits" in data
        assert "aggregations" in data if "aggs" in config["dsl"] else True

        # If expecting count aggregation, verify it exists
        if config["expected_count"] and "aggs" in config["dsl"]:
            assert "count" in data["aggregations"] or "error_types" in data["aggregations"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])