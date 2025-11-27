"""Main processing pipeline orchestration."""

from dataclasses import dataclass
import time
import numpy as np

from seed_analyzer.core.config import ProcessingConfig
from seed_analyzer.core.exceptions import NoSeedsDetectedError
from .calibration import GridCalibrator, CalibrationResult
from .segmentation import SeedSegmenter
from .measurement import SeedMeasurer, SeedMeasurement


@dataclass
class AnalysisResult:
    """Complete analysis result."""

    calibration: CalibrationResult
    measurements: list[SeedMeasurement]
    statistics: dict
    processing_time_ms: int


class AnalysisPipeline:
    """Orchestrates the complete seed analysis pipeline."""

    def __init__(self, config: ProcessingConfig | None = None):
        self.config = config or ProcessingConfig()
        self.calibrator = GridCalibrator(self.config.grid_size_mm)
        self.segmenter = SeedSegmenter()
        self.measurer = SeedMeasurer()

    def analyze(self, image: np.ndarray) -> AnalysisResult:
        """
        Run complete analysis pipeline on an image.

        Args:
            image: BGR image with seeds on millimeter grid paper

        Returns:
            AnalysisResult with calibration, measurements, and statistics

        Raises:
            CalibrationError: If grid cannot be detected
            NoSeedsDetectedError: If no seeds are found
        """
        start_time = time.time()

        # Step 1: Calibrate using grid
        calibration = self.calibrator.calibrate(image)

        # Step 2: Segment seeds
        contours = self.segmenter.segment(
            image,
            calibration.pixels_per_mm,
            self.config.min_seed_area_mm2,
            self.config.max_seed_area_mm2,
        )

        if not contours:
            raise NoSeedsDetectedError()

        # Step 3: Measure each seed
        measurements = []
        for i, contour in enumerate(contours, start=1):
            measurement = self.measurer.measure(contour, calibration.pixels_per_mm, seed_id=i)
            measurements.append(measurement)

        # Step 4: Calculate statistics
        statistics = self.measurer.calculate_statistics(
            measurements, self.config.large_percentile, self.config.small_percentile
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        return AnalysisResult(
            calibration=calibration,
            measurements=measurements,
            statistics=statistics,
            processing_time_ms=processing_time_ms,
        )
