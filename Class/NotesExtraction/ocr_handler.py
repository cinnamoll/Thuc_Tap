import pytesseract
import numpy as np
import cv2
from Class.TableExtractor import Word

class OCRHandler:
    @staticmethod
    def ocr_page_text(pil_img, lang="eng"):
        try:
            gray = np.array(pil_img.convert("L"))
            denoised = cv2.fastNlMeansDenoising(gray, h=10)
            data = pytesseract.image_to_data(denoised, lang=lang, output_type=pytesseract.Output.DICT)
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
            if conf != -1 and conf < 15:
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
                    lines.append({"top": cur_top, "bottom": max(x["y1"] for x in cur),
                                  "words": cur})
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
    def ocr_tokens_to_words(img, page_w, page_h, lang="eng", min_conf=20):
        gray = np.array(img.convert("L"))
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        data =  pytesseract.image_to_data(denoised, lang=lang, output_type=pytesseract.Output.DICT)
        img_w, img_h = img.size
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
            if conf != -1 and conf < min_conf:
                continue
            x = data["left"][j] * sx
            y = data["top"][j] * sy
            w = data["width"][j] * sx
            h = data["height"][j] * sy
            words.append(Word(text, x, x + w, y, y + h))
        return words