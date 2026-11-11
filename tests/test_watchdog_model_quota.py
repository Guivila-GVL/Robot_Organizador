import unittest
from datetime import datetime, timezone, timedelta
from app.services.watchdog_service import (
    parse_reset_duration,
    mark_model_exhausted_from_output,
    clear_model_exhausted,
    get_watchdog_status,
    _get_exhausted_map
)
from app.services.queue_runner import _pick_next_available_model


class TestWatchdogModelQuota(unittest.TestCase):
    def test_parse_reset_duration(self):
        # Test hours, mins, secs
        text1 = "error: Individual quota reached. Resets in 89h15m13s."
        delta1 = parse_reset_duration(text1)
        self.assertIsNotNone(delta1)
        self.assertEqual(delta1.total_seconds(), 89 * 3600 + 15 * 60 + 13)

        # Test days and hours
        text2 = "Quota exhausted. Resets in 2d 5h."
        delta2 = parse_reset_duration(text2)
        self.assertIsNotNone(delta2)
        self.assertEqual(delta2.total_seconds(), 2 * 86400 + 5 * 3600)

        # Test minutes only
        text3 = "Rate limit reached. resets in 45m"
        delta3 = parse_reset_duration(text3)
        self.assertIsNotNone(delta3)
        self.assertEqual(delta3.total_seconds(), 45 * 60)

        # Test invalid
        self.assertIsNone(parse_reset_duration(""))
        self.assertIsNone(parse_reset_duration("Random error message"))

    def test_exhausted_flow_and_watchdog_status(self):
        test_model = "Claude Opus 5.5 (Medium)"

        # Ensure starting fresh
        clear_model_exhausted(test_model)
        ex_map_start = _get_exhausted_map()
        self.assertNotIn(test_model, ex_map_start)

        # Mark exhausted with specific output
        sample_output = "AGY_ERROR: RESOURCE_EXHAUSTED (code 429): Individual quota reached. Resets in 4h30m."
        reset_dt = mark_model_exhausted_from_output(test_model, sample_output)
        now_u = datetime.now(timezone.utc)
        self.assertGreater(reset_dt, now_u + timedelta(hours=4))

        # Check watchdog status reflects exhaustion
        status = get_watchdog_status()
        model_entry = next((m for m in status["models"] if m["name"] == test_model), None)
        self.assertIsNotNone(model_entry)
        self.assertTrue(model_entry["is_exhausted"])
        self.assertEqual(model_entry["quota_remaining_pct"], 0)
        self.assertEqual(model_entry["quota_color"], "red")
        self.assertIn("Renueva en", model_entry["reset_text"])

        # Recommended fallback should never be an exhausted model
        rec = status.get("recommended_fallback")
        if rec:
            self.assertNotEqual(rec["name"], test_model)

        # Queue runner should skip the exhausted model
        picked = _pick_next_available_model([m["name"] for m in status["models"] if m["name"] != test_model and m["order"] < model_entry["order"]])
        if picked:
            self.assertNotEqual(picked["name"], test_model)

        # Test clear / unblock
        clear_model_exhausted(test_model)
        status_after = get_watchdog_status()
        model_entry_after = next((m for m in status_after["models"] if m["name"] == test_model), None)
        self.assertFalse(model_entry_after["is_exhausted"])
        self.assertGreater(model_entry_after["quota_remaining_pct"], 0)


if __name__ == "__main__":
    unittest.main()
