import importlib.util
import tempfile
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

    def test_extract_bitable_action_jobs_keeps_table_id(self):
        collector = load_collector()

        class Action:
            def __init__(self, record_id, table_id=""):
                self.record_id = record_id
                self.table_id = table_id

        class EventData:
            table_id = "tblDefault"
            action_list = [Action("recSdkRecord123", "tblA"), Action("recSdkRecord456")]

        class SdkEvent:
            event = EventData()

        self.assertEqual(
            collector.extract_bitable_action_jobs(SdkEvent()),
            [("tblA", "recSdkRecord123"), ("tblDefault", "recSdkRecord456")],
        )

    def test_feishu_table_ids_dedupes_primary_and_extra_tables(self):
        collector = load_collector()
        cfg = {
            "feishu": {
                "table_id": "tblPrimary",
                "table_ids": ["tblPrimary", "tblCopy", "", "tblCopy"],
            }
        }

        self.assertEqual(collector.feishu_table_ids(cfg), ["tblPrimary", "tblCopy"])

    def test_with_table_id_overrides_table_without_mutating_source(self):
        collector = load_collector()
        cfg = {"feishu": {"table_id": "tblPrimary", "app_token": "app"}, "fields": collector.DEFAULT_FIELDS}

        table_cfg = collector.with_table_id(cfg, "tblCopy")

        self.assertEqual(table_cfg["feishu"]["table_id"], "tblCopy")
        self.assertEqual(cfg["feishu"]["table_id"], "tblPrimary")

    def test_should_process_blank_record_only_for_new_link_rows(self):
        collector = load_collector()
        cfg = {"fields": collector.DEFAULT_FIELDS}

        self.assertTrue(
            collector.should_process_blank_record(
                {"fields": {"作品链接": "https://www.douyin.com/video/123456789"}},
                cfg,
            )
        )
        self.assertFalse(
            collector.should_process_blank_record(
                {"fields": {"作品链接": "https://www.douyin.com/video/123456789", "抓取状态": "成功"}},
                cfg,
            )
        )
        self.assertFalse(
            collector.should_process_blank_record({"fields": {"作品标题": "已有标题"}}, cfg)
        )

    def test_should_process_retry_transcript_rows(self):
        collector = load_collector()
        cfg = {"fields": collector.DEFAULT_FIELDS}

        self.assertTrue(
            collector.should_process_blank_record(
                {
                    "fields": {
                        "作品链接": "https://www.douyin.com/video/123456789",
                        "作品标题": "已有标题",
                        "抓取状态": "待转写",
                    }
                },
                cfg,
            )
        )
        self.assertFalse(
            collector.should_process_blank_record(
                {
                    "fields": {
                        "作品链接": "https://www.douyin.com/video/123456789",
                        "作品标题": "已有标题",
                        "抓取状态": "无音频",
                    }
                },
                cfg,
            )
        )

    def test_first_url_prefers_full_url_list_before_douyin_uri(self):
        collector = load_collector()

        self.assertEqual(
            collector.first_url(
                {
                    "uri": "tos-cn-i-dy/relative-cover",
                    "url_list": ["https://p3-sign.douyinpic.com/full-cover.webp"],
                }
            ),
            "https://p3-sign.douyinpic.com/full-cover.webp",
        )

    def test_attachment_parent_node_uses_wiki_obj_token_when_available(self):
        collector = load_collector()
        calls = []

        def fake_http_json(method, url, **kwargs):
            calls.append((method, url, kwargs))
            return 200, {
                "code": 0,
                "data": {
                    "node": {
                        "obj_type": "bitable",
                        "obj_token": "real_bitable_token",
                    }
                },
            }

        collector.http_json = fake_http_json
        cfg = {
            "feishu": {
                "app_id": "cli_x",
                "app_secret": "secret",
                "app_token": "wiki_node_token",
                "table_id": "tbl_x",
                "base_url": "https://open.feishu.cn",
            }
        }

        collector.tenant_access_token = lambda cfg: "tenant_token"
        self.assertEqual(collector.attachment_parent_node(cfg), "real_bitable_token")
        self.assertIn("/open-apis/wiki/v2/spaces/get_node?token=wiki_node_token", calls[0][1])

    def test_transcribe_from_meta_removes_temp_media_dir_when_asr_fails(self):
        collector = load_collector()
        temp_root = Path(tempfile.mkdtemp(prefix="collector-test-"))
        media_path = temp_root / "media.mp4"
        media_path.write_bytes(b"fake video")
        audio_path = temp_root / "audio.mp3"

        collector.download_media_file = lambda url, cfg, platform: media_path
        collector.extract_audio_file = lambda path: audio_path

        def fail_asr(cfg, path):
            raise RuntimeError("ASR失败")

        collector.transcribe_audio_file = fail_asr

        with self.assertRaisesRegex(RuntimeError, "ASR失败"):
            collector.transcribe_from_meta({}, {"media_url": "https://example.com/video.mp4", "platform": "抖音"})

        self.assertFalse(temp_root.exists())

    def test_classify_processing_error_uses_actionable_statuses(self):
        collector = load_collector()

        self.assertEqual(collector.classify_processing_error(RuntimeError("yt-dlp 需要登录 Cookie")), "需Cookie")
        self.assertEqual(collector.classify_processing_error(RuntimeError("抖音要求刷新登录态")), "需登录")
        self.assertEqual(collector.classify_processing_error(RuntimeError("这是图文作品，没有视频音频")), "图文作品")
        self.assertEqual(collector.classify_processing_error(RuntimeError("未拿到视频/音频直链")), "平台限制")
        self.assertEqual(collector.classify_processing_error(RuntimeError("音频流为空 no audio stream")), "无音频")
        self.assertEqual(collector.classify_processing_error(RuntimeError("ffmpeg 抽取音频失败")), "下载失败")
        self.assertEqual(collector.classify_processing_error(RuntimeError("OpenAI 转写失败 HTTP 500")), "转写失败")
        self.assertEqual(collector.classify_processing_error(RuntimeError("其它错误")), "待人工确认")

    def test_build_update_fields_does_not_write_empty_caption(self):
        collector = load_collector()
        cfg = {"fields": collector.DEFAULT_FIELDS}
        field_types = {name: 1 for name in collector.DEFAULT_FIELDS.values()}

        fields = collector.build_update_fields(
            cfg,
            {
                "platform": "抖音",
                "title": "有标题",
                "caption": "",
                "duration": "",
                "published_at": "",
            },
            field_types,
        )

        self.assertNotIn("文案", fields)


if __name__ == "__main__":
    unittest.main()
