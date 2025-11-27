"""API endpoint definitions."""

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from seed_analyzer.core.config import (
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE,
    ProcessingConfig,
)
from seed_analyzer.core.exceptions import (
    CalibrationError,
    ImageFormatError,
    ImageTooLargeError,
    NoSeedsDetectedError,
    SeedAnalysisError,
)
from seed_analyzer.processing.pipeline import AnalysisPipeline
from .schemas import (
    AnalysisResponse,
    AnalysisSummary,
    CalibrationInfo,
    Coordinates,
    DimensionsSummary,
    DimensionStats,
    ErrorDetail,
    ErrorResponse,
    SeedResult,
    SeedShape,
    ShapeDistribution,
    SizeRatio,
)

router = APIRouter()


async def validate_and_load_image(file: UploadFile) -> np.ndarray:
    """Validate uploaded file and convert to OpenCV image."""
    # Check content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ImageFormatError(f"Unsupported format: {file.content_type}")

    # Read file in chunks to check size
    chunks = []
    total_size = 0

    while chunk := await file.read(1024 * 1024):  # 1MB chunks
        total_size += len(chunk)
        if total_size > MAX_FILE_SIZE:
            raise ImageTooLargeError(f"File exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit")
        chunks.append(chunk)

    # Combine chunks and decode
    file_bytes = b"".join(chunks)
    nparr = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        raise ImageFormatError("Could not decode image data")

    return image


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "seed-analyzer"}


@router.post("/analyze", response_model=AnalysisResponse, responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
async def analyze_seeds(
    image: UploadFile = File(..., description="Image of seeds on millimeter grid paper"),
    grid_size_mm: float = Form(default=1.0, gt=0, le=10, description="Grid spacing in mm"),
    min_seed_area_mm2: float = Form(default=0.5, gt=0, description="Minimum seed area in mm²"),
    max_seed_area_mm2: float = Form(default=100.0, gt=0, description="Maximum seed area in mm²"),
):
    """
    Analyze seeds in an uploaded image.

    Returns dimensions, shape classification, and statistics for all detected seeds.
    """
    try:
        # Load and validate image
        img = await validate_and_load_image(image)

        # Configure and run pipeline
        config = ProcessingConfig(
            grid_size_mm=grid_size_mm,
            min_seed_area_mm2=min_seed_area_mm2,
            max_seed_area_mm2=max_seed_area_mm2,
        )
        pipeline = AnalysisPipeline(config)
        result = pipeline.analyze(img)

        # Build response
        seeds = [
            SeedResult(
                id=m.id,
                length_mm=m.length_mm,
                width_mm=m.width_mm,
                aspect_ratio=m.aspect_ratio,
                shape=SeedShape(m.shape.value),
                area_mm2=m.area_mm2,
                center=Coordinates(x=m.center_x, y=m.center_y),
            )
            for m in result.measurements
        ]

        stats = result.statistics
        summary = AnalysisSummary(
            total_seed_count=stats["total_seed_count"],
            dimensions=DimensionsSummary(
                length=DimensionStats(**stats["dimensions"]["length"]),
                width=DimensionStats(**stats["dimensions"]["width"]),
            ),
            shape_distribution=ShapeDistribution(**stats["shape_distribution"]),
            size_ratio=SizeRatio(**stats["size_ratio"]),
        )

        return AnalysisResponse(
            success=True,
            processing_time_ms=result.processing_time_ms,
            calibration=CalibrationInfo(
                pixels_per_mm=result.calibration.pixels_per_mm,
                grid_lines_detected=result.calibration.grid_lines_detected,
                confidence=result.calibration.confidence,
            ),
            summary=summary,
            seeds=seeds,
        )

    except SeedAnalysisError as e:
        error_detail = ErrorDetail(
            code=e.code,
            message=e.message,
            details=e.details,
            suggestions=getattr(e, "suggestions", []),
        )
        raise HTTPException(status_code=e.status_code, detail=error_detail.model_dump())

    except Exception as e:
        error_detail = ErrorDetail(
            code="INTERNAL_ERROR",
            message=str(e),
        )
        raise HTTPException(status_code=500, detail=error_detail.model_dump())
