import re

from Class.TableExtractor import Word

# Lazy: pytesseract / cv2 / numpy chỉ cần khi thực sự chạy nhánh OCR fallback.
# Dataset hiện tại có text layer đầy đủ nên nhánh này không được gọi tới.
try:  # pragma: no cover - phụ thuộc tuỳ chọn
    import cv2
    import numpy as np
    import pytesseract
except ImportError:  # OCR là tuỳ chọn, không bắt buộc cho pipeline
    cv2 = None
    np = None
    pytesseract = None

class OCRHandler:
    @staticmethod
    def filter_low_confidence_tokens(conf: int, min_conf: int, text: str) -> bool:
        if conf == -1:
            return False
        if conf >= min_conf:
            return False
        if re.search(r"\d", text):
            return False
        return True

    @staticmethod
    def ocr_page_text(pil_img, lang="eng", page_num=None):
        if pytesseract is None:
            return ""
        try:
            if hasattr(pil_img, "convert"):
                gray = np.array(pil_img.convert("L"))
            elif isinstance(pil_img, np.ndarray):
                gray = cv2.cvtColor(pil_img, cv2.COLOR_BGR2GRAY) if len(pil_img.shape) == 3 else pil_img
            else:
                return ""

            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            data = pytesseract.image_to_data(thresh, lang=lang, output_type=pytesseract.Output.DICT)
        except Exception:
            return ""
        
        tokens = []
        for j in range(len(data["text"])):
            text = (data["text"][j] or "").strip()
            if not text:
                continue
            try:
                conf = int(data["conf"][j])
            except (TypeError, ValueError):
                conf = -1
            if OCRHandler.filter_low_confidence_tokens(conf, 15, text):
                continue
            left, top = data["left"][j], data["top"][j]
            width, height = data["width"][j], data["height"][j]
            tokens.append({"text": text, "x0": left, "y0": top, "x1": left + width, "y1": top + height})
        if not tokens:
            return ""
        tokens.sort(key=lambda t: (t["y0"], t["x0"]))
        heights = sorted(t["y1"] - t["y0"] for t in tokens)
        med_h = heights[len(heights) // 2] or 10.0
        tol = max(4.0, med_h * 0.6)
        lines = []
        cur = []
        cur_top = 0.0
        for t in tokens:
            if cur and t["y0"] - cur_top <= tol:
                cur.append(t)
            else:
                if cur:
                    cur.sort(key=lambda x: x["x0"])
                    lines.append({"top": cur_top, "bottom": max(x["y1"] for x in cur), "words": cur})
                cur = [t]
                cur_top = t["y0"]
        if cur:
            cur.sort(key=lambda x: x["x0"])
            lines.append({"top": cur_top, "bottom": max(x["y1"] for x in cur),
                          "words": cur})
        out_lines = []
        for i, line in enumerate(lines):
            if i and (line["top"] - lines[i - 1]["bottom"]) > 1.5 * med_h:
                out_lines.append("")
            out_lines.append(" ".join(w["text"] for w in line["words"]))
        return "\n".join(out_lines)

    @staticmethod
    def ocr_tokens_to_words(img, page_w, page_h, lang="eng", min_conf=20, page_num=None):
        if pytesseract is None:
            return []
        try:
            if hasattr(img, "convert"):
                gray = np.array(img.convert("L"))
                img_w, img_h = img.size
            elif isinstance(img, np.ndarray):
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
                img_h, img_w = img.shape[:2]
            else:
                return []

            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            data = pytesseract.image_to_data(thresh, lang=lang, output_type=pytesseract.Output.DICT)
        except Exception:
            return []

        sx, sy = page_w / float(img_w), page_h / float(img_h)
        words = []
        for j in range(len(data["text"])):
            text = (data["text"][j] or "").strip()
            if not text:
                continue
            try:
                conf = int(data["conf"][j])
            except (TypeError, ValueError):
                conf = -1
            if OCRHandler.filter_low_confidence_tokens(conf, min_conf, text):
                continue
            x = data["left"][j] * sx
            y = data["top"][j] * sy
            w = data["width"][j] * sx
            h = data["height"][j] * sy
            words.append(Word(text, x, x + w, y, y + h))
        return words