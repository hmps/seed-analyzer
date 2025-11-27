"""Seed detection and segmentation from images."""

import cv2
import numpy as np


class SeedSegmenter:
    """Detects and segments individual seeds from an image."""

    def __init__(self):
        # Morphological kernel for cleanup
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    def segment(
        self,
        image: np.ndarray,
        pixels_per_mm: float,
        min_seed_area_mm2: float = 0.5,
        max_seed_area_mm2: float = 100.0,
    ) -> list[np.ndarray]:
        """
        Segment seeds from the image.

        Args:
            image: BGR image with seeds on grid paper
            pixels_per_mm: Calibration factor from grid detection
            min_seed_area_mm2: Minimum seed area to detect
            max_seed_area_mm2: Maximum seed area to detect

        Returns:
            List of contours, one per detected seed
        """
        # Convert area thresholds to pixels
        min_area_px = min_seed_area_mm2 * (pixels_per_mm**2)
        max_area_px = max_seed_area_mm2 * (pixels_per_mm**2)

        # Create seed mask
        mask = self._create_seed_mask(image)

        # Find initial contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Process contours: filter by size and split overlapping seeds
        result_contours = []
        expected_max_single_seed_area = max_area_px * 0.6  # Threshold for splitting

        for contour in contours:
            area = cv2.contourArea(contour)

            # Skip if too small
            if area < min_area_px:
                continue

            # If very large, try to split using watershed
            if area > expected_max_single_seed_area:
                split_contours = self._split_overlapping_seeds(
                    mask, contour, min_area_px, max_area_px
                )
                if split_contours:
                    result_contours.extend(split_contours)
                    continue

            # Skip if too large (and couldn't be split)
            if area > max_area_px:
                continue

            # Validate shape (filter out noise)
            if self._is_valid_seed_shape(contour):
                result_contours.append(contour)

        return result_contours

    def _create_seed_mask(self, image: np.ndarray) -> np.ndarray:
        """Create binary mask of seed regions."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Use Otsu's thresholding to automatically find optimal threshold
        # This works well when there's a bimodal distribution (seeds vs background)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, otsu_mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Also try adaptive thresholding for uneven lighting
        adaptive_mask = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 5
        )

        # Combine both approaches
        seed_mask = cv2.bitwise_or(otsu_mask, adaptive_mask)

        # Remove very light areas (grid paper background)
        _, light_mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        seed_mask = cv2.bitwise_and(seed_mask, cv2.bitwise_not(light_mask))

        # Remove grid lines - they appear as thin structures
        # Use morphological opening with a larger kernel to remove thin lines
        line_removal_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        seed_mask = cv2.morphologyEx(seed_mask, cv2.MORPH_OPEN, line_removal_kernel)

        # Morphological cleanup
        # Opening removes small noise
        seed_mask = cv2.morphologyEx(seed_mask, cv2.MORPH_OPEN, self.morph_kernel)
        # Closing fills small holes
        closing_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        seed_mask = cv2.morphologyEx(seed_mask, cv2.MORPH_CLOSE, closing_kernel)

        return seed_mask

    def _split_overlapping_seeds(
        self,
        full_mask: np.ndarray,
        contour: np.ndarray,
        min_area_px: float,
        max_area_px: float,
    ) -> list[np.ndarray]:
        """
        Use watershed algorithm to split overlapping seeds.

        Returns list of separated contours, or empty list if splitting failed.
        """
        # Create mask just for this contour region
        mask = np.zeros(full_mask.shape, dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)

        # Distance transform - peaks are seed centers
        dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)

        # Find local maxima (sure foreground)
        _, sure_fg = cv2.threshold(
            dist_transform, 0.4 * dist_transform.max(), 255, cv2.THRESH_BINARY
        )
        sure_fg = np.uint8(sure_fg)

        # Find connected components in sure_fg (each peak is a seed)
        num_labels, labels = cv2.connectedComponents(sure_fg)

        # If only one peak found, can't split
        if num_labels <= 2:  # Background + 1 seed
            return []

        # Sure background (dilated region)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        sure_bg = cv2.dilate(mask, kernel, iterations=3)

        # Unknown region
        unknown = cv2.subtract(sure_bg, sure_fg)

        # Prepare markers for watershed
        markers = labels + 1  # Shift so background is 1, not 0
        markers[unknown == 255] = 0

        # Need 3-channel image for watershed
        img_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        markers = cv2.watershed(img_3ch, markers)

        # Extract contours for each seed (labels > 1, excluding background)
        result_contours = []
        for label_id in range(2, num_labels + 1):
            seed_mask = np.uint8(markers == label_id) * 255
            seed_contours, _ = cv2.findContours(
                seed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for c in seed_contours:
                area = cv2.contourArea(c)
                if min_area_px <= area <= max_area_px and self._is_valid_seed_shape(c):
                    result_contours.append(c)

        return result_contours

    def _is_valid_seed_shape(self, contour: np.ndarray) -> bool:
        """Check if contour has a valid seed-like shape."""
        area = cv2.contourArea(contour)
        if area < 10:  # Too small
            return False

        # Check solidity (area / convex hull area)
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        if hull_area == 0:
            return False

        solidity = area / hull_area
        if solidity < 0.6:  # Too concave, probably noise or merged seeds
            return False

        # Check aspect ratio isn't too extreme
        if len(contour) >= 5:
            _, (w, h), _ = cv2.fitEllipse(contour)
            if w > 0 and h > 0:
                aspect = max(w, h) / min(w, h)
                if aspect > 5:  # Too elongated, probably not a seed
                    return False

        return True
