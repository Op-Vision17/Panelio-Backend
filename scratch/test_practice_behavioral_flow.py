import asyncio
import base64
import json
import time
import unittest

import cv2
import numpy as np

from app.features.practice.behavioral import BehavioralAnalyzer, aggregate_session_behavior


class TestPracticeBehavioralIntegration(unittest.TestCase):
    def setUp(self):
        self.analyzer = BehavioralAnalyzer()

    def test_frame_processing_fallback_handling(self):
        # Create a blank image canvas
        img = np.zeros((300, 300, 3), dtype=np.uint8)
        _, buffer = cv2.imencode(".jpg", img)
        image_bytes = buffer.tobytes()

        # Process frame
        result = self.analyzer.process_frame(image_bytes)

        self.assertIn("face_detected", result)
        self.assertIn("eye_contact", result)
        self.assertIn("gaze_direction", result)
        self.assertIn("posture", result)
        self.assertFalse(result["face_detected"])
        self.assertEqual(result["gaze_direction"], "looking_away")

    def test_aggregate_behavioral_ticks_sequence(self):
        now = time.time()
        ticks = [
            {"face_detected": True, "eye_contact": True, "gaze_direction": "center", "posture": "upright", "timestamp": now},
            {"face_detected": True, "eye_contact": True, "gaze_direction": "center", "posture": "upright", "timestamp": now + 2},
            {"face_detected": True, "eye_contact": False, "gaze_direction": "looking_away", "posture": "upright", "timestamp": now + 4},
            {"face_detected": True, "eye_contact": False, "gaze_direction": "looking_away", "posture": "upright", "timestamp": now + 6},
            {"face_detected": True, "eye_contact": True, "gaze_direction": "center", "posture": "upright", "timestamp": now + 8},
        ]

        summary = aggregate_session_behavior(ticks)
        self.assertEqual(summary["total_frames_analyzed"], 5)
        self.assertEqual(summary["face_visibility_pct"], 100.0)
        self.assertEqual(summary["eye_contact_pct"], 60.0)
        self.assertEqual(summary["looking_away_events"], 1)
        self.assertAlmostEqual(summary["avg_looking_away_duration_sec"], 4.0, delta=0.5)


if __name__ == "__main__":
    unittest.main()
