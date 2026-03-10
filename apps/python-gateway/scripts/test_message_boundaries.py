import json

import httpx


def test():
    url = "http://127.0.0.1:8000/v1/chat/stream"
    payload = {
        "chat_id": "test_boundary_chat",
        "thread_id": "test_boundary_thread",
        "sender_id": "test_user",
        "message_id": "msg_boundary_001",
        "text": "先给一句简短回答，再补一句解释。如果用了工具，也把工具后的回复单独算一条消息。",
    }

    current_event = None
    messages: list[str] = []

    def ensure_message(index: int) -> None:
        while len(messages) < index:
            messages.append("")

    with httpx.stream("POST", url, json=payload, timeout=120.0) as response:
        print(f"status={response.status_code}")
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

            if current_event == "message_start":
                index = int(data.get("index") or 1)
                ensure_message(index)
                print(f"[message_start] index={index}")
                continue

            if current_event == "delta":
                if not messages:
                    ensure_message(1)
                messages[-1] += str(data.get("text") or "")
                print(f"[delta] {data.get('text')!r}")
                continue

            if current_event == "tool_event":
                print(f"[tool_event] {json.dumps(data, ensure_ascii=False)}")
                continue

            if current_event == "done":
                print("[done]")
                break

    print("\nassembled messages:")
    for idx, text in enumerate(messages, start=1):
        print(f"{idx}. {text}")


if __name__ == "__main__":
    test()
