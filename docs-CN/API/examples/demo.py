"""依次演示分页、临时故障重试和幂等创建。"""

from reliable_client import ReliableApiClient


def main(base_url: str = "http://127.0.0.1:8765") -> None:
    with ReliableApiClient(base_url) as client:
        print("分页结果：", list(client.iter_items()))
        print("临时故障恢复：", client.get_flaky_status())

        payload = {"task": "index-document", "document_id": "doc-42"}
        first = client.create_job(payload, idempotency_key="learning-operation-001")
        second = client.create_job(payload, idempotency_key="learning-operation-001")
        print("首次创建：", first)
        print("同 key 重放：", second)
        print("是否同一任务：", first["id"] == second["id"])


if __name__ == "__main__":
    main()
