"""Custom exceptions for seed analysis."""


class SeedAnalysisError(Exception):
    """Base exception for seed analysis errors."""

    code: str = "ANALYSIS_ERROR"
    status_code: int = 500

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class CalibrationError(SeedAnalysisError):
    """Grid detection/calibration failed."""

    code = "CALIBRATION_FAILED"
    status_code = 422

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, details)
        self.suggestions = [
            "Ensure the entire grid is visible in the image",
            "Check that lighting is even across the image",
            "Verify the grid paper is flat, not wrinkled",
        ]


class NoSeedsDetectedError(SeedAnalysisError):
    """No seeds found in image."""

    code = "NO_SEEDS_DETECTED"
    status_code = 422

    def __init__(self, message: str = "No seeds detected in the image"):
        super().__init__(message)
        self.suggestions = [
            "Ensure seeds are visible and have good contrast with the background",
            "Check that seeds are not too small or too large for the detection range",
        ]


class ImageFormatError(SeedAnalysisError):
    """Unsupported or corrupt image."""

    code = "INVALID_IMAGE"
    status_code = 400


class ImageTooLargeError(SeedAnalysisError):
    """Image exceeds size limits."""

    code = "IMAGE_TOO_LARGE"
    status_code = 413
