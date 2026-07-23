"""Demonstrate pagination, temporary-failure retry, and idempotent creation in order."""

from reliable_client import ReliableApiClient


def main(base_url: str = "http://127.0.0.1:8765") -> None:
    with ReliableApiClient(base_url) as client:
        print("Pagination result:", list(client.iter_items()))
        print("Temporary-failure recovery:", client.get_flaky_status())

        payload = {"task": "index-document", "document_id": "doc-42"}
        first = client.create_job(payload, idempotency_key="learning-operation-001")
        second = client.create_job(payload, idempotency_key="learning-operation-001")
        print("First creation:", first)
        print("Same-key replay:", second)
        print("Same job:", first["id"] == second["id"])


if __name__ == "__main__":
    main()
