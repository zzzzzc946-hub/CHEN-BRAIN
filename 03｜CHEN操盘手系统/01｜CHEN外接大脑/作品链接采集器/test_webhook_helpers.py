import importlib.util
import unittest
from pathlib import Path


def load_collector():
    path = Path(__file__).with_name("content_link_collector.py")
    spec = importlib.util.spec_from_file_location("content_link_collector", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WebhookHelperTests(unittest.TestCase):
    def test_extract_record_ids_from_nested_event(self):
        collector = load_collector()
        payload = {
            "schema": "2.0",
            "header": {"event_type": "bitable.record.changed"},
            "event": {
                "app_token": "apptoken",
                "table_id": "tbl123",
                "record_id": "recAaBbCcDd123",
                "changes": [{"record_id": "recEeFfGgHh456"}],
            },
        }

        self.assertEqual(
            collector.extract_record_ids(payload),
            ["recAaBbCcDd123", "recEeFfGgHh456"],
        )

    def test_challenge_response_payload(self):
        collector = load_collector()

        self.assertEqual(
            collector.challenge_response({"type": "url_verification", "challenge": "abc123"}),
            {"challenge": "abc123"},
        )

    def test_extract_bitable_action_record_ids_from_sdk_event(self):
        collector = load_collector()

        class Action:
            def __init__(self, record_id):
                self.record_id = record_id

        class EventData:
            action_list = [Action("recSdkRecord123"), Action("recSdkRecord456")]

        class SdkEvent:
            event = EventData()

        self.assertEqual(
            collector.extract_bitable_action_record_ids(SdkEvent()),
            ["recSdkRecord123", "recSdkRecord456"],
        )


if __name__ == "__main__":
    unittest.main()
