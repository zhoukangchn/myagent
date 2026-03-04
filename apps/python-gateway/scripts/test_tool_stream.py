import httpx
import json

def test():
    url = "http://127.0.0.1:8000/v1/chat/stream"
    payload = {
        "chat_id": "test_tool_chat",
        "thread_id": "test_tool_thread",
        "sender_id": "test_user",
        "message_id": "msg_456",
        # Asking for current time or search web usually triggers a tool
        "text": "Please use a tool to check what time it is right now in UTC."
    }
    print("Testing with tool prompt...")
    try:
        with httpx.stream("POST", url, json=payload, timeout=30.0) as r:
            for line in r.iter_lines():
                if line:
                    print(line)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
