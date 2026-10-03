---
entity_id: "0102381001"
company_name: "CMISTONE VIETNAM JOINT STOCK COMPANY"
symbol: null
period_key: "2024Q4"
scope: "separate"
currency_unit: "VND"
circular: "200"
lang: "vi"
batch_id: "batch_20261003_230638_d76a12"
source_files: ["/home/cinnamoll/Code/BT_Thuc_Tap/dataset/000000014485621_EN_FinancialStatements_Q4_2024.pdf"]
generated_at: null
report_version: 1
review_status: "approved"
prev_period_file: null
next_period_file: null
data_quality_flags:
  unit_mismatch_suspected: false
  missing_prior_period: true
  missing_financial_notes: false
  accounting_checks_passed: true
---

# BÁO CÁO PHÂN TÍCH TÀI CHÍNH (RAG OPTIMIZED) — DOANH NGHIỆP

## 0. Khối dữ liệu cấu trúc (Structured Data JSON)

```json
{
  "balance_sheet": {
    "total_assets": 167400624941.0,
    "short_term_assets": 94113398194.0,
    "long_term_assets": 73287226747.0,
    "total_liabilities": 239506246763.0,
    "equity": -72105621822.0,
    "unit": "ty_vnd"
  },
  "income_statement": {
    "revenue": null,
    "gross_profit": null,
    "net_profit": -3939172206.0,
    "unit": "ty_vnd"
  },
  "ratios": {
    "roe": null,
    "roa": null,
    "debt_to_equity": null,
    "net_margin": null,
    "unit": "percent_or_ratio"
  },
  "growth": {
    "qoq": null,
    "yoy": null,
    "cagr": null,
    "reason_null": "no_prior_period_data"
  }
}
```

## 1. Phân tích Tường thuật Quản trị (MD&A)

# BÁO CÁO PHÂN TÍCH QUẢN TRỊ (MD&A) – KỲ 2024Q4  
**Phạm vi báo cáo:** Separate  
**Đơn vị trình bày:** tỷ VND (đã quy đổi từ dữ liệu gốc; các giá trị rất nhỏ ghi kèm VND để tránh làm tròn về 0)

> **Lưu ý về dữ liệu:** Không có số liệu kỳ trước, vì vậy toàn bộ phân tích dưới đây là phân tích tĩnh cho riêng 2024Q4. Không thể tính toán/thuyết minh biến động QoQ, YoY hoặc CAGR. Mọi nhận định về thay đổi so với kỳ trước đều không thực hiện được.

---

## 1. TÓM TẮT ĐIỀU HÀNH

Doanh nghiệp đang ở trạng thái tài chính **đặc biệt nghiêm trọng**:

- **Không có doanh thu bán hàng/thuần từ hoạt động kinh doanh**; doanh thu tài chính chỉ **27.579 VND** (≈0,0000276 tỷ VND).
- **Lỗ sau thuế 3,939 tỷ VND**, chủ yếu do chi phí tài chính **2,426 tỷ VND** và chi phí khác **1,513 tỷ VND**.
- **Vốn chủ sở hữu âm 72,106 tỷ VND**; lỗ lũy kế **236,165 tỷ VND**, lớn hơn vốn điều lệ 160 tỷ VND.
- **Nợ phải trả 239,506 tỷ VND**, lớn hơn tổng tài sản 167,401 tỷ VND. Tỷ lệ nợ phải trả/tổng tài sản = **143,1%**.
- **Thanh khoản ngắn hạn yếu:** tài sản ngắn hạn 94,113 tỷ VND < nợ ngắn hạn 127,962 tỷ VND; vốn lưu động thuần âm **33,849 tỷ VND**.
- **Tiền mặt rất thấp:** chỉ 0,073 tỷ VND (≈73,4 triệu VND).

Đây là các dấu hiệu điển hình của **rủi ro hoạt động liên tục (going concern)** và **mất khả năng thanh toán** nếu không có phương án tái cấu trúc tài chính khẩn cấp.

---

## 2. PHÂN TÍCH TÀI SẢN – NGUỒN VỐN

### 2.1. Cơ cấu tài sản

| Chỉ tiêu | 2024Q4 (tỷ VND) | So với kỳ trước | Ghi chú |
|---|---:|---|---|
| Tổng tài sản | 167,401 | Không có dữ liệu | 100% |
| Tài sản ngắn hạn | 94,113 | Không có dữ liệu | 56,2% tổng tài sản |
| Tiền | 0,073 | Không có dữ liệu | Rất thấp |
| Phải thu ngắn hạn | 91,687 | Không có dữ liệu | Chiếm 97,4% tài sản ngắn hạn |
| – Dự phòng phải thu ngắn hạn | -27,577 | Không có dữ liệu | Rủi ro thu hồi cao |
| Hàng tồn kho thuần | 0,768 | Không có dữ liệu | Gộp 8,747; dự phòng -7,979 |
| Tài sản dài hạn | 73,287 | Không có dữ liệu | 43,8% tổng tài sản |
| Đầu tư vào công ty con | 8,000 | Không có dữ liệu | Đã trích lập dự phòng toàn bộ -8,000 |
| Chi phí trả trước dài hạn | 8,954 | Không có dữ liệu | |

**Nhận xét:**  
Tài sản ngắn hạn chủ yếu là **các khoản phải thu**. Trong đó, khoản phải thu khác ngắn hạn gộp lên tới **104,872 tỷ VND**, đã trích lập dự phòng **27,577 tỷ VND**. Đây là điểm rủi ro trọng yếu: chất lượng khoản phải thu thấp, khả năng thu hồi không chắc chắn. Hàng tồn kho gần như đã trích lập dự phòng toàn bộ, phản ánh tài sản kém thanh khoản. Đầu tư vào công ty con 8 tỷ VND đã bị trích lập dự phòng 100%, cho thấy suy giảm giá trị nghiêm trọng.

### 2.2. Cơ cấu nguồn vốn

| Chỉ tiêu | 2024Q4 (tỷ VND) | So với kỳ trước | Ghi chú |
|---|---:|---|---|
| Nợ phải trả | 239,506 | Không có dữ liệu | 143,1% tổng tài sản |
| Nợ ngắn hạn | 127,962 | Không có dữ liệu | 53,4% nợ phải trả |
| Nợ dài hạn | 111,544 | Không có dữ liệu | 46,6% nợ phải trả |
| Vay và nợ thuê tài chính ngắn hạn | 33,019 | Không có dữ liệu | |
| Vay và nợ thuê tài chính dài hạn | 111,544 | Không có dữ liệu | |
| Tổng vay chịu lãi | 144,563 | Không có dữ liệu | 86,4% tổng tài sản |
| Phải trả người bán | 6,814 | Không có dữ liệu | |
| Thuế phải nộp | 15,137 | Không có dữ liệu | |
| Chi phí phải trả ngắn hạn | 61,912 | Không có dữ liệu | Gây áp lực thanh khoản |
| Vốn chủ sở hữu | -72,106 | Không có dữ liệu | Âm |
| Vốn điều lệ | 160,000 | Không có dữ liệu | |
| Lỗ lũy kế | -236,165 | Không có dữ liệu | Bằng 147,6% vốn điều lệ |

**Nhận xét:**  
Nợ phải trả đã vượt tổng tài sản. Vốn chủ sở hữu âm cho thấy **toàn bộ vốn điều lệ và các quỹ đã bị lỗ lũy kế ăn mòn**, phần thiếu hụt phải bù đắp bằng nợ. Cơ cấu vốn mất cân đối nghiêm trọng, phụ thuộc lớn vào vay nợ. Áp lực trả nợ ngắn hạn lớn trong khi tiền mặt gần như không đáng kể.

---

## 3. KẾT QUẢ KINH DOANH

| Chỉ tiêu | 2024Q4 (tỷ VND) | So với kỳ trước | Ghi chú |
|---|---:|---|---|
| Doanh thu tài chính | 0,0000276 | Không có dữ liệu | 27.579 VND |
| Chi phí tài chính | 2,426 | Không có dữ liệu | Chủ yếu lãi vay/chi phí tài chính |
| Chi phí bán hàng | 0,000187 | Không có dữ liệu | 187.000 VND |
| Lợi nhuận thuần kinh doanh | -2,426 | Không có dữ liệu | Lỗ hoạt động |
| Chi phí khác | 1,513 | Không có dữ liệu | |
| Lợi nhuận khác | -1,513 | Không có dữ liệu | |
| Lợi nhuận trước thuế | -3,939 | Không có dữ liệu | |
| Lợi nhuận sau thuế | -3,939 | Không có dữ liệu | Lỗ ròng |

**Nhận xét:**  
Doanh nghiệp **không có doanh thu bán hàng**, chỉ có doanh thu tài chính không đáng kể. Chi phí tài chính 2,426 tỷ VND là nguyên nhân chính gây lỗ hoạt động. Chi phí khác 1,513 tỷ VND làm gia tăng lỗ ròng lên 3,939 tỷ VND. Không có dấu hiệu cải thiện từ hoạt động kinh doanh cốt lõi trong kỳ này.

---

## 4. DÒNG TIỀN

| Chỉ tiêu | 2024Q4 | So với kỳ trước | Ghi chú |
|---|---:|---|---|
| Dòng tiền thuần từ HĐKD (CFO) | -0,000187 tỷ VND | Không có dữ liệu | -187.000 VND |
| Dòng tiền thuần từ HĐĐT (CFI) | +0,0000276 tỷ VND | Không có dữ liệu | 27.579 VND |
| Dòng tiền thuần từ HĐTC (CFF) | 0 | Không có dữ liệu | Không phát sinh |
| Lưu chuyển tiền thuần trong kỳ | -0,000159 tỷ VND | Không có dữ liệu | -159.421 VND |
| Tiền đầu kỳ | 0,073558 | Không có dữ liệu | 73.558.496 VND |
| Tiền cuối kỳ | 0,073399 | Không có dữ liệu | 73.399.075 VND |

**Nhận xét:**  
Dòng tiền từ hoạt động kinh doanh gần như bằng 0 và âm nhẹ. Không có dòng tiền từ bán hàng, không vay/trả nợ trong kỳ. Tiền mặt giảm nhẹ nhưng ở mức cực thấp. Doanh nghiệp không tạo được tiền từ hoạt động cốt lõi, trong khi nghĩa vụ nợ và chi phí phải trả lớn.

---

## 5. CÁC CHỈ SỐ TÀI CHÍNH TRỌNG YẾU

| Chỉ số | 2024Q4 | So với kỳ trước | Diễn giải |
|---|---:|---|---|
| ROE | 5,46% | Không có dữ liệu | **Dương giả tạo** do vốn chủ sở hữu âm; không phản ánh hiệu quả |
| ROA | -2,35% | Không có dữ liệu | Lỗ trên tổng tài sản |
| Debt/Equity | -3,32 | Không có dữ liệu | Âm do vốn chủ sở hữu âm; nên dùng Nợ/Tài sản = 143,1% |
| Net Margin | 0,0% | Không có dữ liệu | Không có doanh thu thuần nên không có ý nghĩa |
| Current ratio | 0,735 | Không có dữ liệu | Tài sản ngắn hạn/nợ ngắn hạn < 1 |
| Quick ratio | 0,729 | Không có dữ liệu | Loại hàng tồn kho vẫn < 1 |
| Cash ratio | 0,00057 | Không có dữ liệu | Tiền/nợ ngắn hạn gần bằng 0 |
| Vốn lưu động thuần | -33,849 tỷ VND | Không có dữ liệu | Thiếu hụt thanh khoản ngắn hạn |
| Nợ phải trả/Tổng tài sản | 143,1% | Không có dữ liệu | Nợ vượt tài sản |
| Vốn chủ sở hữu/Tổng tài sản | -43,1% | Không có dữ liệu | Vốn chủ sở hữu âm |
| Lỗ lũy kế/Vốn điều lệ | 147,6% | Không có dữ liệu | Vốn điều lệ đã bị lỗ lũy kế vượt qua |

**Cảnh báo kế toán:**  
- **ROE dương 5,46%** là hiện tượng do mẫu số âm, không phải dấu hiệu sinh lời.  
- **Debt/Equity âm -3,32** không dùng để đánh giá đòn bẩy thông thường; cần dùng tỷ lệ Nợ/Tài sản.  
- **Net Margin 0,0%** không có ý nghĩa vì doanh nghiệp không có doanh thu thuần; nếu tính trên doanh thu tài chính, biên lợi nhuận âm cực lớn.

---

## 6. CẢNH BÁO VÀ RỦI RO TRỌNG YẾU

1. **Hoạt động liên tục:** Vốn chủ sở hữu âm, lỗ lũy kế lớn hơn vốn điều lệ, nợ phải trả vượt tài sản, tiền mặt cạn kiệt. Đây là các chỉ dấu điển hình của nghi ngờ hoạt động liên tục.
2. **Rủi ro thanh khoản:** Nợ ngắn hạn 127,962 tỷ VND trong khi tài sản ngắn hạn 94,113 tỷ VND; tiền mặt chỉ 0,073 tỷ VND. Khả năng thanh toán ngắn hạn rất yếu.
3. **Rủi ro thu hồi công nợ:** Phải thu khác ngắn hạn gộp 104,872 tỷ VND, dự phòng 27,577 tỷ VND. Cần đánh giá khả năng thu hồi và bên liên quan.
4. **Hàng tồn kho:** Đã trích lập dự phòng 7,979/8,747 tỷ VND, tức gần như toàn bộ. Chất lượng tài sản thấp.
5. **Đầu tư tài chính:** Đầu tư vào công ty con 8 tỷ VND đã trích lập dự phòng 100%, phản ánh suy giảm giá trị.
6. **Chi phí tài chính lớn:** 2,426 tỷ VND trong khi doanh thu tài chính không đáng kể. Gánh nặng lãi vay/chi phí tài chính đang bào mòn vốn.
7. **Không có dòng tiền từ kinh doanh:** CFO âm nhẹ, không có doanh thu bán hàng. Hoạt động hiện tại không tạo tiền.
8. **Phạm vi separate:** Báo cáo riêng không hợp nhất công ty con; tình hình thực tế của tập đoàn có thể khác. Cần xem xét thuyết minh về công ty con, bên liên quan và các cam kết nợ.

---

## 7. KHUYẾN NGHỊ NGẮN GỌN

1. **Ưu tiên sống còn – tái cấu trúc nợ khẩn cấp:** Đàm phán gia hạn nợ, giảm lãi, chuyển nợ thành vốn, hoặc tìm nguồn tài trợ mới. Nếu không, rủi ro mất khả năng trả nợ là hiện hữu.
2. **Tăng vốn:** Yêu cầu cổ đông góp thêm vốn, phát hành cổ phiếu, hoặc bán tài sản không sinh lời để bù đắp vốn chủ sở hữu âm.
3. **Thu hồi công nợ:** Tập trung thu hồi các khoản phải thu khác ngắn hạn; đánh giá lại dự phòng và xử lý nợ khó đòi.
4. **Cắt giảm chi phí:** Kiểm soát chặt chi phí tài chính, chi phí khác; đàm phán lãi suất.
5. **Xử lý tài sản kém hiệu quả:** Thanh lý hàng tồn kho, thu hồi VAT, xử lý đầu tư công ty con.
6. **Xây dựng phương án kinh doanh có doanh thu:** Hiện doanh nghiệp gần như không có doanh thu; cần kế hoạch phục hồi hoặc phương án giải thể/phá sản theo quy định nếu không khả thi.
7. **Công bố thông tin và kiểm toán:** Giải trình rõ vốn chủ sở hữu âm, lỗ lũy kế, khả năng hoạt động liên tục, các giao dịch bên liên quan và khả năng thu hồi tài sản.
8. **Quản trị dòng tiền ngắn hạn:** Lập kế hoạch dòng tiền 13 tuần, giám sát hàng tuần; ưu tiên thanh toán các nghĩa vụ thiết yếu và đàm phán giãn nợ.

---

**Kết luận:**  
2024Q4 cho thấy doanh nghiệp đang mất cân đối tài chính nghiêm trọng: vốn chủ sở hữu âm, nợ vượt tài sản, không có doanh thu, lỗ tiếp diễn và thanh khoản cạn kiệt. Các chỉ số ROE dương và Net Margin 0,0% không phản ánh đúng bản chất do mẫu số âm/không có doanh thu. Ưu tiên hàng đầu là tái cấu trúc nợ – vốn và đánh giá khả năng hoạt động liên tục.

## 2. Bảng chỉ tiêu chính theo kỳ

| Chỉ tiêu | 2024Q4 |
|---|---|
| Tổng tài sản | 167.4 |
| Tài sản ngắn hạn | 94.1 |
| Tài sản dài hạn | 73.3 |
| Nợ phải trả | 239.5 |
| Vốn chủ sở hữu | -72.1 |
| Tổng nguồn vốn | 167.4 |
| Lợi nhuận trước thuế | -3.9 |
| Lợi nhuận sau thuế | -3.9 |
| Tiền cuối kỳ | 0.1 |

## 3. Chỉ số tài chính

| Chỉ số | 2024Q4 |
|---|---|
| ROE | 5.46 |
| ROA | -2.35 |
| Debt_to_Equity | -3.32 |
| Net_Margin | 0.00 |

## 4. Tăng trưởng (QoQ / YoY / CAGR)

```json
{
  "growth": null,
  "reason": "no_prior_period_data"
}
```

## 5. Kiểm định đẳng thức kế toán (deterministic)

Đã qua kiểm định: Không ghi nhận bất thường kế toán hoặc vi phạm đẳng thức.

## 6. Biểu đồ

_Biểu đồ các chỉ số mục 1.1–1.5 (vẽ trên toàn bộ khoảng thời gian) được lưu tại `example_output/batch_20261003_230638_d76a12/charts/`:_

- Mục 1.1 — Quy mô và cơ cấu tài sản: `example_output/batch_20261003_230638_d76a12/charts/1.1/chart_1_1_asset_structure.png`
- Mục 1.2 — Cơ cấu nguồn vốn: `example_output/batch_20261003_230638_d76a12/charts/1.2/chart_1_2_capital_structure.png`
- Mục 1.3 — Thanh khoản và khả năng trả nợ: `example_output/batch_20261003_230638_d76a12/charts/1.3/chart_1_3_liquidity.png`
- Mục 1.4 — Kết quả kinh doanh: `example_output/batch_20261003_230638_d76a12/charts/1.4/chart_1_4_profitability.png`
- Mục 1.5 — Dòng tiền: `example_output/batch_20261003_230638_d76a12/charts/1.5/chart_1_5_cashflow.png`

## 8. Đánh giá rủi ro tài chính tổng hợp (LLM-generated)

# BÁO CÁO PHÂN TÍCH QUẢN TRỊ (MD&A) – KỲ 2024Q4  
**Phạm vi báo cáo:** Separate  
**Đơn vị trình bày:** tỷ VND (đã quy đổi từ dữ liệu gốc; các giá trị rất nhỏ ghi kèm VND để tránh làm tròn về 0)

> **Lưu ý về dữ liệu:** Không có số liệu kỳ trước, vì vậy toàn bộ phân tích dưới đây là phân tích tĩnh cho riêng 2024Q4. Không thể tính toán/thuyết minh biến động QoQ, YoY hoặc CAGR. Mọi nhận định về thay đổi so với kỳ trước đều không thực hiện được.

---

## 1. TÓM TẮT ĐIỀU HÀNH

Doanh nghiệp đang ở trạng thái tài chính **đặc biệt nghiêm trọng**:

- **Không có doanh thu bán hàng/thuần từ hoạt động kinh doanh**; doanh thu tài chính chỉ **27.579 VND** (≈0,0000276 tỷ VND).
- **Lỗ sau thuế 3,939 tỷ VND**, chủ yếu do chi phí tài chính **2,426 tỷ VND** và chi phí khác **1,513 tỷ VND**.
- **Vốn chủ sở hữu âm 72,106 tỷ VND**; lỗ lũy kế **236,165 tỷ VND**, lớn hơn vốn điều lệ 160 tỷ VND.
- **Nợ phải trả 239,506 tỷ VND**, lớn hơn tổng tài sản 167,401 tỷ VND. Tỷ lệ nợ phải trả/tổng tài sản = **143,1%**.
- **Thanh khoản ngắn hạn yếu:** tài sản ngắn hạn 94,113 tỷ VND < nợ ngắn hạn 127,962 tỷ VND; vốn lưu động thuần âm **33,849 tỷ VND**.
- **Tiền mặt rất thấp:** chỉ 0,073 tỷ VND (≈73,4 triệu VND).

Đây là các dấu hiệu điển hình của **rủi ro hoạt động liên tục (going concern)** và **mất khả năng thanh toán** nếu không có phương án tái cấu trúc tài chính khẩn cấp.

---

## 2. PHÂN TÍCH TÀI SẢN – NGUỒN VỐN

### 2.1. Cơ cấu tài sản

| Chỉ tiêu | 2024Q4 (tỷ VND) | So với kỳ trước | Ghi chú |
|---|---:|---|---|
| Tổng tài sản | 167,401 | Không có dữ liệu | 100% |
| Tài sản ngắn hạn | 94,113 | Không có dữ liệu | 56,2% tổng tài sản |
| Tiền | 0,073 | Không có dữ liệu | Rất thấp |
| Phải thu ngắn hạn | 91,687 | Không có dữ liệu | Chiếm 97,4% tài sản ngắn hạn |
| – Dự phòng phải thu ngắn hạn | -27,577 | Không có dữ liệu | Rủi ro thu hồi cao |
| Hàng tồn kho thuần | 0,768 | Không có dữ liệu | Gộp 8,747; dự phòng -7,979 |
| Tài sản dài hạn | 73,287 | Không có dữ liệu | 43,8% tổng tài sản |
| Đầu tư vào công ty con | 8,000 | Không có dữ liệu | Đã trích lập dự phòng toàn bộ -8,000 |
| Chi phí trả trước dài hạn | 8,954 | Không có dữ liệu | |

**Nhận xét:**  
Tài sản ngắn hạn chủ yếu là **các khoản phải thu**. Trong đó, khoản phải thu khác ngắn hạn gộp lên tới **104,872 tỷ VND**, đã trích lập dự phòng **27,577 tỷ VND**. Đây là điểm rủi ro trọng yếu: chất lượng khoản phải thu thấp, khả năng thu hồi không chắc chắn. Hàng tồn kho gần như đã trích lập dự phòng toàn bộ, phản ánh tài sản kém thanh khoản. Đầu tư vào công ty con 8 tỷ VND đã bị trích lập dự phòng 100%, cho thấy suy giảm giá trị nghiêm trọng.

### 2.2. Cơ cấu nguồn vốn

| Chỉ tiêu | 2024Q4 (tỷ VND) | So với kỳ trước | Ghi chú |
|---|---:|---|---|
| Nợ phải trả | 239,506 | Không có dữ liệu | 143,1% tổng tài sản |
| Nợ ngắn hạn | 127,962 | Không có dữ liệu | 53,4% nợ phải trả |
| Nợ dài hạn | 111,544 | Không có dữ liệu | 46,6% nợ phải trả |
| Vay và nợ thuê tài chính ngắn hạn | 33,019 | Không có dữ liệu | |
| Vay và nợ thuê tài chính dài hạn | 111,544 | Không có dữ liệu | |
| Tổng vay chịu lãi | 144,563 | Không có dữ liệu | 86,4% tổng tài sản |
| Phải trả người bán | 6,814 | Không có dữ liệu | |
| Thuế phải nộp | 15,137 | Không có dữ liệu | |
| Chi phí phải trả ngắn hạn | 61,912 | Không có dữ liệu | Gây áp lực thanh khoản |
| Vốn chủ sở hữu | -72,106 | Không có dữ liệu | Âm |
| Vốn điều lệ | 160,000 | Không có dữ liệu | |
| Lỗ lũy kế | -236,165 | Không có dữ liệu | Bằng 147,6% vốn điều lệ |

**Nhận xét:**  
Nợ phải trả đã vượt tổng tài sản. Vốn chủ sở hữu âm cho thấy **toàn bộ vốn điều lệ và các quỹ đã bị lỗ lũy kế ăn mòn**, phần thiếu hụt phải bù đắp bằng nợ. Cơ cấu vốn mất cân đối nghiêm trọng, phụ thuộc lớn vào vay nợ. Áp lực trả nợ ngắn hạn lớn trong khi tiền mặt gần như không đáng kể.

---

## 3. KẾT QUẢ KINH DOANH

| Chỉ tiêu | 2024Q4 (tỷ VND) | So với kỳ trước | Ghi chú |
|---|---:|---|---|
| Doanh thu tài chính | 0,0000276 | Không có dữ liệu | 27.579 VND |
| Chi phí tài chính | 2,426 | Không có dữ liệu | Chủ yếu lãi vay/chi phí tài chính |
| Chi phí bán hàng | 0,000187 | Không có dữ liệu | 187.000 VND |
| Lợi nhuận thuần kinh doanh | -2,426 | Không có dữ liệu | Lỗ hoạt động |
| Chi phí khác | 1,513 | Không có dữ liệu | |
| Lợi nhuận khác | -1,513 | Không có dữ liệu | |
| Lợi nhuận trước thuế | -3,939 | Không có dữ liệu | |
| Lợi nhuận sau thuế | -3,939 | Không có dữ liệu | Lỗ ròng |

**Nhận xét:**  
Doanh nghiệp **không có doanh thu bán hàng**, chỉ có doanh thu tài chính không đáng kể. Chi phí tài chính 2,426 tỷ VND là nguyên nhân chính gây lỗ hoạt động. Chi phí khác 1,513 tỷ VND làm gia tăng lỗ ròng lên 3,939 tỷ VND. Không có dấu hiệu cải thiện từ hoạt động kinh doanh cốt lõi trong kỳ này.

---

## 4. DÒNG TIỀN

| Chỉ tiêu | 2024Q4 | So với kỳ trước | Ghi chú |
|---|---:|---|---|
| Dòng tiền thuần từ HĐKD (CFO) | -0,000187 tỷ VND | Không có dữ liệu | -187.000 VND |
| Dòng tiền thuần từ HĐĐT (CFI) | +0,0000276 tỷ VND | Không có dữ liệu | 27.579 VND |
| Dòng tiền thuần từ HĐTC (CFF) | 0 | Không có dữ liệu | Không phát sinh |
| Lưu chuyển tiền thuần trong kỳ | -0,000159 tỷ VND | Không có dữ liệu | -159.421 VND |
| Tiền đầu kỳ | 0,073558 | Không có dữ liệu | 73.558.496 VND |
| Tiền cuối kỳ | 0,073399 | Không có dữ liệu | 73.399.075 VND |

**Nhận xét:**  
Dòng tiền từ hoạt động kinh doanh gần như bằng 0 và âm nhẹ. Không có dòng tiền từ bán hàng, không vay/trả nợ trong kỳ. Tiền mặt giảm nhẹ nhưng ở mức cực thấp. Doanh nghiệp không tạo được tiền từ hoạt động cốt lõi, trong khi nghĩa vụ nợ và chi phí phải trả lớn.

---

## 5. CÁC CHỈ SỐ TÀI CHÍNH TRỌNG YẾU

| Chỉ số | 2024Q4 | So với kỳ trước | Diễn giải |
|---|---:|---|---|
| ROE | 5,46% | Không có dữ liệu | **Dương giả tạo** do vốn chủ sở hữu âm; không phản ánh hiệu quả |
| ROA | -2,35% | Không có dữ liệu | Lỗ trên tổng tài sản |
| Debt/Equity | -3,32 | Không có dữ liệu | Âm do vốn chủ sở hữu âm; nên dùng Nợ/Tài sản = 143,1% |
| Net Margin | 0,0% | Không có dữ liệu | Không có doanh thu thuần nên không có ý nghĩa |
| Current ratio | 0,735 | Không có dữ liệu | Tài sản ngắn hạn/nợ ngắn hạn < 1 |
| Quick ratio | 0,729 | Không có dữ liệu | Loại hàng tồn kho vẫn < 1 |
| Cash ratio | 0,00057 | Không có dữ liệu | Tiền/nợ ngắn hạn gần bằng 0 |
| Vốn lưu động thuần | -33,849 tỷ VND | Không có dữ liệu | Thiếu hụt thanh khoản ngắn hạn |
| Nợ phải trả/Tổng tài sản | 143,1% | Không có dữ liệu | Nợ vượt tài sản |
| Vốn chủ sở hữu/Tổng tài sản | -43,1% | Không có dữ liệu | Vốn chủ sở hữu âm |
| Lỗ lũy kế/Vốn điều lệ | 147,6% | Không có dữ liệu | Vốn điều lệ đã bị lỗ lũy kế vượt qua |

**Cảnh báo kế toán:**  
- **ROE dương 5,46%** là hiện tượng do mẫu số âm, không phải dấu hiệu sinh lời.  
- **Debt/Equity âm -3,32** không dùng để đánh giá đòn bẩy thông thường; cần dùng tỷ lệ Nợ/Tài sản.  
- **Net Margin 0,0%** không có ý nghĩa vì doanh nghiệp không có doanh thu thuần; nếu tính trên doanh thu tài chính, biên lợi nhuận âm cực lớn.

---

## 6. CẢNH BÁO VÀ RỦI RO TRỌNG YẾU

1. **Hoạt động liên tục:** Vốn chủ sở hữu âm, lỗ lũy kế lớn hơn vốn điều lệ, nợ phải trả vượt tài sản, tiền mặt cạn kiệt. Đây là các chỉ dấu điển hình của nghi ngờ hoạt động liên tục.
2. **Rủi ro thanh khoản:** Nợ ngắn hạn 127,962 tỷ VND trong khi tài sản ngắn hạn 94,113 tỷ VND; tiền mặt chỉ 0,073 tỷ VND. Khả năng thanh toán ngắn hạn rất yếu.
3. **Rủi ro thu hồi công nợ:** Phải thu khác ngắn hạn gộp 104,872 tỷ VND, dự phòng 27,577 tỷ VND. Cần đánh giá khả năng thu hồi và bên liên quan.
4. **Hàng tồn kho:** Đã trích lập dự phòng 7,979/8,747 tỷ VND, tức gần như toàn bộ. Chất lượng tài sản thấp.
5. **Đầu tư tài chính:** Đầu tư vào công ty con 8 tỷ VND đã trích lập dự phòng 100%, phản ánh suy giảm giá trị.
6. **Chi phí tài chính lớn:** 2,426 tỷ VND trong khi doanh thu tài chính không đáng kể. Gánh nặng lãi vay/chi phí tài chính đang bào mòn vốn.
7. **Không có dòng tiền từ kinh doanh:** CFO âm nhẹ, không có doanh thu bán hàng. Hoạt động hiện tại không tạo tiền.
8. **Phạm vi separate:** Báo cáo riêng không hợp nhất công ty con; tình hình thực tế của tập đoàn có thể khác. Cần xem xét thuyết minh về công ty con, bên liên quan và các cam kết nợ.

---

## 7. KHUYẾN NGHỊ NGẮN GỌN

1. **Ưu tiên sống còn – tái cấu trúc nợ khẩn cấp:** Đàm phán gia hạn nợ, giảm lãi, chuyển nợ thành vốn, hoặc tìm nguồn tài trợ mới. Nếu không, rủi ro mất khả năng trả nợ là hiện hữu.
2. **Tăng vốn:** Yêu cầu cổ đông góp thêm vốn, phát hành cổ phiếu, hoặc bán tài sản không sinh lời để bù đắp vốn chủ sở hữu âm.
3. **Thu hồi công nợ:** Tập trung thu hồi các khoản phải thu khác ngắn hạn; đánh giá lại dự phòng và xử lý nợ khó đòi.
4. **Cắt giảm chi phí:** Kiểm soát chặt chi phí tài chính, chi phí khác; đàm phán lãi suất.
5. **Xử lý tài sản kém hiệu quả:** Thanh lý hàng tồn kho, thu hồi VAT, xử lý đầu tư công ty con.
6. **Xây dựng phương án kinh doanh có doanh thu:** Hiện doanh nghiệp gần như không có doanh thu; cần kế hoạch phục hồi hoặc phương án giải thể/phá sản theo quy định nếu không khả thi.
7. **Công bố thông tin và kiểm toán:** Giải trình rõ vốn chủ sở hữu âm, lỗ lũy kế, khả năng hoạt động liên tục, các giao dịch bên liên quan và khả năng thu hồi tài sản.
8. **Quản trị dòng tiền ngắn hạn:** Lập kế hoạch dòng tiền 13 tuần, giám sát hàng tuần; ưu tiên thanh toán các nghĩa vụ thiết yếu và đàm phán giãn nợ.

---

**Kết luận:**  
2024Q4 cho thấy doanh nghiệp đang mất cân đối tài chính nghiêm trọng: vốn chủ sở hữu âm, nợ vượt tài sản, không có doanh thu, lỗ tiếp diễn và thanh khoản cạn kiệt. Các chỉ số ROE dương và Net Margin 0,0% không phản ánh đúng bản chất do mẫu số âm/không có doanh thu. Ưu tiên hàng đầu là tái cấu trúc nợ – vốn và đánh giá khả năng hoạt động liên tục.

## Phụ lục A — Đối chiếu Riêng vs Hợp nhất

_Không đủ dữ liệu để đối chiếu (cần cả bản riêng và hợp nhất)._

## Phụ lục B — Thuyết minh trọng yếu

_Không có đoạn thuyết minh nào được trích (Reason: no_notes_extracted_from_source)._

## Retrieval Tags (Từ khóa song ngữ)

```yaml
tags:
  - {vi: "vốn chủ sở hữu âm", en: "negative equity"}
  - {vi: "rủi ro hoạt động liên tục", en: "going concern risk"}
  - {vi: "hệ số thanh toán ngắn hạn", en: "current ratio"}
  - {vi: "phải thu khó đòi", en: "doubtful debt provision"}
```