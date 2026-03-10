import json
import time

import httpx


def test() -> None:
    url = "http://127.0.0.1:8000/v1/chat/stream"
    payload = {
        "chat_id": "test_batch_chat",
        "thread_id": "test_batch_thread",
        "sender_id": "test_user",
        "message_id": "msg_batch_001",
        "text": "请分多次回复，每次间隔一点时间。",
        "metadata": {},
    }

    current_event = None
    received_at: list[float] = []
    events: list[tuple[str, dict]] = []

    with httpx.stream("POST", url, json=payload, timeout=120.0) as response:
        print(f"status={response.status_code}")
        start = time.monotonic()
        for raw_line in response.iter_lines():
            if not raw_line:
                continue

            line = raw_line.strip()
            if line.startswith("event: "):
                current_event = line[7:]
                continue

            if not line.startswith("data: "):
                continue

            data = json.loads(line[6:])
            if current_event in {"ack", "message_start", "delta", "tool_event", "done", "error"}:
                elapsed = time.monotonic() - start
                received_at.append(elapsed)
                events.append((current_event or "unknown", data))
                print(f"[{elapsed:0.3f}s] {current_event}: {json.dumps(data, ensure_ascii=False)}")

            if current_event in {"done", "error"}:
                break

    print("\nintervals:")
    for idx in range(1, len(received_at)):
        delta = received_at[idx] - received_at[idx - 1]
        print(f"{idx}: {delta:0.3f}s")

    print("\nevent summary:")
    for idx, (event_name, data) in enumerate(events, start=1):
        print(f"{idx}. {event_name} -> keys={sorted(data.keys())}")


if __name__ == "__main__":
    test()
