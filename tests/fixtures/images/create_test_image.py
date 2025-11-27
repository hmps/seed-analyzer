"""Create a synthetic test image for pipeline testing."""

import cv2
import numpy as np


def create_test_image(output_path: str):
    """Create a test image with grid and seeds."""
    # Create white background
    img = np.ones((800, 800, 3), dtype=np.uint8) * 255

    # Draw 1mm grid (assuming 25 pixels per mm for this test)
    grid_spacing = 25
    grid_color = (200, 200, 200)  # Light gray

    # Vertical lines
    for x in range(0, 800, grid_spacing):
        cv2.line(img, (x, 0), (x, 800), grid_color, 1)

    # Horizontal lines
    for y in range(0, 800, grid_spacing):
        cv2.line(img, (0, y), (800, y), grid_color, 1)

    # Draw some seeds (brown ellipses)
    seed_color = (50, 100, 150)  # BGR - brownish color

    # Circular seed (aspect ratio ~1.0)
    cv2.ellipse(img, (100, 100), (30, 28), 0, 0, 360, seed_color, -1)

    # Oval seeds (aspect ratio ~1.5)
    cv2.ellipse(img, (200, 200), (45, 30), 30, 0, 360, seed_color, -1)
    cv2.ellipse(img, (350, 150), (40, 28), -20, 0, 360, seed_color, -1)

    # Elongated seeds (aspect ratio > 1.8)
    cv2.ellipse(img, (500, 300), (60, 25), 45, 0, 360, seed_color, -1)
    cv2.ellipse(img, (150, 400), (55, 22), -10, 0, 360, seed_color, -1)

    # More varied seeds
    cv2.ellipse(img, (400, 500), (35, 32), 15, 0, 360, seed_color, -1)  # Circular
    cv2.ellipse(img, (600, 400), (50, 35), 60, 0, 360, seed_color, -1)  # Oval
    cv2.ellipse(img, (300, 600), (65, 28), -45, 0, 360, seed_color, -1)  # Elongated
    cv2.ellipse(img, (550, 650), (42, 30), 0, 0, 360, seed_color, -1)  # Oval
    cv2.ellipse(img, (700, 200), (38, 35), 0, 0, 360, seed_color, -1)  # Circular

    cv2.imwrite(output_path, img)
    print(f"Created test image at: {output_path}")


if __name__ == "__main__":
    create_test_image("test_seeds.jpg")
