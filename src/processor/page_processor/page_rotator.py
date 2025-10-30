import cv2
import fitz
import numpy as np
import pytesseract
from loguru import logger


class PageRotator:
    """Rotate PDF pages while keeping the original content (e.g. widgets) intact."""

    _LANDSCAPE_ROTATION = 90
    _UPSIDE_DOWN_ANGLE = 180
    _PIXMAP_SCALE = 3.0
    _MAX_DIMENSION = 4000

    def rotate(self, page: fitz.Page) -> int:
        """Rotate the supplied page in-place and return the net rotation applied.

        The method only updates the page metadata so the underlying PDF objects
        (forms, annotations, etc.) remain untouched.
        """
        net_rotation = 0

        if self._is_landscape(page):
            net_rotation += self._apply_rotation(page,
                                                 self._LANDSCAPE_ROTATION)

        net_rotation += self._correct_upside_down(page)
        return net_rotation

    def _is_landscape(self, page: fitz.Page) -> bool:
        return page.rect.width > page.rect.height

    def _apply_rotation(self, page: fitz.Page, angle: int) -> int:
        target_rotation = (page.rotation + angle) % 360
        page.set_rotation(target_rotation)
        logger.debug(
            "Rotated page {} by {} degrees (new rotation: {})",
            page.number + 1,
            angle,
            target_rotation,
        )
        return angle

    def _correct_upside_down(self, page: fitz.Page) -> int:
        pix = page.get_pixmap(matrix=fitz.Matrix(
            self._PIXMAP_SCALE, self._PIXMAP_SCALE))
        image = self._pix_to_cv2_image(pix)

        text_orientation = self._get_text_orientation(image, page.number)
        if text_orientation == self._UPSIDE_DOWN_ANGLE:
            self._apply_rotation(page, self._UPSIDE_DOWN_ANGLE)
            logger.debug(
                "Corrected upside-down orientation on page {}", page.number + 1)
            return self._UPSIDE_DOWN_ANGLE

        logger.debug("Page {} orientation is correct", page.number + 1)
        return 0

    def _get_text_orientation(self, image: np.ndarray, page_num: int) -> int:
        """Return the detected text orientation in degrees."""
        image_for_osd = self._downscale_for_osd(image)

        try:
            if image_for_osd.ndim == 2:
                gray = image_for_osd
            else:
                gray = cv2.cvtColor(image_for_osd, cv2.COLOR_BGR2GRAY)

            # min_characters_to_try improves accuracy for sparse documents.
            result = pytesseract.image_to_osd(
                gray, output_type="dict", config="--psm 0 -c min_characters_to_try=200"
            )
            orientation = result.get("orientation", 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to detect text orientation on page {}: {}", page_num + 1, exc
            )
            orientation = 0

        logger.debug("Detected text orientation for page {}: {} deg",
                     page_num + 1, orientation)
        return orientation

    def _downscale_for_osd(self, image: np.ndarray) -> np.ndarray:
        height, width = image.shape[:2]
        max_dim = max(height, width)
        if max_dim <= self._MAX_DIMENSION:
            return image

        scale = self._MAX_DIMENSION / max_dim
        new_size = (int(width * scale), int(height * scale))
        return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

    def _pix_to_cv2_image(self, pix: fitz.Pixmap) -> np.ndarray:
        # If the image is CMYK convert it to RGB before handing to OpenCV.
        if pix.n - pix.alpha == 4:
            pix = fitz.Pixmap(fitz.csRGB, pix)

        if pix.n - pix.alpha == 1:
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.h, pix.w).copy()
            return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.h, pix.w, pix.n).copy()
        if pix.alpha:
            img = img[:, :, :3]

        if pix.colorspace == fitz.csRGB:
            return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        return img
