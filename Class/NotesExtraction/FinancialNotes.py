import pdfplumber
from pdf2image import convert_from_path
import numpy as np
import cv2
from Class.NotesExtraction.ocr_handler import OCRHandler

from Class.ReportContent.FinancialNotesReport import FinancialNotesReport
from Class.NotesExtraction.section_extractor import SectionExtractor
from Class.NotesExtraction.heading_mapper import HeadingMapper
from Class.NotesExtraction.notes_table_extractor import NotesTableExtractor

class FinancialNotesExtractor:
    def __init__(self):
        self.section_extractor = SectionExtractor()
        self.heading_mapper = HeadingMapper()
        self.table_extractor = NotesTableExtractor()

    def extract_notes_structured(self, file_path: str, page_start: int, page_end: int, year: int):
        full_text = self.extract_text_from_pdf(file_path, first_page=page_start+1, last_page=page_end+1)
        raw_notes = self.section_extractor.extract_all_to_format(full_text)

        notes = FinancialNotesReport(page_start=page_start, page_end=page_end, year=year)
        notes.raw_data = raw_notes

        KEY_MAP = [
            ("dac_diem_hoat_dong", lambda k: "đặc điểm hoạt động" in k),
            ("ky_ke_toan_tien_te", lambda k: "kỳ kế toán" in k),
            ("chuan_muc_che_do", lambda k: "chuẩn mực" in k),
            ("chinh_sach_hoat_dong_lien_tuc", lambda k: "hoạt động liên tục" in k and "không" not in k),
            ("chinh_sach_khong_lien_tuc", lambda k: "không đáp ứng" in k or "không liên tục" in k),
            ("bo_sung_bang_can_doi", lambda k: "bảng cân đối" in k),
            ("bo_sung_ket_qua_kd", lambda k: "kết quả" in k),
            ("bo_sung_luu_chuyen_tien_te", lambda k: "lưu chuyển tiền tệ" in k),
            ("nhung_thong_tin_khac", lambda k: "thông tin khác" in k or "những thông tin" in k),
        ]

        for section in raw_notes:
            if not isinstance(section, dict):
                continue
            for key, value in section.items():
                kl = key.lower()
                for field_name, matcher in KEY_MAP:
                    if matcher(kl):
                        if field_name in ("dac_diem_hoat_dong", "bo_sung_bang_can_doi", "nhung_thong_tin_khac"):
                            setattr(notes, field_name, value if isinstance(value, dict) else {"noi_dung": str(value)})
                        else:
                            setattr(notes, field_name, str(value) if value else None)
                        break

        text_sections = self.section_extractor.slice_by_numeric_sections(full_text)
        tables, page_headings = self.table_extractor.extract_tables_from_pages(file_path, page_start, page_end)

        if not tables:
            merged_tables: dict = {}
        else:
            merged_tables = dict(tables)

        for heading, text in text_sections.items():
            if not text:
                continue
            if heading in merged_tables:
                continue
            if not self.heading_mapper.is_valid_section_key(heading):
                continue
            merged_tables[heading] = [{"text": text}]

        if merged_tables:
            notes.tables = merged_tables

        for heading, rows in merged_tables.items():
            if not rows or not isinstance(rows, list):
                continue
            if isinstance(rows[0], dict) and set(rows[0].keys()) == {"text"}:
                continue
            
            m = self.heading_mapper.SECTION_NO.match(heading)
            title_part = m.group(2).strip() if m else heading
            section_field = self.heading_mapper.map_heading_to_section(title_part)
            renamed_rows = self.table_extractor.rename_notes_columns(rows, heading)

            current = getattr(notes, section_field, None)
            if current is None:
                current = {}
            if not isinstance(current, dict):
                current = {"noi_dung": str(current)}
            if heading in current and isinstance(current[heading], list):
                current[heading].extend(renamed_rows)
            else:
                current[heading] = renamed_rows
            setattr(notes, section_field, current)

        return notes

    def extract_text_from_pdf(self, file_path, first_page=None, last_page=None):
        text_parts = []
        try:
            with pdfplumber.open(file_path) as pdf:
                start_page = (first_page - 1) if first_page else 0
                end_page = last_page if last_page else len(pdf.pages)
                end_page = min(end_page, len(pdf.pages))

                for page_num in range(start_page, end_page):
                    page = pdf.pages[page_num]
                    page_text = page.extract_text(x_tolerance=30, layout=True)
                    if page_text and page_text.strip():
                        text_parts.append(page_text)
                    else:
                        try:
                            pil_img = convert_from_path(file_path, first_page=page_num + 1, last_page=page_num + 1, dpi=300, fmt='jpeg')[0]
                            img = np.array(pil_img)
                            if len(img.shape) == 3:
                                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                            else:
                                gray = img
                            ocr_text = OCRHandler.ocr_page_text(pil_img, lang="eng")
                            if ocr_text and ocr_text.strip():
                                text_parts.append(ocr_text)
                        except Exception as e:
                            pass
        except Exception as e:
            try:
                images = convert_from_path(file_path, first_page=first_page, last_page=last_page, dpi=300, fmt='jpeg')
                for img in images:
                    img_np = np.array(img)
                    if len(img_np.shape) == 3:
                        gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
                    else:
                        gray = img_np
                    ocr_text = OCRHandler.ocr_page_text(img, lang="eng")
                    if ocr_text and ocr_text.strip():
                        text_parts.append(ocr_text)
            except Exception:
                pass
        return "\n\n".join(text_parts)