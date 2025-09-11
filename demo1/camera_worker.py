# This Python file uses the following encoding: utf-8
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from vmbpy import VmbSystem, PixelFormat, Camera, Stream, Frame


class CameraWorker(QThread):
    """
    QThread-based camera grabber using Allied Vision VmbPy.
    Outputs Mono8 frames as raw bytes via frameReady(bytes, width, height).
    """

    frameReady = Signal(object, int, int, int)  # numpy array (uint8), width, height, bytes_per_line (Mono8)
    # Control signals from UI -> worker thread
    setExposureAuto = Signal(str)   # 'Off' | 'Once' | 'Continuous'
    setExposureTime = Signal(float) # in microseconds (typical)
    setGainAuto = Signal(str)       # 'Off' | 'Continuous'
    setGain = Signal(float)         # in dB (typical)
    setGammaEnable = Signal(bool)
    setBlackLevel = Signal(float)

    error = Signal(str)
    startedStreaming = Signal()
    stoppedStreaming = Signal()

    def __init__(self, camera_id: str | None = None, parent=None):
        super().__init__(parent)
        self._camera_id = camera_id
        self._running = False

    def stop(self):
        self._running = False
        self.wait()  # block until thread finishes

    def run(self):
        try:
            with VmbSystem.get_instance() as vmb:
                cams = vmb.get_all_cameras()
                if not cams:
                    self.error.emit("No camera found.")
                    return

                cam = None
                if self._camera_id:
                    # try exact id match, else default to first
                    for c in cams:
                        if c.get_id() == self._camera_id:
                            cam = c
                            break
                if cam is None:
                    cam = cams[0]

                def handler(camera: Camera, stream: Stream, frame: Frame):
                    try:
                        # Ensure Mono8; if not, convert on the fly (costly but safe)
                        if frame.get_pixel_format() != PixelFormat.Mono8:
                            f = frame.convert_pixel_format(PixelFormat.Mono8)
                        else:
                            f = frame
                        w = f.get_width()
                        h = f.get_height()
                        # Obtain numpy view and copy to own memory so it outlives callback
                        arr = f.as_numpy_ndarray()
                        arr_owned = arr.copy()
                        bytes_per_line = arr_owned.strides[0]
                        self.frameReady.emit(arr_owned, w, h, bytes_per_line)
                    finally:
                        camera.queue_frame(frame)

                with cam:
                    # Try to configure commonly helpful features for visibility
                    def try_set_enum(feature_name: str, value: str):
                        try:
                            feat = getattr(cam, feature_name, None)
                            if feat is not None:
                                feat.set(value)
                        except Exception:
                            pass

                    def try_set_bool(feature_name: str, value: bool):
                        try:
                            feat = getattr(cam, feature_name, None)
                            if feat is not None:
                                feat.set(value)
                        except Exception:
                            pass

                    # Acquisition Mode: Continuous (if supported)
                    try_set_enum('AcquisitionMode', 'Continuous')
                    # Auto exposure/gain to help illumination
                    try_set_enum('ExposureAuto', 'Continuous')
                    try_set_enum('GainAuto', 'Continuous')
                    # Disable gamma if it makes image washed out (best-effort)
                    try_set_bool('GammaEnable', False)

                    # Connect control signals to feature setters (executed in worker thread)
                    def on_set_exposure_auto(mode: str):
                        try_set_enum('ExposureAuto', mode)
                    def on_set_exposure_time(val: float):
                        # When exposure auto is Off, set manual time if possible
                        try:
                            feat = getattr(cam, 'ExposureTime', None)
                            if feat is not None:
                                # Clamp to valid range
                                lo, hi = feat.get_range()
                                feat.set(max(lo, min(hi, val)))
                        except Exception:
                            pass
                    def on_set_gain_auto(mode: str):
                        try_set_enum('GainAuto', mode)
                    def on_set_gain(val: float):
                        try:
                            feat = getattr(cam, 'Gain', None)
                            if feat is not None:
                                lo, hi = feat.get_range()
                                feat.set(max(lo, min(hi, val)))
                        except Exception:
                            pass
                    def on_set_gamma_enable(enabled: bool):
                        try_set_bool('GammaEnable', enabled)
                    def on_set_black_level(val: float):
                        try:
                            feat = getattr(cam, 'BlackLevel', None)
                            if feat is not None:
                                lo, hi = feat.get_range()
                                feat.set(max(lo, min(hi, val)))
                        except Exception:
                            pass

                    self.setExposureAuto.connect(on_set_exposure_auto)
                    self.setExposureTime.connect(on_set_exposure_time)
                    self.setGainAuto.connect(on_set_gain_auto)
                    self.setGain.connect(on_set_gain)
                    self.setGammaEnable.connect(on_set_gamma_enable)
                    self.setBlackLevel.connect(on_set_black_level)

                    # Try to set Mono8 if supported
                    try:
                        cam.set_pixel_format(PixelFormat.Mono8)
                    except Exception:
                        # Fallback: will convert in handler
                        pass

                    self._running = True
                    cam.start_streaming(handler)
                    self.startedStreaming.emit()
                    try:
                        while self._running:
                            self.msleep(10)
                    finally:
                        cam.stop_streaming()
                        self.stoppedStreaming.emit()
        except Exception as e:
            self.error.emit(str(e))
