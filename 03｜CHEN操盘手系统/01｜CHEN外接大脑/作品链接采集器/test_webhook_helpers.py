import importlib.util
import queue
import tempfile
import threading
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

    def test_discover_feishu_table_ids_merges_auto_discovered_tables(self):
        collector = load_collector()
        cfg = {
            "feishu": {
                "app_id": "cli_x",
                "app_secret": "secret",
                "app_token": "app",
                "table_id": "tblPrimary",
                "table_ids": ["tblCopy"],
                "auto_discover_tables": True,
            }
        }

        collector.list_tables = lambda cfg: [{"table_id": "tblPrimary"}, {"table_id": "tblNew"}]

        self.assertEqual(collector.discover_feishu_table_ids(cfg), ["tblPrimary", "tblCopy", "tblNew"])

    def test_with_table_id_overrides_table_without_mutating_source(self):
        collector = load_collector()
        cfg = {"feishu": {"table_id": "tblPrimary", "app_token": "app"}, "fields": collector.DEFAULT_FIELDS}

        table_cfg = collector.with_table_id(cfg, "tblCopy")

        self.assertEqual(table_cfg["feishu"]["table_id"], "tblCopy")
        self.assertEqual(cfg["feishu"]["table_id"], "tblPrimary")

    def test_event_worker_count_defaults_and_clamps(self):
        collector = load_collector()

        self.assertEqual(collector.event_worker_count({}), 3)
        self.assertEqual(collector.event_worker_count({"event": {"worker_count": 0}}), 1)
        self.assertEqual(collector.event_worker_count({"event": {"worker_count": 99}}), 8)

    def test_scan_missing_records_continues_after_one_table_times_out(self):
        collector = load_collector()
        cfg = {"feishu": {"table_id": "bad"}, "fields": collector.DEFAULT_FIELDS}
        jobs = queue.Queue()
        pending = set()
        pending_lock = threading.Lock()

        collector.discover_feishu_table_ids = lambda cfg: ["bad", "good"]

        def fake_list_records(table_cfg):
            if table_cfg["feishu"]["table_id"] == "bad":
                raise TimeoutError("first table timed out")
            return [
                {
                    "record_id": "recGoodRecord123",
                    "fields": {"作品链接": "https://www.douyin.com/video/123456789"},
                }
            ]

        collector.list_records = fake_list_records

        collector.scan_missing_records_once(cfg, jobs, pending, pending_lock)

        self.assertEqual(jobs.get_nowait(), ("good", "recGoodRecord123"))

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
        self.assertTrue(
            collector.should_process_blank_record(
                {
                    "fields": {
                        "作品链接": "https://www.douyin.com/video/123456789",
                        "作品标题": "已有标题",
                        "抓取状态": "网络异常",
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

    def test_classify_transient_tls_error_as_retryable(self):
        collector = load_collector()

        self.assertEqual(
            collector.classify_processing_error(
                RuntimeError("<urlopen error EOF occurred in violation of protocol (_ssl.c:1129)>")
            ),
            "网络异常",
        )

    def test_tencent_rec_task_payload_uses_local_audio_data(self):
        collector = load_collector()

        payload = collector.tencent_create_rec_task_payload(b"abc123", {"engine_model_type": "16k_zh"})

        self.assertEqual(payload["EngineModelType"], "16k_zh")
        self.assertEqual(payload["ChannelNum"], 1)
        self.assertEqual(payload["ResTextFormat"], 3)
        self.assertEqual(payload["SourceType"], 1)
        self.assertEqual(payload["Data"], "YWJjMTIz")
        self.assertEqual(payload["DataLen"], 6)

    def test_clean_tencent_transcript_removes_timestamps(self):
        collector = load_collector()

        self.assertEqual(
            collector.clean_tencent_transcript("[0:0.020,0:2.380]  腾讯云语音识别欢迎您。\n[0:2.4,0:3.0] 第二句。"),
            "腾讯云语音识别欢迎您。\n第二句。",
        )

    def test_tencent_audio_size_guard_falls_back_to_local(self):
        collector = load_collector()
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "audio.mp3"
            audio.write_bytes(b"x" * (5 * 1024 * 1024 + 1))

            with self.assertRaisesRegex(RuntimeError, "腾讯云本地音频上传限制"):
                collector.tencent_transcribe_file({"tencent_asr": {}}, audio)

    def test_should_transcribe_record_only_after_metadata_sync(self):
        collector = load_collector()
        cfg = {"fields": collector.DEFAULT_FIELDS}

        self.assertFalse(
            collector.should_transcribe_record(
                {"fields": {"作品链接": "https://www.douyin.com/video/123456789"}},
                cfg,
            )
        )
        self.assertTrue(
            collector.should_transcribe_record(
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

    def test_iter_json_objects_reads_xiaohongshu_initial_state(self):
        collector = load_collector()
        html = '<script>window.__INITIAL_STATE__={"note":{"title":"小红书标题"}};</script>'

        objects = list(collector.iter_json_objects(html))

        self.assertEqual(objects[-1]["note"]["title"], "小红书标题")

    def test_iter_json_objects_reads_xiaohongshu_initial_state_with_undefined(self):
        collector = load_collector()
        html = (
            '<script>window.__INITIAL_STATE__={"feed":undefined,'
            '"note":{"noteDetailMap":{"target":{"note":{"noteId":"target","type":"video"}}}}};</script>'
        )

        objects = list(collector.iter_json_objects(html))

        self.assertIsNone(objects[-1]["feed"])
        self.assertEqual(
            objects[-1]["note"]["noteDetailMap"]["target"]["note"]["noteId"],
            "target",
        )

    def test_extract_xiaohongshu_image_note_writes_body_as_caption(self):
        collector = load_collector()
        html = """
        <html><script>window.__INITIAL_STATE__={
          "noteDetailMap": {
            "abc": {"note": {
              "type": "normal",
              "title": "穿搭图文笔记",
              "desc": "这是图文正文",
              "imageList": [{"urlDefault": "https://ci.xiaohongshu.com/cover.jpg"}],
              "interactInfo": {"likedCount": "1.2万", "commentCount": "345", "shareCount": "67", "collectedCount": "890"},
              "time": 1710000000000
            }}
          }
        };</script></html>
        """

        meta = collector.extract_xiaohongshu_meta("https://www.xiaohongshu.com/explore/abc", html, "https://www.xiaohongshu.com/explore/abc")

        self.assertEqual(meta["platform"], "小红书")
        self.assertEqual(meta["title"], "穿搭图文笔记")
        self.assertEqual(meta["caption"], "这是图文正文")
        self.assertEqual(meta["cover_url"], "https://ci.xiaohongshu.com/cover.jpg")
        self.assertEqual(meta["duration"], "图文")
        self.assertEqual(meta["likes"], 12000)
        self.assertEqual(meta["comments"], 345)
        self.assertEqual(meta["shares"], 67)

    def test_extract_xiaohongshu_cover_normalizes_protocol_relative_url(self):
        collector = load_collector()
        html = """
        <meta property="og:image" content="//ci.xiaohongshu.com/cover.jpg">
        <script>window.__INITIAL_STATE__={"note":{"title":"标题","desc":"正文","type":"normal"}};</script>
        """

        meta = collector.extract_xiaohongshu_meta("https://www.xiaohongshu.com/explore/abc", html, "https://www.xiaohongshu.com/explore/abc")

        self.assertEqual(meta["cover_url"], "https://ci.xiaohongshu.com/cover.jpg")

    def test_extract_xiaohongshu_video_note_keeps_caption_for_asr(self):
        collector = load_collector()
        html = """
        <html><script>window.__INITIAL_STATE__={
          "note": {
            "type": "video",
            "title": "视频笔记",
            "desc": "这是视频简介，不是逐字稿",
            "cover": {"url": "https://ci.xiaohongshu.com/video-cover.jpg"},
            "interactInfo": {"likedCount": 12, "commentCount": 3, "shareCount": 4, "collectedCount": 9},
            "video": {"media": {"stream": {"h264": [{"masterUrl": "https://sns-video-hw.xhscdn.com/video.mp4"}]}}, "duration": 83000}
          }
        };</script></html>
        """

        meta = collector.extract_xiaohongshu_meta("https://www.xiaohongshu.com/explore/abc", html, "https://www.xiaohongshu.com/explore/abc")

        self.assertEqual(meta["title"], "视频笔记")
        self.assertEqual(meta["caption"], "")
        self.assertEqual(meta["cover_url"], "https://ci.xiaohongshu.com/video-cover.jpg")
        self.assertEqual(meta["duration"], "01:23")
        self.assertEqual(meta["media_url"], "https://sns-video-hw.xhscdn.com/video.mp4")
        self.assertEqual(meta["shares"], 4)

    def test_extract_xiaohongshu_does_not_treat_collections_as_shares(self):
        collector = load_collector()
        html = """
        <script>window.__INITIAL_STATE__={"note":{"noteDetailMap":{"abc":{"note":{
          "noteId":"abc",
          "type":"normal",
          "title":"图文",
          "desc":"正文",
          "interactInfo":{"likedCount":"3","commentCount":"2","collectedCount":"99"},
          "imageList":[{"urlDefault":"https://ci.xiaohongshu.com/cover.jpg"}]
        }}}}};</script>
        """

        meta = collector.extract_xiaohongshu_meta(
            "https://www.xiaohongshu.com/explore/abc",
            html,
            "https://www.xiaohongshu.com/explore/abc",
        )

        self.assertIsNone(meta["shares"])

    def test_extract_xiaohongshu_video_note_matches_url_id_and_reads_current_schema(self):
        collector = load_collector()
        html = """
        <html>
        <meta name="og:title" content="错误的元标签标题 - 小红书">
        <script>window.__INITIAL_STATE__={
          "feed": undefined,
          "note": {
            "noteDetailMap": {
              "other": {"note": {
                "noteId": "other",
                "type": "normal",
                "title": "不应选中的图文",
                "desc": "错误正文",
                "imageList": [{"urlDefault": "https://ci.xiaohongshu.com/wrong.jpg"}]
              }},
              "6a23fe8c000000003503bc2a": {"note": {
                "noteId": "6a23fe8c000000003503bc2a",
                "type": "video",
                "title": "Jason谈展示面三要素（第一期：颜值）",
                "desc": "#男性情感[话题]# #展示面[话题]#",
                "time": 1780743820000,
                "interactInfo": {
                  "likedCount": "14",
                  "commentCount": "2",
                  "shareCount": "1"
                },
                "imageList": [{"urlDefault": "https://ci.xiaohongshu.com/right.jpg"}],
                "video": {
                  "media": {
                    "video": {"duration": 132},
                    "stream": {
                      "h264": [{
                        "masterUrl": "https://sns-video-v4.xhscdn.com/target.mp4",
                        "videoDuration": 131900
                      }]
                    }
                  }
                }
              }}
            }
          }
        };</script></html>
        """

        meta = collector.extract_xiaohongshu_meta(
            "https://www.xiaohongshu.com/discovery/item/6a23fe8c000000003503bc2a",
            html,
            "https://www.xiaohongshu.com/explore/6a23fe8c000000003503bc2a",
        )

        self.assertEqual(meta["content_type"], "video")
        self.assertEqual(meta["title"], "Jason谈展示面三要素（第一期：颜值）")
        self.assertEqual(meta["caption"], "")
        self.assertEqual(meta["cover_url"], "https://ci.xiaohongshu.com/right.jpg")
        self.assertEqual(meta["duration"], "02:12")
        self.assertEqual(meta["likes"], 14)
        self.assertEqual(meta["comments"], 2)
        self.assertEqual(meta["shares"], 1)
        self.assertEqual(meta["published_at"], "2026年06月06日19时03分40秒")
        self.assertEqual(meta["media_url"], "https://sns-video-v4.xhscdn.com/target.mp4")

    def test_xiaohongshu_missing_metadata_is_reported_after_transcription(self):
        collector = load_collector()

        self.assertEqual(
            collector.metadata_quality_message(
                {
                    "platform": "小红书",
                    "content_type": "video",
                    "title": "视频标题",
                    "cover_url": "https://example.com/cover.jpg",
                    "media_url": "https://example.com/video.mp4",
                    "duration": "01:00",
                    "likes": None,
                    "comments": None,
                    "shares": None,
                    "published_at": "",
                }
            ),
            "小红书页面未暴露或未解析到：点赞、评论、分享、发布时间。",
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
