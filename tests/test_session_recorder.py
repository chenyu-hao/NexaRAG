import json


def test_session_recorder_writes_jsonl_events(tmp_path):
    from core.recorder import SessionRecorder

    recorder = SessionRecorder(root=tmp_path, user_id="u1", session_id="s1")

    recorder.record({"type": "node_started", "node": "IntentNode"})

    path = tmp_path / "u1" / "sessions" / "s1.jsonl"
    event = json.loads(path.read_text(encoding="utf-8").strip())

    assert event["type"] == "node_started"
    assert event["node"] == "IntentNode"
