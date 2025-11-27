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
        max_single_seed_area_mm2: float = 12.0,  # Max ~5mm x 2.5mm seed
        max_seed_length_mm: float = 6.0,  # Max length for a single seed
    ) -> list[np.ndarray]:
        """
        Segment seeds from the image.

        Args:
            image: BGR image with seeds on grid paper
            pixels_per_mm: Calibration factor from grid detection
            min_seed_area_mm2: Minimum seed area to detect
            max_seed_area_mm2: Maximum seed area to detect
            max_single_seed_area_mm2: Max area for a single seed (larger = multiple seeds)
            max_seed_length_mm: Max length for a single seed (longer = multiple seeds)

        Returns:
            List of contours, one per detected seed
        """
        # Convert area thresholds to pixels
        min_area_px = min_seed_area_mm2 * (pixels_per_mm**2)
        max_area_px = max_seed_area_mm2 * (pixels_per_mm**2)
        max_single_seed_area_px = max_single_seed_area_mm2 * (pixels_per_mm**2)
        max_length_px = max_seed_length_mm * pixels_per_mm

        # Create seed mask
        mask = self._create_seed_mask(image)

        # Find initial contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Process contours: filter by size and split overlapping seeds
        result_contours = []

        for contour in contours:
            area = cv2.contourArea(contour)

            # Skip if too small
            if area < min_area_px:
                continue

            # Check if contour is too large (by area or length)
            is_too_large = area > max_single_seed_area_px
            if not is_too_large and len(contour) >= 5:
                _, (w, h), _ = cv2.fitEllipse(contour)
                major_axis = max(w, h)
                is_too_large = major_axis > max_length_px

            # If larger than expected single seed, try to split
            if is_too_large:
                split_contours = self._split_overlapping_seeds(
                    mask, contour, min_area_px, max_single_seed_area_px,
                    pixels_per_mm, max_length_px
                )
                if split_contours:
                    result_contours.extend(split_contours)
                # If can't split and too large, skip this cluster entirely
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
        pixels_per_mm: float,
        max_length_px: float,
    ) -> list[np.ndarray]:
        """
        Use watershed algorithm to split overlapping seeds.

        Returns list of separated contours, or empty list if splitting failed.
        """
        # Create mask just for this contour region
        mask = np.zeros(full_mask.shape, dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, -1)

        # Erode slightly to separate touching seeds before distance transform
        erode_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        eroded_mask = cv2.erode(mask, erode_kernel, iterations=2)

        # Distance transform - peaks are seed centers
        dist_transform = cv2.distanceTransform(eroded_mask, cv2.DIST_L2, 5)

        # Use a lower threshold to find more peaks (0.2 instead of 0.4)
        # Also use absolute minimum based on expected seed size (~1mm radius = pixels_per_mm)
        min_dist = max(pixels_per_mm * 0.5, 3)  # At least 0.5mm from edge
        threshold = max(0.2 * dist_transform.max(), min_dist)

        _, sure_fg = cv2.threshold(dist_transform, threshold, 255, cv2.THRESH_BINARY)
        sure_fg = np.uint8(sure_fg)

        # Find connected components in sure_fg (each peak is a seed)
        num_labels, labels = cv2.connectedComponents(sure_fg)

        # If only one peak found, try with even lower threshold
        if num_labels <= 2:
            threshold = max(0.15 * dist_transform.max(), min_dist * 0.5)
            _, sure_fg = cv2.threshold(dist_transform, threshold, 255, cv2.THRESH_BINARY)
            sure_fg = np.uint8(sure_fg)
            num_labels, labels = cv2.connectedComponents(sure_fg)

        # If still only one peak, estimate based on area
        if num_labels <= 2:
            contour_area = cv2.contourArea(contour)
            expected_seeds = max(2, int(contour_area / max_area_px) + 1)
            # Use k-means on distance transform peaks as fallback
            if expected_seeds >= 2:
                # Find local maxima using dilation comparison
                dilated = cv2.dilate(dist_transform, np.ones((7, 7)))
                local_max = (dist_transform == dilated) & (dist_transform > min_dist)
                coords = np.column_stack(np.where(local_max))
                if len(coords) >= 2:
                    # Create markers from local maxima
                    sure_fg = np.zeros_like(mask)
                    for i, (y, x) in enumerate(coords[:min(expected_seeds * 2, 20)]):
                        cv2.circle(sure_fg, (x, y), int(min_dist), 255, -1)
                    num_labels, labels = cv2.connectedComponents(sure_fg)

        if num_labels <= 2:
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
        markers_result = cv2.watershed(img_3ch, markers.copy())

        # Extract contours for each seed (labels > 1, excluding background)
        result_contours = []
        for label_id in range(2, num_labels + 1):
            seed_mask = np.uint8(markers_result == label_id) * 255
            seed_contours, _ = cv2.findContours(
                seed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for c in seed_contours:
                area = cv2.contourArea(c)

                # Check if too large by area or length
                is_too_large = area > max_area_px
                major_axis = 0
                if len(c) >= 5:
                    _, (w, h), _ = cv2.fitEllipse(c)
                    major_axis = max(w, h)
                    if not is_too_large:
                        is_too_large = major_axis > max_length_px

                # Recursively split if still too large
                if is_too_large:
                    sub_split = self._split_overlapping_seeds(
                        full_mask, c, min_area_px, max_area_px, pixels_per_mm, max_length_px
                    )
                    if sub_split:
                        result_contours.extend(sub_split)
                    # If can't split, discard this cluster
                elif min_area_px <= area <= max_area_px and self._is_valid_seed_shape(c):
                    # Final check: ensure length is within bounds
                    if major_axis <= max_length_px or len(c) < 5:
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
