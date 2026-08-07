import logging
import time
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Try importing CV libraries
try:
    import cv2
    import numpy as np
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False
    logger.warning("OpenCV or NumPy not available. Behavioral Analyzer will use fallback telemetry aggregator.")


class BehavioralAnalyzer:
    """
    Analyzes image frames to measure objective face visibility, gaze/eye contact, and posture stability.
    Stateless processing: frames are processed in memory and discarded immediately.
    """

    def __init__(self):
        self.face_cascade = None
        self.eye_cascade = None

        if CV_AVAILABLE:
            try:
                self.face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                )
                self.eye_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + "haarcascade_eye.xml"
                )
            except Exception as e:
                logger.error(f"Failed to load OpenCV cascades: {e}")

    def process_frame(self, image_bytes: bytes) -> Dict:
        """
        Process a single compressed image frame (JPEG/PNG bytes).
        Returns an objective metric telemetry tick dict.
        """
        if not CV_AVAILABLE or self.face_cascade is None or self.face_cascade.empty():
            return {
                "face_detected": False,
                "eye_contact": False,
                "gaze_direction": "unknown",
                "posture": "unknown",
                "timestamp": time.time(),
            }

        try:
            # Decode image from buffer
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return {
                    "face_detected": False,
                    "eye_contact": False,
                    "gaze_direction": "unknown",
                    "posture": "unknown",
                    "timestamp": time.time(),
                }

            h, w, _ = frame.shape
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )

            if len(faces) == 0:
                return {
                    "face_detected": False,
                    "eye_contact": False,
                    "gaze_direction": "looking_away",
                    "posture": "unknown",
                    "timestamp": time.time(),
                }

            # Pick largest detected face
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            fx, fy, fw, fh = faces[0]

            # 1. Eye Contact & Gaze Calculation
            eye_contact, gaze_dir = self._calculate_gaze(gray, fx, fy, fw, fh)

            # 2. Posture Calculation (Center alignment and aspect ratio)
            posture = self._calculate_posture(fx, fy, fw, fh, w, h)

            return {
                "face_detected": True,
                "eye_contact": eye_contact,
                "gaze_direction": gaze_dir,
                "posture": posture,
                "timestamp": time.time(),
            }
        except Exception as e:
            logger.error(f"Error processing behavioral frame: {e}")
            return {
                "face_detected": False,
                "eye_contact": False,
                "gaze_direction": "unknown",
                "posture": "unknown",
                "timestamp": time.time(),
            }

    def _calculate_gaze(self, gray_img, fx: int, fy: int, fw: int, fh: int) -> Tuple[bool, str]:
        """
        Detects eye region within upper face ROI to evaluate direct screen/camera eye contact vs looking away.
        """
        try:
            # Eye ROI is top 55% of the face bounding box
            roi_h = int(fh * 0.55)
            roi_gray = gray_img[fy : fy + roi_h, fx : fx + fw]

            if roi_gray.size == 0 or self.eye_cascade is None or self.eye_cascade.empty():
                return True, "center"

            eyes = self.eye_cascade.detectMultiScale(
                roi_gray, scaleFactor=1.1, minNeighbors=4, minSize=(15, 15)
            )

            if len(eyes) >= 1:
                # Check horizontal centering of eyes within face ROI
                eye_centers_x = [ex + ew / 2 for ex, ey, ew, eh in eyes]
                avg_eye_x = sum(eye_centers_x) / len(eye_centers_x)
                relative_pos = avg_eye_x / fw

                if 0.25 <= relative_pos <= 0.75:
                    return True, "center"
                else:
                    return False, "looking_away"
            else:
                # No eyes detected in upper ROI -> candidate turned head / looking away
                return False, "looking_away"
        except Exception:
            return True, "center"

    def _calculate_posture(self, fx: int, fy: int, fw: int, fh: int, img_w: int, img_h: int) -> str:
        """
        Evaluates posture stability based on face box aspect ratio and relative position within the camera frame.
        """
        try:
            # Face center coordinates
            face_center_x = (fx + fw / 2) / img_w
            face_center_y = (fy + fh / 2) / img_h
            aspect_ratio = fh / max(fw, 1)

            # Check if candidate is centered and upright vs severely leaning or slouching
            if 0.25 <= face_center_x <= 0.75 and 0.15 <= face_center_y <= 0.85 and 1.0 <= aspect_ratio <= 1.8:
                return "upright"
            else:
                return "leaning_slouching"
        except Exception:
            return "upright"


def aggregate_session_behavior(raw_ticks: List[Dict]) -> Dict:
    """
    Aggregates temporal series of behavioral telemetry ticks into objective summary metrics.
    """
    if not raw_ticks:
        return {
            "total_frames_analyzed": 0,
            "face_visibility_pct": 0.0,
            "eye_contact_pct": 0.0,
            "looking_away_events": 0,
            "avg_looking_away_duration_sec": 0.0,
            "posture_summary": {
                "upright_pct": 0.0,
                "slouching_leaning_pct": 0.0,
            },
        }

    total_ticks = len(raw_ticks)
    face_detected_ticks = [t for t in raw_ticks if t.get("face_detected", False)]
    face_count = len(face_detected_ticks)

    face_visibility_pct = round((face_count / total_ticks) * 100, 1)

    if face_count > 0:
        eye_contact_count = sum(1 for t in face_detected_ticks if t.get("eye_contact", False))
        eye_contact_pct = round((eye_contact_count / face_count) * 100, 1)

        upright_count = sum(1 for t in face_detected_ticks if t.get("posture") == "upright")
        upright_pct = round((upright_count / face_count) * 100, 1)
        slouching_leaning_pct = round(100.0 - upright_pct, 1)
    else:
        eye_contact_pct = 0.0
        upright_pct = 0.0
        slouching_leaning_pct = 0.0

    # Calculate sustained looking away events (> 2 consecutive ticks looking away)
    looking_away_events = 0
    event_durations = []
    current_event_len = 0

    time_step = 2.0
    if len(raw_ticks) > 1 and "timestamp" in raw_ticks[0] and "timestamp" in raw_ticks[1]:
        delta = raw_ticks[1]["timestamp"] - raw_ticks[0]["timestamp"]
        if 0.1 <= delta <= 10.0:
            time_step = delta

    for t in raw_ticks:
        is_looking_away = (not t.get("face_detected", False)) or (not t.get("eye_contact", False)) or (t.get("gaze_direction") == "looking_away")
        if is_looking_away:
            current_event_len += 1
        else:
            if current_event_len >= 2:
                looking_away_events += 1
                event_durations.append(current_event_len * time_step)
            current_event_len = 0

    if current_event_len >= 2:
        looking_away_events += 1
        event_durations.append(current_event_len * time_step)

    avg_looking_away_duration = (
        round(sum(event_durations) / len(event_durations), 1) if event_durations else 0.0
    )

    return {
        "total_frames_analyzed": total_ticks,
        "face_visibility_pct": face_visibility_pct,
        "eye_contact_pct": eye_contact_pct,
        "looking_away_events": looking_away_events,
        "avg_looking_away_duration_sec": avg_looking_away_duration,
        "posture_summary": {
            "upright_pct": upright_pct,
            "slouching_leaning_pct": slouching_leaning_pct,
        },
    }
