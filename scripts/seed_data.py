#!/usr/bin/env python3
"""
Seed Data Script
Loads sample banking log data for a specific Elasticsearch index
"""

import argparse
import json
import random
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndexDataSeeder:
    """Seeds sample data for a specific Elasticsearch index"""

    def __init__(self, es_url: str = "http://localhost:9200", username: str = "", password: str = ""):
        self.es = Elasticsearch(
            es_url,
            basic_auth=(username, password) if username else None,
            verify_certs=False
        )

    def seed_index_data(self, index_pattern: str) -> None:
        """Seed data for a specific index pattern"""
        logger.info(f"Seeding data for index pattern: {index_pattern}")

        # Determine index type and seed appropriate data
        if "auth" in index_pattern:
            self._seed_auth_data(index_pattern)
        elif "mobile" in index_pattern:
            self._seed_mobile_data(index_pattern)
        elif "payment" in index_pattern:
            self._seed_payment_data(index_pattern)
        elif "meta-dictionary" in index_pattern:
            self._seed_dictionary_data(index_pattern)
        else:
            raise ValueError(f"Unknown index pattern type: {index_pattern}")

    def _seed_auth_data(self, index_pattern: str) -> None:
        """Seed authentication data"""
        docs = self._generate_auth_events()
        self._bulk_index(index_pattern, docs)
        logger.info(f"Seeded {len(docs)} auth events into {index_pattern}")

    def _seed_mobile_data(self, index_pattern: str) -> None:
        """Seed mobile app data"""
        docs = self._generate_mobile_events()
        self._bulk_index(index_pattern, docs)
        logger.info(f"Seeded {len(docs)} mobile events into {index_pattern}")

    def _seed_payment_data(self, index_pattern: str) -> None:
        """Seed payment data"""
        docs = self._generate_payment_events()
        self._bulk_index(index_pattern, docs)
        logger.info(f"Seeded {len(docs)} payment events into {index_pattern}")

    def _seed_dictionary_data(self, index_pattern: str) -> None:
        """Seed meta-dictionary data"""
        docs = self._generate_dictionary_entries()
        self._bulk_index(index_pattern, docs)
        logger.info(f"Seeded {len(docs)} dictionary entries into {index_pattern}")

    def _generate_auth_events(self, num_events: int = 100) -> List[Dict[str, Any]]:
        """Generate sample authentication events"""
        docs = []
        actions = ["user_login", "user_logout", "password_reset"]
        outcomes = ["success", "failure"]
        channels = ["mobile", "online", "ivr"]
        devices = ["iOS", "Android", "Windows", "macOS"]
        cities = ["New York", "London", "Tokyo", "Singapore"]

        for i in range(num_events):
            timestamp = datetime.now() - timedelta(minutes=random.randint(0, 1440))  # Last 24 hours

            doc = {
                "@timestamp": timestamp.isoformat(),
                "event": {
                    "action": random.choice(actions),
                    "outcome": random.choice(outcomes)
                },
                "app": {
                    "channel": random.choice(channels),
                    "name": "banking-app"
                },
                "user": {
                    "id": f"user_{random.randint(1000, 9999)}"
                },
                "source": {
                    "ip": f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
                },
                "device": {
                    "os": {
                        "name": random.choice(devices)
                    }
                },
                "geo": {
                    "city_name": random.choice(cities)
                }
            }

            docs.append(doc)

        return docs

    def _generate_mobile_events(self, num_events: int = 150) -> List[Dict[str, Any]]:
        """Generate sample mobile app events"""
        docs = []
        actions = ["app_launch", "transaction_view", "account_check", "session_start"]
        outcomes = ["success", "failure"]
        devices = ["iOS", "Android"]
        cities = ["New York", "London", "Tokyo", "Singapore"]

        for i in range(num_events):
            timestamp = datetime.now() - timedelta(minutes=random.randint(0, 1440))

            doc = {
                "@timestamp": timestamp.isoformat(),
                "event": {
                    "action": random.choice(actions),
                    "outcome": random.choice(outcomes)
                },
                "app": {
                    "channel": "mobile",
                    "name": "mobile-banking",
                    "version": f"{random.randint(1, 5)}.{random.randint(0, 9)}"
                },
                "user": {
                    "id": f"user_{random.randint(1000, 9999)}"
                },
                "device": {
                    "os": {
                        "name": random.choice(devices)
                    }
                },
                "geo": {
                    "city_name": random.choice(cities)
                }
            }

            docs.append(doc)

        return docs

    def _generate_payment_events(self, num_events: int = 50) -> List[Dict[str, Any]]:
        """Generate sample payment events"""
        docs = []
        actions = ["payment_initiated", "payment_completed", "payment_failed"]
        outcomes = ["success", "failure"]
        channels = ["mobile", "online", "ivr"]

        for i in range(num_events):
            timestamp = datetime.now() - timedelta(minutes=random.randint(0, 1440))

            doc = {
                "@timestamp": timestamp.isoformat(),
                "event": {
                    "action": random.choice(actions),
                    "outcome": random.choice(outcomes)
                },
                "app": {
                    "channel": random.choice(channels),
                    "name": "payment-service"
                },
                "transaction": {
                    "amount": round(random.uniform(10.0, 10000.0), 2),
                    "currency": "USD"
                },
                "user": {
                    "id": f"user_{random.randint(1000, 9999)}"
                }
            }

            docs.append(doc)

        return docs

    def _generate_dictionary_entries(self) -> List[Dict[str, Any]]:
        """Generate meta-dictionary entries"""
        return [
            {
                "field": "event.action",
                "description": "The action performed by the user or system",
                "valid_values": ["user_login", "user_logout", "password_reset", "app_launch", "transaction_view", "payment_initiated", "payment_completed"],
                "synonyms": ["action", "operation", "event_type", "signin", "sign-in", "login"],
                "example": "user_login",
                "domain": "authentication"
            },
            {
                "field": "event.outcome",
                "description": "The result of the event (success or failure)",
                "valid_values": ["success", "failure"],
                "synonyms": ["result", "status", "outcome", "successful", "failed", "error"],
                "example": "success",
                "domain": "general"
            },
            {
                "field": "app.channel",
                "description": "The application channel used",
                "valid_values": ["mobile", "online", "ivr"],
                "synonyms": ["channel", "platform", "app_type", "mobile banking", "web", "internet banking"],
                "example": "mobile",
                "domain": "channels"
            }
        ]

    def _bulk_index(self, index_name: str, docs: List[Dict[str, Any]]) -> None:
        """Bulk index documents into Elasticsearch"""
        if not docs:
            return

        # Prepare bulk request body
        bulk_body = []
        for doc in docs:
            bulk_body.extend([
                {"create": {"_index": index_name}},
                doc
            ])

        # Execute bulk request
        response = self.es.bulk(body=bulk_body, refresh=True)

        if response.get("errors"):
            logger.error(f"Bulk indexing errors for {index_name}:")
            for item in response.get("items", []):
                if "error" in item.get("index", {}):
                    logger.error(f"Error: {json.dumps(item['index']['error'], indent=2)}")
        else:
            logger.info(f"Successfully indexed {len(docs)} documents into {index_name}")


def main():
    parser = argparse.ArgumentParser(description="Seed data for a specific Elasticsearch index")
    parser.add_argument("--index", required=True, help="Index pattern to seed (e.g., logs-auth-2025.10.22)")
    parser.add_argument("--es-url", default="http://localhost:9200", help="Elasticsearch URL")
    parser.add_argument("--username", default="", help="Elasticsearch username")
    parser.add_argument("--password", default="", help="Elasticsearch password")

    args = parser.parse_args()

    seeder = IndexDataSeeder(args.es_url, args.username, args.password)
    seeder.seed_index_data(args.index)


if __name__ == "__main__":
    main()