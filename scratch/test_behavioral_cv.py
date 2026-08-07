import time
import unittest
from app.features.practice.behavioral import BehavioralAnalyzer, aggregate_session_behavior


class TestBehavioralModule(unittest.TestCase):
    def setUp(self):
        self.analyzer = BehavioralAnalyzer()

    def test_aggregate_session_behavior_empty(self):
        res = aggregate_session_behavior([])
        self.assertEqual(res["total_frames_analyzed"], 0)
        self.assertEqual(res["face_visibility_pct"], 0.0)
        self.assertEqual(res["eye_contact_pct"], 0.0)

    def test_aggregate_session_behavior_metrics(self):
        now = time.time()
        sample_ticks = [
            {"face_detected": True, "eye_contact": True, "gaze_direction": "center", "posture": "upright", "timestamp": now},
            {"face_detected": True, "eye_contact": True, "gaze_direction": "center", "posture": "upright", "timestamp": now + 2},
            {"face_detected": True, "eye_contact": False, "gaze_direction": "looking_away", "posture": "upright", "timestamp": now + 4},
            {"face_detected": True, "eye_contact": False, "gaze_direction": "looking_away", "posture": "leaning_slouching", "timestamp": now + 6},
            {"face_detected": True, "eye_contact": True, "gaze_direction": "center", "posture": "upright", "timestamp": now + 8},
        ]

        summary = aggregate_session_behavior(sample_ticks)

        self.assertEqual(summary["total_frames_analyzed"], 5)
        self.assertEqual(summary["face_visibility_pct"], 100.0)
        self.assertEqual(summary["eye_contact_pct"], 60.0)
        self.assertEqual(summary["looking_away_events"], 1)
        self.assertEqual(summary["posture_summary"]["upright_pct"], 80.0)
        self.assertEqual(summary["posture_summary"]["slouching_leaning_pct"], 20.0)

    def test_analyzer_fallback_on_invalid_bytes(self):
        res = self.analyzer.process_frame(b"invalid_image_bytes")
        self.assertFalse(res["face_detected"])
        self.assertFalse(res["eye_contact"])
        self.assertEqual(res["gaze_direction"], "unknown")


if __name__ == "__main__":
    unittest.main()
