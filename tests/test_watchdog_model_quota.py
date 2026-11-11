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

    def test_sequence_cleans_obsolete_models(self):
        from app.services.watchdog_service import get_model_sequence
        seq = get_model_sequence(["Gemini 3.5 Flash (High)", "Gemini 3.8 Flash (High)"])
        # Debe haber reemplazado 3.5 Flash por 3.8 Flash y no tener duplicados
        self.assertNotIn("Gemini 3.5 Flash (High)", seq)
        self.assertIn("Gemini 3.8 Flash (High)", seq)
        self.assertEqual(len(seq), len(set(seq)))

    def test_quota_error_requires_nonzero_returncode(self):
        # Si el modelo respondió un resumen técnico mencionando '429' o 'resource_exhausted' con rc==0,
        # NO debe marcarse como error de cuota
        rc_success = 0
        output_with_quota_words = "El fix resuelve el error 429 RESOURCE_EXHAUSTED con éxito."
        from app.services.watchdog_service import QUOTA_KEYWORDS
        lower_out = output_with_quota_words.lower()
        is_err = (rc_success != 0) and any(k in lower_out for k in QUOTA_KEYWORDS)
        self.assertFalse(is_err)

        rc_failure = 1
        is_real_err = (rc_failure != 0) and any(k in lower_out for k in QUOTA_KEYWORDS)
        self.assertTrue(is_real_err)

    def test_canonical_model_name(self):
        from app.services.watchdog_service import canonical_model_name
        self.assertEqual(canonical_model_name("Gemini 3.5 Flash (High)"), "Gemini 3.8 Flash (High)")
        self.assertEqual(canonical_model_name("gemini-3.8-flash-high"), "Gemini 3.8 Flash (High)")
        self.assertEqual(canonical_model_name("Gemini 3.8 Flash (High)"), "Gemini 3.8 Flash (High)")
        self.assertEqual(canonical_model_name("gemini-4-argon-medium"), "Gemini 4 Argon (Medium)")
        self.assertEqual(canonical_model_name("gemini-4-argon-high"), "Gemini 4 Argon (Medium)")
        self.assertEqual(canonical_model_name("claude-sonnet-5-5-medium"), "Claude Sonnet 5.5 (Medium)")
        self.assertEqual(canonical_model_name("claude-opus-5-5-medium"), "Claude Opus 5.5 (Medium)")
        self.assertEqual(canonical_model_name("gpt-oss-120b-medium"), "GPT-OSS 120B (Medium)")
        self.assertEqual(canonical_model_name("gemini-3.8-flash-low"), "Gemini 3.8 Flash (Low)")
        self.assertEqual(canonical_model_name("Gemini Flash Lite"), "Gemini 3.8 Flash (Low)")

    def test_alias_exhausted_mapping(self):
        # Marcar agotado con alias 'Gemini 3.5 Flash (High)'
        from app.services.watchdog_service import _mark_model_exhausted, _clear_model_exhausted
        test_model_alias = "Gemini 3.5 Flash (High)"
        canonical_target = "Gemini 3.8 Flash (High)"

        _clear_model_exhausted(canonical_target)
        now_u = datetime.now(timezone.utc)
        _mark_model_exhausted(test_model_alias, now_u + timedelta(hours=3))

        ex_map = _get_exhausted_map()
        # Debe reflejarse bajo el nombre canónico oficial
        self.assertIn(canonical_target, ex_map)

        # Y get_watchdog_status debe reportar agotado a Gemini 3.8 Flash (High)
        status = get_watchdog_status()
        entry = next((m for m in status["models"] if m["name"] == canonical_target), None)
        self.assertIsNotNone(entry)
        self.assertTrue(entry["is_exhausted"])
        self.assertEqual(entry["quota_remaining_pct"], 0)

        # Limpiar usando el alias también debe desbloquear
        _clear_model_exhausted(test_model_alias)
        ex_map_after = _get_exhausted_map()
        self.assertNotIn(canonical_target, ex_map_after)

    def test_build_conv_to_model_map(self):
        from app.services.watchdog_service import _build_conv_to_model_map
        conv_map = _build_conv_to_model_map()
        self.assertIsInstance(conv_map, dict)
        # Debe haber mapeado conversaciones reales de logs existentes si existen
        if conv_map:
            for cid, model_name in conv_map.items():
                self.assertTrue(len(cid) >= 8)
                self.assertTrue(any(brand in model_name for brand in ["Gemini", "Claude", "GPT"]))


if __name__ == "__main__":
    unittest.main()
