from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image

from src.ocr.base import OCRDocument, OCREngine, OCRPage

logger = logging.getLogger(__name__)

# Maps our internal ISO-ish codes to Tesseract's language pack names.
_LANG_MAP = {
    "eng": "eng", "fas": "fas", "ara": "ara", "fra": "fra", "deu": "deu",
    "ita": "ita", "spa": "spa", "por": "por", "rus": "rus", "zho": "chi_sim",
    "jpn": "jpn", "kor": "kor", "tur": "tur", "hin": "hin", "urd": "urd",
}


def _preprocess(image: np.ndarray) -> np.ndarray:
    """Deskew + denoise + adaptive-threshold. Handwriting benefits most
    from denoising; printed text benefits most from thresholding — we
    apply both since we don't know in advance which we're given."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
    )
    return thresh


def _ocr_pil_image(image: Image.Image, lang_str: str) -> OCRPage:
    arr = np.array(image.convert("RGB"))[:, :, ::-1]  # RGB -> BGR for cv2
    processed = _preprocess(arr)
    data = pytesseract.image_to_data(
        processed, lang=lang_str, output_type=pytesseract.Output.DICT
    )
    words, confidences = [], []
    for text, conf in zip(data["text"], data["conf"]):
        if text.strip():
            words.append(text)
            try:
                c = float(conf)
            except ValueError:
                continue
            if c >= 0:
                confidences.append(c)
    mean_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
    return OCRPage(text=" ".join(words), mean_confidence=mean_conf)


class TesseractOCREngine(OCREngine):
    def extract(self, file_path: Path, languages: list[str]) -> OCRDocument:
        lang_str = "+".join(_LANG_MAP.get(l, l) for l in languages) or "eng"
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(file_path, lang_str)
        if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
            image = Image.open(file_path)
            return OCRDocument(pages=[_ocr_pil_image(image, lang_str)])

        raise ValueError(f"TesseractOCREngine cannot handle file type: {suffix}")

    def _extract_pdf(self, file_path: Path, lang_str: str) -> OCRDocument:
        from pdf2image import convert_from_path

        try:
            images = convert_from_path(str(file_path), dpi=300)
        except Exception as exc:  # poppler missing, corrupt file, etc.
            logger.error("Failed to rasterize PDF %s: %s", file_path, exc)
            return OCRDocument(pages=[])
        pages = [_ocr_pil_image(img, lang_str) for img in images]
        return OCRDocument(pages=pages)
