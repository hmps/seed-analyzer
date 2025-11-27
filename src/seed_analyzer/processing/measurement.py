"""Seed measurement using ellipse fitting."""

from dataclasses import dataclass
from enum import Enum
import cv2
import numpy as np


class SeedShape(str, Enum):
    """Seed shape classification."""

    CIRCULAR = "circular"
    OVAL = "oval"
    ELONGATED = "elongated"


@dataclass
class SeedMeasurement:
    """Measurement result for a single seed."""

    id: int
    length_mm: float
    width_mm: float
    aspect_ratio: float
    shape: SeedShape
    area_mm2: float
    center_x: float
    center_y: float


class SeedMeasurer:
    """Measures seed dimensions using ellipse fitting."""

    # Shape classification thresholds
    CIRCULAR_THRESHOLD = 1.2
    OVAL_THRESHOLD = 1.8

    def measure(self, contour: np.ndarray, pixels_per_mm: float, seed_id: int) -> SeedMeasurement:
        """
        Measure a single seed contour.

        Args:
            contour: OpenCV contour of the seed
            pixels_per_mm: Calibration factor
            seed_id: Unique identifier for this seed

        Returns:
            SeedMeasurement with dimensions and classification
        """
        # Fit ellipse if enough points
        if len(contour) >= 5:
            ellipse = cv2.fitEllipse(contour)
            (center_x, center_y), (axis1, axis2), _ = ellipse

            # axis1 and axis2 are NOT guaranteed to be in major/minor order
            major_axis_px = max(axis1, axis2)
            minor_axis_px = min(axis1, axis2)
        else:
            # Fallback to bounding rectangle
            rect = cv2.minAreaRect(contour)
            (center_x, center_y), (w, h), _ = rect
            major_axis_px = max(w, h)
            minor_axis_px = min(w, h)

        # Convert to millimeters
        length_mm = major_axis_px / pixels_per_mm
        width_mm = minor_axis_px / pixels_per_mm

        # Calculate aspect ratio
        if width_mm > 0:
            aspect_ratio = length_mm / width_mm
        else:
            aspect_ratio = float("inf")

        # Classify shape
        shape = self._classify_shape(aspect_ratio)

        # Calculate area
        area_px = cv2.contourArea(contour)
        area_mm2 = area_px / (pixels_per_mm**2)

        return SeedMeasurement(
            id=seed_id,
            length_mm=round(length_mm, 3),
            width_mm=round(width_mm, 3),
            aspect_ratio=round(aspect_ratio, 3),
            shape=shape,
            area_mm2=round(area_mm2, 3),
            center_x=round(center_x, 1),
            center_y=round(center_y, 1),
        )

    def _classify_shape(self, aspect_ratio: float) -> SeedShape:
        """Classify seed shape based on aspect ratio."""
        if aspect_ratio < self.CIRCULAR_THRESHOLD:
            return SeedShape.CIRCULAR
        elif aspect_ratio <= self.OVAL_THRESHOLD:
            return SeedShape.OVAL
        else:
            return SeedShape.ELONGATED

    def calculate_statistics(
        self, measurements: list[SeedMeasurement], large_percentile: float, small_percentile: float
    ) -> dict:
        """
        Calculate summary statistics for all seed measurements.

        Args:
            measurements: List of seed measurements
            large_percentile: Percentile threshold for "large" seeds (e.g., 75)
            small_percentile: Percentile threshold for "small" seeds (e.g., 25)

        Returns:
            Dictionary with summary statistics
        """
        if not measurements:
            return {}

        lengths = [m.length_mm for m in measurements]
        widths = [m.width_mm for m in measurements]
        areas = [m.area_mm2 for m in measurements]

        # Calculate percentile thresholds for size ratio
        large_threshold = float(np.percentile(areas, large_percentile))
        small_threshold = float(np.percentile(areas, small_percentile))

        large_count = sum(1 for a in areas if a >= large_threshold)
        small_count = sum(1 for a in areas if a <= small_threshold)

        # Shape distribution
        shape_counts = {SeedShape.CIRCULAR: 0, SeedShape.OVAL: 0, SeedShape.ELONGATED: 0}
        for m in measurements:
            shape_counts[m.shape] += 1

        return {
            "total_seed_count": len(measurements),
            "dimensions": {
                "length": {
                    "min_mm": round(min(lengths), 3),
                    "max_mm": round(max(lengths), 3),
                    "mean_mm": round(float(np.mean(lengths)), 3),
                    "std_mm": round(float(np.std(lengths)), 3),
                },
                "width": {
                    "min_mm": round(min(widths), 3),
                    "max_mm": round(max(widths), 3),
                    "mean_mm": round(float(np.mean(widths)), 3),
                    "std_mm": round(float(np.std(widths)), 3),
                },
            },
            "shape_distribution": {
                "circular": shape_counts[SeedShape.CIRCULAR],
                "oval": shape_counts[SeedShape.OVAL],
                "elongated": shape_counts[SeedShape.ELONGATED],
            },
            "size_ratio": {
                "large_count": large_count,
                "small_count": small_count,
                "ratio": round(large_count / small_count, 3) if small_count > 0 else 0.0,
            },
        }
