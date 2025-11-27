"""Grid detection and calibration for pixel-to-millimeter conversion."""

from dataclasses import dataclass
import cv2
import numpy as np

from seed_analyzer.core.exceptions import CalibrationError


@dataclass
class CalibrationResult:
    """Result of grid calibration."""

    pixels_per_mm: float
    grid_lines_detected: int
    confidence: float


class GridCalibrator:
    """Detects millimeter grid and calculates pixel-to-mm conversion."""

    def __init__(self, grid_size_mm: float = 1.0):
        self.grid_size_mm = grid_size_mm
        self.min_lines_required = 5

    def calibrate(self, image: np.ndarray) -> CalibrationResult:
        """
        Detect grid lines and calculate pixels per millimeter.

        Args:
            image: BGR image containing millimeter grid paper

        Returns:
            CalibrationResult with pixel-to-mm conversion factor

        Raises:
            CalibrationError: If grid cannot be reliably detected
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Adaptive threshold to handle uneven lighting
        binary = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        # Detect edges
        edges = cv2.Canny(binary, 50, 150, apertureSize=3)

        # Detect lines using probabilistic Hough transform
        height, width = image.shape[:2]
        min_line_length = int(min(width, height) * 0.15)

        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=50,
            minLineLength=min_line_length,
            maxLineGap=10,
        )

        if lines is None or len(lines) < self.min_lines_required:
            raise CalibrationError(
                "Could not detect grid pattern in image",
                details={"lines_detected": 0 if lines is None else len(lines)},
            )

        # Classify lines as horizontal or vertical
        horizontal_lines = []
        vertical_lines = []

        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))

            # Horizontal: angle close to 0 or 180
            if abs(angle) < 15 or abs(angle) > 165:
                horizontal_lines.append((y1 + y2) / 2)  # Store y-position
            # Vertical: angle close to 90 or -90
            elif 75 < abs(angle) < 105:
                vertical_lines.append((x1 + x2) / 2)  # Store x-position

        # Need lines in both directions
        if len(horizontal_lines) < 3 or len(vertical_lines) < 3:
            raise CalibrationError(
                "Insufficient grid lines detected",
                details={
                    "horizontal_lines": len(horizontal_lines),
                    "vertical_lines": len(vertical_lines),
                },
            )

        # Calculate spacing between lines
        h_spacing = self._calculate_median_spacing(sorted(horizontal_lines))
        v_spacing = self._calculate_median_spacing(sorted(vertical_lines))

        if h_spacing is None or v_spacing is None:
            raise CalibrationError(
                "Could not determine consistent grid spacing",
                details={"h_spacing": h_spacing, "v_spacing": v_spacing},
            )

        # Average of horizontal and vertical spacing
        avg_spacing_pixels = (h_spacing + v_spacing) / 2
        pixels_per_mm = avg_spacing_pixels / self.grid_size_mm

        # Calculate confidence based on consistency
        spacing_consistency = 1.0 - abs(h_spacing - v_spacing) / max(h_spacing, v_spacing)
        line_count_factor = min(1.0, (len(horizontal_lines) + len(vertical_lines)) / 20)
        confidence = spacing_consistency * 0.7 + line_count_factor * 0.3

        total_lines = len(horizontal_lines) + len(vertical_lines)

        return CalibrationResult(
            pixels_per_mm=pixels_per_mm,
            grid_lines_detected=total_lines,
            confidence=round(confidence, 3),
        )

    def _calculate_median_spacing(self, positions: list[float]) -> float | None:
        """Calculate median spacing between sorted line positions."""
        if len(positions) < 2:
            return None

        # Calculate differences between adjacent lines
        spacings = []
        for i in range(1, len(positions)):
            diff = positions[i] - positions[i - 1]
            # Filter out very small gaps (noise) and very large gaps (missed lines)
            if diff > 5:  # Minimum 5 pixels between lines
                spacings.append(diff)

        if not spacings:
            return None

        # Use median to be robust to outliers
        median_spacing = float(np.median(spacings))

        # Filter to spacings close to median (within 50%)
        filtered = [s for s in spacings if 0.5 * median_spacing < s < 1.5 * median_spacing]

        if not filtered:
            return median_spacing

        return float(np.median(filtered))
