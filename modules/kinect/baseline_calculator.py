import numpy as np
import logging
from config import Config

class BaselineCalculator:
    """
    Accumulates depth frames to compute and provide a baseline (background reference).

    - On initialization, no baseline is set.
    - `update(frame)` accumulates up to `config.n_profile` frames, then computes the mean baseline.
    - `reset()` clears accumulation and baseline (e.g., on tool change).
    - `baseline` property returns the current baseline or raises if not ready.
    """

    def __init__(self, config: Config, logger=None):
        self.config = config
        self._frames_sum = None  # sum of frames
        self._count = 0          # number of frames accumulated
        self._baseline = None    # computed baseline
        self.logger = logger or logging.getLogger(__name__)

        if self.config.debug_mode:
            self.logger.setLevel(logging.DEBUG)
            logger.debug("BaselineCalculator created with n_profile=%d", config.n_profile)

    def ensure_baseline_ready(self, frame: np.ndarray) -> np.ndarray:
        """
        1) Si la baseline n'est pas encore prête (RuntimeError), on accumule cette frame
        et on relance l'exception pour signaler « pas encore prêt ».
        2) Sinon, on retourne directement self.baseline.
        """
        try:
            return self.baseline
        except RuntimeError:
            self.update(frame)
            raise

    def update(self, frame: np.ndarray) -> None:
        """
        Add a new frame to the accumulator.
        Once `n_profile` frames are collected, compute the baseline.
        """
        if self._baseline is not None:
            # Baseline already computed; no further accumulation
            return
        if self._frames_sum is None:
            self._frames_sum = np.zeros_like(frame, dtype=np.float64)
        self._frames_sum += frame.astype(np.float64)
        self._count += 1
        self.logger.debug("Accumulating frame %d/%d", self._count, self.config.n_profile)
        if self._count >= self.config.n_profile:
            # Compute mean baseline
            self._baseline = (self._frames_sum / self._count).astype(frame.dtype)
            self.logger.info("Baseline computed after %d frames", self._count)
            # Optionally free sum to save memory
            self._frames_sum = None

    @property
    def baseline(self) -> np.ndarray:
        """
        Return the computed baseline.
        Raises:
            RuntimeError if baseline is not yet ready.
        """
        if self._baseline is None:
            raise RuntimeError("Baseline not ready: needs %d frames" % self.config.n_profile)
        return self._baseline

    def reset(self) -> None:
        """
        Reset the accumulator and clear any existing baseline.
        Useful when tool or context changes.
        """
        self.logger.info("Resetting baseline calculator")
        self._frames_sum = None
        self._count = 0
        self._baseline = None
    