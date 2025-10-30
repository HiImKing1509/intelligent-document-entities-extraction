import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import fitz
import numpy as np
from loguru import logger


@dataclass(frozen=True)
class SkewDetectionResult:
    angle: float
    image_bytes: Optional[bytes]
    width_pts: float
    height_pts: float


class SkewDetector:
    """Detect and correct page skew in PDFs rendered via PyMuPDF."""

    def __init__(
        self,
        max_skew: float = 15.0,
        min_correction: float = 0.3,
        detection_dpi: int = 300,
        max_detection_size: int = 2000,
    ) -> None:
        """
        Args:
            max_skew: Maximum absolute skew angle (degrees) that will be corrected.
                      Larger detected skews are treated as false positives.
            min_correction: Ignore angles smaller than this value to avoid jitter.
            detection_dpi: Rendering DPI used when rasterising PDF pages for analysis.
            max_detection_size: Largest dimension (pixels) used when analysing the page.
                                Pages larger than this are downscaled to keep processing fast.
        """
        if detection_dpi < 72:
            raise ValueError("detection_dpi must be at least 72.")
        if max_detection_size < 256:
            raise ValueError("max_detection_size must be >= 256.")

        self.max_skew = float(max_skew)
        self.min_correction = float(min_correction)
        self._render_scale = detection_dpi / 72.0
        self._analysis_scale_limit = int(max_detection_size)
        self._render_matrix = fitz.Matrix(
            self._render_scale, self._render_scale)

    def detect_skew_angle(self, page: fitz.Page) -> float:
        """Return the estimated skew angle (degrees) for a PDF page."""
        analysis_image, _ = self._page_to_numpy(page, retain_scale=False)
        return self._estimate_angle(analysis_image)

    def deskew_page(self, page: fitz.Page) -> SkewDetectionResult:
        """Return skew correction artefacts for a page. If no correction needed, image_bytes is None."""
        raster, (scale_x, scale_y) = self._page_to_numpy(
            page, retain_scale=True)
        angle = self._estimate_angle(raster)

        if abs(angle) < self.min_correction:
            return SkewDetectionResult(angle=0.0, image_bytes=None, width_pts=page.rect.width, height_pts=page.rect.height)

        rotated = self._rotate_image(raster, angle)
        width_pts = rotated.shape[1] * scale_x
        height_pts = rotated.shape[0] * scale_y

        encode_params = [int(cv2.IMWRITE_PNG_COMPRESSION), 9]
        try:
            success, buffer = cv2.imencode(".png", rotated, encode_params)
        except cv2.error as exc:  # pragma: no cover - guard against OpenCV backend issues
            logger.warning(f"Failed to encode rotated page as PNG: {exc}")
            return SkewDetectionResult(angle=0.0, image_bytes=None, width_pts=page.rect.width, height_pts=page.rect.height)

        if not success:
            logger.warning(
                "OpenCV failed to encode rotated image; falling back to uncorrected page.")
            return SkewDetectionResult(angle=0.0, image_bytes=None, width_pts=page.rect.width, height_pts=page.rect.height)

        return SkewDetectionResult(angle=angle, image_bytes=buffer.tobytes(), width_pts=width_pts, height_pts=height_pts)

    def _page_to_numpy(self, page: fitz.Page, retain_scale: bool) -> Tuple[np.ndarray, Tuple[float, float]]:
        pix = page.get_pixmap(matrix=self._render_matrix, alpha=False)
        image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n)

        if pix.n == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        elif pix.n == 1:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:  # pragma: no cover - unexpected pixmap format
            raise ValueError(f"Unsupported pixmap channels: {pix.n}")

        if not retain_scale:
            analysis_image = self._downscale_for_analysis(image)
            return analysis_image, (1.0, 1.0)

        scale_x = page.rect.width / float(pix.width)
        scale_y = page.rect.height / float(pix.height)
        return image, (scale_x, scale_y)

    def _downscale_for_analysis(self, image: np.ndarray) -> np.ndarray:
        height, width = image.shape[:2]
        max_dim = max(height, width)

        if max_dim <= self._analysis_scale_limit:
            return image

        scale = self._analysis_scale_limit / float(max_dim)
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

    def _estimate_angle(self, image: np.ndarray) -> float:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        binary = cv2.bitwise_not(binary)

        kernel_width = max(3, int(round(image.shape[1] * 0.015)))
        if kernel_width % 2 == 0:
            kernel_width += 1
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 3))
        morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        morph = cv2.erode(morph, np.ones((3, 3), dtype=np.uint8), iterations=1)

        edges = cv2.Canny(morph, 50, 150, apertureSize=3, L2gradient=True)

        weighted_angles = self._collect_hough_segment_angles(edges)
        if weighted_angles:
            angle = self._robust_weighted_angle(weighted_angles)
            if abs(angle) <= self.max_skew:
                return angle

        weighted_angles = self._collect_standard_hough_angles(edges)
        if weighted_angles:
            angle = self._robust_weighted_angle(weighted_angles)
            if abs(angle) <= self.max_skew:
                return angle

        coords = cv2.findNonZero(morph)
        if coords is None:
            return 0.0

        angle = self._angle_from_pca(coords)
        if abs(angle) <= self.max_skew:
            return angle

        return self._angle_from_min_area(coords)

    def _collect_hough_segment_angles(self, edges: np.ndarray) -> List[Tuple[float, float]]:
        height, width = edges.shape[:2]
        threshold = max(60, int(0.12 * min(height, width)))
        min_line_length = max(width // 4, 40)
        max_line_gap = max(10, min_line_length // 6)

        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 360.0,
            threshold=threshold,
            minLineLength=min_line_length,
            maxLineGap=max_line_gap,
        )

        if lines is None:
            return []

        weighted_angles: List[Tuple[float, float]] = []
        for x1, y1, x2, y2 in lines[:, 0]:
            dx = x2 - x1
            dy = y2 - y1
            if dx == 0 and dy == 0:
                continue
            angle = math.degrees(math.atan2(dy, dx))
            angle = self._normalise_angle(angle)
            length = math.hypot(dx, dy)
            if abs(angle) <= 90.0 and length >= 5:
                weighted_angles.append((angle, length))
        return weighted_angles

    def _collect_standard_hough_angles(self, edges: np.ndarray) -> List[Tuple[float, float]]:
        height, width = edges.shape[:2]
        accumulator_threshold = max(80, int(0.08 * max(height, width)))
        lines = cv2.HoughLines(edges, 1, np.pi / 1800.0, accumulator_threshold)

        if lines is None:
            return []

        weighted_angles: List[Tuple[float, float]] = []
        for rho, theta in lines[:, 0]:
            angle = (theta - np.pi / 2.0) * 180.0 / np.pi
            angle = self._normalise_angle(angle)
            weight = max(1.0, abs(rho))
            if abs(angle) <= 90.0:
                weighted_angles.append((angle, weight))
        return weighted_angles

    def _robust_weighted_angle(self, weighted_angles: List[Tuple[float, float]]) -> float:
        if not weighted_angles:
            return 0.0

        angles = np.array([a for a, _ in weighted_angles], dtype=np.float32)
        weights = np.array([w for _, w in weighted_angles], dtype=np.float32)

        sorter = np.argsort(angles)
        angles = angles[sorter]
        weights = weights[sorter]
        cumulative = np.cumsum(weights)
        cutoff = cumulative[-1] * 0.5
        median_idx = int(np.searchsorted(cumulative, cutoff))
        return float(angles[min(median_idx, len(angles) - 1)])

    def _angle_from_pca(self, coords: np.ndarray) -> float:
        points = coords.reshape(-1, 2).astype(np.float32)
        mean, eigenvectors = cv2.PCACompute(points, mean=None, maxComponents=1)
        if eigenvectors is None or eigenvectors.size == 0:
            return 0.0
        direction = eigenvectors[0]
        angle = math.degrees(math.atan2(direction[1], direction[0]))
        return self._normalise_angle(angle)

    def _angle_from_min_area(self, coords: np.ndarray) -> float:
        box = cv2.minAreaRect(coords)
        angle = box[-1]
        if angle < -45.0:
            angle = -(90.0 + angle)
        else:
            angle = -angle

        if not math.isfinite(angle):
            return 0.0

        angle = float(angle)
        if abs(angle) > self.max_skew:
            return 0.0
        return angle

    @staticmethod
    def _normalise_angle(angle: float) -> float:
        while angle <= -90.0:
            angle += 180.0
        while angle > 90.0:
            angle -= 180.0
        return angle

    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        if abs(angle) < self.min_correction:
            return image

        height, width = image.shape[:2]
        center = (width / 2.0, height / 2.0)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        cos = abs(rotation_matrix[0, 0])
        sin = abs(rotation_matrix[0, 1])
        bound_width = int(math.ceil(height * sin + width * cos))
        bound_height = int(math.ceil(height * cos + width * sin))

        rotation_matrix[0, 2] += bound_width / 2.0 - center[0]
        rotation_matrix[1, 2] += bound_height / 2.0 - center[1]

        return cv2.warpAffine(
            image,
            rotation_matrix,
            (bound_width, bound_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )
