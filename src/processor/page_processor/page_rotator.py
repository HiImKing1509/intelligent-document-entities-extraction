import cv2
import fitz
import pytesseract
import numpy as np
from loguru import logger

from src.processor.page_processor.skew_detector import SkewDetector

class PageRotator:    
    VERTICAL_ANGLE = 90
    UPSIDE_DOWN_ANGLE = 180
    
    def __init__(self):
        self.skew_detector = SkewDetector()

    def rotate(self, page: fitz.Page) -> fitz.Page:
        # Implement your rotation logic here
        page, landscape_orientation = self.landscape_rotator(page)
        page, page_image, upside_down_orientation = self.upside_down_rotator(page)

        # Write code to save `page_image` for debugging if needed
        # cv2.imwrite(f"debug_page_{page.number + 1}.png", page_image)
        return page

    def _get_text_orientation(self, image, page_num: int) -> int:
        # Detect text direction
        # Downscale only if image is very large (e.g., width or height > 4000)
        max_dim = 4000
        orig_shape = image.shape
        scale_factor = 1.0
        if image.shape[0] > max_dim or image.shape[1] > max_dim:
            scale_factor = max_dim / max(image.shape[0], image.shape[1])
            new_size = (int(image.shape[1] * scale_factor), int(image.shape[0] * scale_factor))
            small_image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
            print(f"[Rotation] Downscaled image for orientation check: original={orig_shape}, new={small_image.shape}, scale_factor={scale_factor:.3f}")
        else:
            small_image = image
        try:
            if len(small_image.shape) < 3 or small_image.shape[2] == 1:
                gray = small_image
            else:
                gray = cv2.cvtColor(small_image, cv2.COLOR_BGR2GRAY)
            # min_characters_to_try is set to 200 to ensure that the orientation is detected accurately: https://github.com/tesseract-ocr/tesseract/issues/4172#issuecomment-1865313332
            result = pytesseract.image_to_osd(gray, output_type="dict", config='--psm 0 -c min_characters_to_try=200')
            text_orientation = result['orientation']
        except Exception as e:
            text_orientation = 0
        print(f"Text orientation for page {page_num + 1}: {text_orientation} degrees")
        return text_orientation
    
    def pix_to_cv2_image(self, pix):
        # If the image is CMYK, convert it to RGB
        if pix.n - pix.alpha == 4:  # CMYK
            pix = fitz.Pixmap(fitz.csRGB, pix)

        if pix.n - pix.alpha == 1:  # Grayscale
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w).copy()
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:  # RGB or RGBA
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n).copy()
            if pix.alpha:  # If there is an alpha channel, remove it
                img = img[:, :, :3]
            
            # Check if the image is already in BGR format
            if pix.colorspace == fitz.csRGB:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            # If it's not RGB, assume it's already in BGR format
        
        return img

    def landscape_rotator(self, page: fitz.Page) -> tuple[fitz.Page, int]:
        """ Determine page orientation by comparing width and height """
        is_landscape = page.rect.width > page.rect.height
        target_rotation = 0
        if is_landscape:
            current_rotation = page.rotation
            target_rotation = (current_rotation + 90) % 360
            page.set_rotation(target_rotation)
        else:
            logger.info(f"Page {page.number + 1} is in portrait orientation, no rotation needed")
            
        return page, target_rotation

    def upside_down_rotator(self, page: fitz.Page, multiplier: float = 3.0) -> tuple[fitz.Page, np.ndarray, int]:
        """ Determine if the page is upside down """
        # Initial image conversion
        pix = page.get_pixmap(matrix=fitz.Matrix(multiplier, multiplier))
        image = self.pix_to_cv2_image(pix)
        current_rotation = page.rotation
        
        # Check and correct text orientation
        text_orientation = self._get_text_orientation(image, page.number)
        if text_orientation == self.UPSIDE_DOWN_ANGLE:
            target_rotation = (current_rotation + self.UPSIDE_DOWN_ANGLE) % 360
            page.set_rotation(target_rotation)
            image = cv2.rotate(image, cv2.ROTATE_180)
            print(f"Page {page.number + 1} is upside down, rotating to correct orientation")
        else:
            print(f"Page {page.number + 1} is in correct orientation, no rotation needed")
        return page, image, self.UPSIDE_DOWN_ANGLE if text_orientation == self.UPSIDE_DOWN_ANGLE else 0