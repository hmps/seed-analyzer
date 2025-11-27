"""Application configuration."""

from dataclasses import dataclass


@dataclass
class ProcessingConfig:
    """Configuration for image processing."""

    grid_size_mm: float = 1.0
    min_seed_area_mm2: float = 0.5
    max_seed_area_mm2: float = 100.0

    # Percentile thresholds for large/small classification
    large_percentile: float = 75.0
    small_percentile: float = 25.0


MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}
