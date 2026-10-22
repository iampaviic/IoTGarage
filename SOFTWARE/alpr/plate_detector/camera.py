"""USB camera capture that always returns the *latest* frame.

USB webcams buffer several frames; reading only when a car arrives would give
a stale image from seconds ago. A background thread keeps grabbing so
read_latest() is always fresh.

    cam = Camera(0, width=1280, height=720).start()
    frame = cam.read_latest()

source can be a camera index (0 = /dev/video0), a video file, an RTSP URL or
a GStreamer pipeline string (Jetson CSI camera).
"""

from __future__ import annotations

import logging
import platform
import threading
import time
from typing import Optional, Union

import cv2
import numpy as np

log = logging.getLogger(__name__)


class CameraError(RuntimeError):
    pass


class Camera:
    def __init__(self, source: Union[int, str] = 0, width: int = 1280, height: int = 720, fps: int = 30) -> None:
        self.source = int(source) if isinstance(source, str) and source.isdigit() else source
        self.width, self.height, self.fps = width, height, fps
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._frame_time = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _open(self) -> cv2.VideoCapture:
        if isinstance(self.source, int):
            backend = cv2.CAP_V4L2 if platform.system() == "Linux" else (
                cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY)
            cap = cv2.VideoCapture(self.source, backend)
            # MJPG lets cheap USB cameras deliver 720p at 30 fps
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        elif "!" in str(self.source):
            cap = cv2.VideoCapture(self.source, cv2.CAP_GSTREAMER)
        else:
            cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            raise CameraError("cannot open camera %r" % (self.source,))
        return cap

    def start(self) -> "Camera":
        self._cap = self._open()
        self._thread = threading.Thread(target=self._loop, name="camera", daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        failures = 0
        while not self._stop.is_set():
            ok, frame = self._cap.read() if self._cap is not None else (False, None)
            if ok:
                failures = 0
                with self._lock:
                    self._frame, self._frame_time = frame, time.monotonic()
                continue
            failures += 1
            if failures in (10, 100) or failures % 500 == 0:
                log.warning("camera read failed %d times, reopening", failures)
                try:
                    if self._cap is not None:
                        self._cap.release()
                    self._cap = self._open()
                except CameraError as e:
                    log.error("%s", e)
            time.sleep(0.05)

    def read_latest(self, max_age_s: float = 1.0, timeout_s: float = 3.0) -> np.ndarray:
        """Newest frame not older than max_age_s; raises CameraError on timeout."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            with self._lock:
                if self._frame is not None and time.monotonic() - self._frame_time <= max_age_s:
                    return self._frame.copy()
            time.sleep(0.02)
        raise CameraError("no fresh frame from camera %r" % (self.source,))

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap is not None:
            self._cap.release()
