"""Pydantic schemas for API request/response models."""

from enum import Enum
from pydantic import BaseModel, Field


class SeedShape(str, Enum):
    """Seed shape classification based on aspect ratio."""

    CIRCULAR = "circular"
    OVAL = "oval"
    ELONGATED = "elongated"


class Coordinates(BaseModel):
    """2D coordinates."""

    x: float
    y: float


class SeedResult(BaseModel):
    """Measurement result for a single seed."""

    id: int
    length_mm: float = Field(description="Length (major axis) in millimeters")
    width_mm: float = Field(description="Width (minor axis) in millimeters")
    aspect_ratio: float = Field(description="Length divided by width")
    shape: SeedShape
    area_mm2: float = Field(description="Area in square millimeters")
    center: Coordinates = Field(description="Center position in image pixels")


class DimensionStats(BaseModel):
    """Statistics for a dimension (length or width)."""

    min_mm: float
    max_mm: float
    mean_mm: float
    std_mm: float


class DimensionsSummary(BaseModel):
    """Summary statistics for seed dimensions."""

    length: DimensionStats
    width: DimensionStats


class ShapeDistribution(BaseModel):
    """Count of seeds by shape classification."""

    circular: int
    oval: int
    elongated: int


class SizeRatio(BaseModel):
    """Large to small seed ratio information."""

    large_count: int = Field(description="Number of seeds in top 25% by area")
    small_count: int = Field(description="Number of seeds in bottom 25% by area")
    ratio: float = Field(description="Ratio of large to small seeds")


class AnalysisSummary(BaseModel):
    """Summary statistics for all detected seeds."""

    total_seed_count: int
    dimensions: DimensionsSummary
    shape_distribution: ShapeDistribution
    size_ratio: SizeRatio


class CalibrationInfo(BaseModel):
    """Grid calibration information."""

    pixels_per_mm: float
    grid_lines_detected: int
    confidence: float = Field(ge=0.0, le=1.0)


class AnalysisResponse(BaseModel):
    """Complete analysis response."""

    success: bool
    processing_time_ms: int
    calibration: CalibrationInfo
    summary: AnalysisSummary
    seeds: list[SeedResult]


class ErrorDetail(BaseModel):
    """Error response detail."""

    code: str
    message: str
    details: dict = Field(default_factory=dict)
    suggestions: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Error response."""

    success: bool = False
    error: ErrorDetail
