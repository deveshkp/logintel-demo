#!/usr/bin/env python3
"""
Seed All Data Script
Loads sample banking log data across all required Elasticsearch indices
"""

import argparse
import json
import os
import random
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BankingDataSeeder:
    """Seeds sample banking log data into Elasticsearch"""

    def __init__(self, es_url: str = None, username: str = "", password: str = ""):
        # Use environment variable or Docker service name
        if es_url is None:
            es_url = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
        
        self.es = Elasticsearch(
            es_url,
            basic_auth=(username, password) if username else None,
            verify_certs=False
        )

        # Sample data generators
        self.auth_actions = ["user_login", "user_logout", "password_reset"]
        self.outcomes = ["success", "failure"]
        self.channels = ["mobile", "online", "ivr"]
        self.failure_reasons = ["invalid_credentials", "account_locked", "session_expired", "network_error"]
        self.devices = ["iOS", "Android", "Windows", "macOS", "Linux"]
        self.cities = ["New York", "London", "Tokyo", "Singapore", "Sydney", "Berlin", "Paris"]

    def seed_all_data(self) -> None:
        """Seed data across all index types"""
        logger.info("Starting data seeding process...")

        # Skip template creation - templates are already set up via Docker
        # self._create_index_templates()

        # Seed data for today and yesterday
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        for date in [yesterday, today]:
            self._seed_auth_logs(date)
            self._seed_mobile_logs(date)
            self._seed_payment_logs(date)

        # Seed meta-dictionary
        self._seed_meta_dictionary()

        logger.info("Data seeding completed successfully!")

    def _create_index_templates(self) -> None:
        """Create Elasticsearch index templates"""
        templates = [
            self._get_auth_template(),
            self._get_mobile_template(),
            self._get_payment_template()
        ]

        for template in templates:
            template_name = template["name"]
            try:
                self.es.indices.put_template(name=template_name, body=template["body"])
                logger.info(f"Created template: {template_name}")
            except Exception as e:
                logger.error(f"Error creating template {template_name}: {e}")

    def _seed_auth_logs(self, date: datetime.date) -> None:
        """Seed authentication log data"""
        index_name = f"logs-auth-{date.isoformat()}"
        docs = []

        # Generate 100-200 auth events per day
        num_events = random.randint(100, 200)

        for i in range(num_events):
            timestamp = datetime.combine(date, datetime.min.time()) + timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )

            outcome = random.choice(self.outcomes)
            action = random.choice(self.auth_actions)

            doc = {
                "@timestamp": timestamp.isoformat(),
                "event": {
                    "action": action,
                    "outcome": outcome,
                    "reason": random.choice(self.failure_reasons) if outcome == "failure" else None
                },
                "app": {
                    "channel": random.choice(self.channels),
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
                        "name": random.choice(self.devices)
                    }
                },
                "geo": {
                    "city_name": random.choice(self.cities)
                },
                "trace": {
                    "id": f"trace_{random.randint(100000, 999999)}"
                }
            }

            docs.append(doc)

        self._bulk_index(index_name, docs)
        logger.info(f"Seeded {len(docs)} auth log events for {date}")

    def _seed_mobile_logs(self, date: datetime.date) -> None:
        """Seed mobile app log data"""
        index_name = f"logs-mobile-{date.isoformat()}"
        docs = []

        # Generate 150-300 mobile events per day
        num_events = random.randint(150, 300)

        for i in range(num_events):
            timestamp = datetime.combine(date, datetime.min.time()) + timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )

            doc = {
                "@timestamp": timestamp.isoformat(),
                "event": {
                    "action": random.choice(["app_launch", "transaction_view", "account_check", "session_start"]),
                    "outcome": random.choice(self.outcomes)
                },
                "app": {
                    "channel": "mobile",
                    "name": "mobile-banking",
                    "version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
                },
                "user": {
                    "id": f"user_{random.randint(1000, 9999)}"
                },
                "device": {
                    "os": {
                        "name": random.choice(["iOS", "Android"])
                    },
                    "model": f"Device_{random.randint(1, 100)}"
                },
                "geo": {
                    "city_name": random.choice(self.cities)
                }
            }

            docs.append(doc)

        self._bulk_index(index_name, docs)
        logger.info(f"Seeded {len(docs)} mobile log events for {date}")

    def _seed_payment_logs(self, date: datetime.date) -> None:
        """Seed payment processing log data"""
        index_name = f"logs-payment-{date.isoformat()}"
        docs = []

        # Generate 50-100 payment events per day
        num_events = random.randint(50, 100)

        for i in range(num_events):
            timestamp = datetime.combine(date, datetime.min.time()) + timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )

            doc = {
                "@timestamp": timestamp.isoformat(),
                "event": {
                    "action": random.choice(["payment_initiated", "payment_completed", "payment_failed", "transfer_processed"]),
                    "outcome": random.choice(self.outcomes)
                },
                "app": {
                    "channel": random.choice(self.channels),
                    "name": "payment-service"
                },
                "transaction": {
                    "amount": round(random.uniform(10.0, 10000.0), 2),
                    "currency": "USD"
                },
                "user": {
                    "id": f"user_{random.randint(1000, 9999)}"
                },
                "source": {
                    "ip": f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
                }
            }

            docs.append(doc)

        self._bulk_index(index_name, docs)
        logger.info(f"Seeded {len(docs)} payment log events for {date}")

    def _seed_meta_dictionary(self) -> None:
        """Seed meta-dictionary with field mappings and synonyms"""
        docs = [
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

        self._bulk_index("meta-dictionary", docs)
        logger.info(f"Seeded {len(docs)} meta-dictionary entries")

    def _bulk_index(self, index_name: str, docs: List[Dict[str, Any]]) -> None:
        """Bulk index documents into Elasticsearch"""
        if not docs:
            return

        # Prepare bulk request body
        bulk_body = []
        for doc in docs:
            bulk_body.extend([
                {"create": {}},  # Use create for data streams
                doc
            ])

        # Execute bulk request
        response = self.es.bulk(index=index_name, body=bulk_body, refresh=True)

        if response.get("errors"):
            logger.error(f"Bulk indexing errors for {index_name}: {response['errors']}")
            # Log first error for debugging
            for item in response.get("items", []):
                if "error" in item.get("index", {}):
                    logger.error(f"First error: {item['index']['error']}")
                    break
        else:
            logger.info(f"Successfully indexed {len(docs)} documents into {index_name}")

    def _get_auth_template(self) -> Dict[str, Any]:
        """Get index template for auth logs"""
        return {
            "name": "logs-auth-template",
            "body": {
                "index_patterns": ["logs-auth-*"],
                "mappings": {
                    "_meta": {
                        "default_time_field": "@timestamp",
                        "primary_facets": ["event.outcome", "event.action", "app.channel", "source.ip", "device.os.name"],
                        "examples": ["user_login failure on mobile"]
                    },
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "event": {
                            "properties": {
                                "action": {"type": "keyword"},
                                "outcome": {"type": "keyword"},
                                "reason": {"type": "keyword"}
                            }
                        },
                        "app": {
                            "properties": {
                                "channel": {"type": "keyword"},
                                "name": {"type": "keyword"}
                            }
                        },
                        "user": {
                            "properties": {
                                "id": {"type": "keyword"}
                            }
                        },
                        "source": {
                            "properties": {
                                "ip": {"type": "ip"}
                            }
                        },
                        "device": {
                            "properties": {
                                "os": {
                                    "properties": {
                                        "name": {"type": "keyword"}
                                    }
                                }
                            }
                        },
                        "geo": {
                            "properties": {
                                "city_name": {"type": "keyword"}
                            }
                        },
                        "trace": {
                            "properties": {
                                "id": {"type": "keyword"}
                            }
                        }
                    }
                }
            }
        }

    def _get_mobile_template(self) -> Dict[str, Any]:
        """Get index template for mobile logs"""
        return {
            "name": "logs-mobile-template",
            "body": {
                "index_patterns": ["logs-mobile-*"],
                "mappings": {
                    "_meta": {
                        "default_time_field": "@timestamp",
                        "primary_facets": ["event.outcome", "event.action", "device.os.name", "geo.city_name"],
                        "examples": ["app_launch on iOS"]
                    },
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "event": {
                            "properties": {
                                "action": {"type": "keyword"},
                                "outcome": {"type": "keyword"}
                            }
                        },
                        "app": {
                            "properties": {
                                "channel": {"type": "keyword"},
                                "name": {"type": "keyword"},
                                "version": {"type": "keyword"}
                            }
                        },
                        "user": {
                            "properties": {
                                "id": {"type": "keyword"}
                            }
                        },
                        "device": {
                            "properties": {
                                "os": {
                                    "properties": {
                                        "name": {"type": "keyword"}
                                    }
                                },
                                "model": {"type": "keyword"}
                            }
                        },
                        "geo": {
                            "properties": {
                                "city_name": {"type": "keyword"}
                            }
                        }
                    }
                }
            }
        }

    def _get_payment_template(self) -> Dict[str, Any]:
        """Get index template for payment logs"""
        return {
            "name": "logs-payment-template",
            "body": {
                "index_patterns": ["logs-payment-*"],
                "mappings": {
                    "_meta": {
                        "default_time_field": "@timestamp",
                        "primary_facets": ["event.outcome", "event.action", "app.channel"],
                        "examples": ["payment_completed via mobile"]
                    },
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "event": {
                            "properties": {
                                "action": {"type": "keyword"},
                                "outcome": {"type": "keyword"}
                            }
                        },
                        "app": {
                            "properties": {
                                "channel": {"type": "keyword"},
                                "name": {"type": "keyword"}
                            }
                        },
                        "transaction": {
                            "properties": {
                                "amount": {"type": "float"},
                                "currency": {"type": "keyword"}
                            }
                        },
                        "user": {
                            "properties": {
                                "id": {"type": "keyword"}
                            }
                        },
                        "source": {
                            "properties": {
                                "ip": {"type": "ip"}
                            }
                        }
                    }
                }
            }
        }


def main():
    parser = argparse.ArgumentParser(description="Seed banking log data into Elasticsearch")
    parser.add_argument("--es-url", default=os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200"), help="Elasticsearch URL")
    parser.add_argument("--username", default="", help="Elasticsearch username")
    parser.add_argument("--password", default="", help="Elasticsearch password")

    args = parser.parse_args()

    seeder = BankingDataSeeder(args.es_url, args.username, args.password)
    seeder.seed_all_data()


if __name__ == "__main__":
    main()