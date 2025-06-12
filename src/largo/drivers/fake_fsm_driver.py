import numpy as np
import logging
from rpyc.utils.classic import obtain

logger = logging.getLogger(__name__)

# Full disclosure this was almost entirely written by ChatGPT based on fake_odmr_driver.py
#  and the requirements of fsm_scan.py

class FakeFSM:
    """
    Simulate a fast-steering mirror (FSM) driver that produces faux photoluminescence maps
    with Gaussian blobs on top of baseline noise.
    """
    def __init__(self, num_blobs=5, region_size=50, baseline=100, noise_level=0.05):
        """
        Args:
            num_blobs (int): Number of Gaussian emitters (blobs) to simulate.
            region_size (float): Half-size of square region (in µm) over which blobs are placed.
            baseline (float): Baseline count level.
            noise_level (float): Relative standard deviation of additive Gaussian noise.
        """
        self.acq_rate = None
        self.position = {'x': 0.0, 'y': 0.0}
        self.num_blobs = num_blobs
        self.region_size = region_size
        self.baseline = baseline
        self.noise_level = noise_level
        self._generate_blobs()

    def __enter__(self):
        logger.info("Connected to FakeFSM")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("Disconnected from FakeFSM")

    def setAcqRate(self, rate):
        """
        Set the acquisition rate (Hz).
        """
        rate = obtain(rate)
        self.acq_rate = rate
        logger.info(f"Acquisition rate set to {self.acq_rate} Hz")

    def getAcqRate(self):
        """
        Get the current acquisition rate (Hz).
        """
        return self.acq_rate

    def move(self, point):
        """
        Move the FSM to a new (x, y) position (µm).
        """
        x, y = self._convert_point(point)
        self.position = {'x': x, 'y': y}
        logger.info(f"Moved fsm to (x={x}, y={y})")

    def line_scan(self, init_point, final_point, steps, pts_per_step):
        """
        Perform a line scan between two points and return one-dimensional data.

        Args:
            init_point: {'x': x0, 'y': y0} or (x0, y0)
            final_point: {'x': x1, 'y': y1} or (x1, y1)
            steps (int): Number of pixels along the line.
            pts_per_step (int): (ignored) number of acquisitions per pixel.

        Returns:
            numpy.ndarray of length `steps` with simulated counts.
        """
        init = obtain(init_point)
        final = obtain(final_point)
        x0, y0 = self._convert_point(init)
        x1, y1 = self._convert_point(final)

        # Generate pixel positions along x
        xs = np.linspace(x0, x1, steps)
        # Start with baseline
        data = np.full(steps, self.baseline, dtype=float)
        # Add Gaussian blob contributions
        for blob in self.blobs:
            dx = xs - blob['x0']
            dy = y0 - blob['y0']
            data += blob['amplitude'] * np.exp(-(dx**2 + dy**2) / (2 * blob['sigma']**2))
        # Add noise
        data += np.random.normal(scale=self.noise_level * self.baseline, size=steps)
        return data

    def _convert_point(self, point):
        """
        Normalize point format to (x, y) tuple.
        """
        p = obtain(point)
        if isinstance(p, dict) and 'x' in p and 'y' in p:
            return float(p['x']), float(p['y'])
        if hasattr(p, '__len__') and len(p) == 2:
            return float(p[0]), float(p[1])
        raise ValueError(f"Invalid point: {p}")

    def _generate_blobs(self):
        """
        Initialize random Gaussian blobs within the defined region.
        """
        self.blobs = []
        for _ in range(self.num_blobs):
            x0 = np.random.uniform(-self.region_size, self.region_size)
            y0 = np.random.uniform(-self.region_size, self.region_size)
            sigma = np.random.uniform(0.5, 2.0)
            amplitude = np.random.uniform(self.baseline, self.baseline * 5)
            self.blobs.append({'x0': x0, 'y0': y0, 'sigma': sigma, 'amplitude': amplitude})
            