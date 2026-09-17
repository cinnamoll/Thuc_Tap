---
entity_id: null
company_name: null
symbol: null
period_key: "2024Q4"
scope: "separate"
currency_unit: "VND"
circular: "200"
lang: "vi"
batch_id: "batch_20260917_103640_66ecb6"
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

**Doanh nghiệp:** N/A  
**Phạm vi:** Báo cáo riêng (separate)  
**Kỳ báo cáo:** Quý 4/2024  
**Đơn vị trình bày:** tỷ VND (quy đổi từ dữ liệu gốc VND; 1 tỷ VND = 1.000.000.000 VND). Một số chỉ tiêu rất nhỏ được ghi chú thêm bằng VND.

> **Lưu ý quan trọng về dữ liệu:** Không có dữ liệu kỳ trước và không có tăng trưởng QoQ/YoY/CAGR. Do đó, báo cáo chỉ phân tích kỳ 2024Q4; mọi nhận định về thay đổi so với kỳ trước đều là **không xác định**.

---

## 1. Tóm tắt điều hành

Doanh nghiệp đang ở trạng thái tài chính rất yếu:

- **Tổng tài sản:** 167,40 tỷ VND.
- **Nợ phải trả:** 239,51 tỷ VND, lớn hơn tổng tài sản 72,11 tỷ VND.
- **Vốn chủ sở hữu:** âm 72,11 tỷ VND.
- **Kết quả kinh doanh:** lỗ sau thuế 3,94 tỷ VND; gần như không có doanh thu bán hàng, doanh thu tài chính chỉ 27.579 VND.
- **Thanh khoản:** tiền mặt cuối kỳ 0,0734 tỷ VND; hệ số thanh toán ngắn hạn khoảng 0,74 lần; vốn lưu động âm 33,85 tỷ VND.
- **Rủi ro trọng yếu:** mất khả năng thanh toán, vốn chủ sở hữu âm, phụ thuộc lớn vào khả năng thu hồi các khoản phải thu và tái cấu trúc nợ.

---

## 2. Phân tích chi tiết

### 2.1. Cơ cấu tài sản

| Chỉ tiêu | Giá trị (tỷ VND) | % tổng tài sản | Ghi chú |
|---|---:|---:|---|
| Tổng tài sản | 167,40 | 100,0% | |
| Tài sản ngắn hạn | 94,11 | 56,2% | |
| – Tiền và tương đương tiền | 0,0734 | 0,04% | Rất thấp |
| – Phải thu ngắn hạn | 91,69 | 54,8% | Chiếm tỷ trọng lớn nhất |
| – Hàng tồn kho (net) | 0,768 | 0,46% | Gross 8,747; dự phòng -7,979 |
| – Tài sản sinh học ngắn hạn/thuế GTGT được khấu trừ | 1,585 | 0,95% | Cần đối chiếu thuyết minh |
| Tài sản dài hạn | 73,29 | 43,8% | |
| – TSCĐ thuê tài chính | 64,33 | 38,4% | Chiếm tỷ trọng lớn |
| – Chi phí trả trước dài hạn | 8,954 | 5,3% | |
| – Đầu tư vào công ty con | 8,000 | 4,8% | Đã trích lập dự phòng toàn bộ -8,000, net 0 |

**Phân tích:**

- **Phải thu ngắn hạn** là khoản mục lớn nhất: 91,69 tỷ VND, chiếm 54,8% tổng tài sản. Trong đó, **phải thu khác ngắn hạn** gross lên tới 104,87 tỷ VND, đã trích lập dự phòng 27,58 tỷ VND. Đây là rủi ro trọng yếu vì chất lượng khoản phải thu khác thường khó đánh giá, có thể liên quan đến bên liên quan hoặc khoản tạm ứng/cho vay.
- **Hàng tồn kho** gross 8,747 tỷ VND nhưng đã trích lập dự phòng 7,979 tỷ VND, tức tỷ lệ dự phòng khoảng 91,2%. Giá trị thuần còn lại chỉ 0,768 tỷ VND, phản ánh hàng tồn kho có chất lượng rất thấp.
- **Đầu tư vào công ty con** 8,000 tỷ VND đã bị trích lập dự phòng toàn bộ, cho thấy khoản đầu tư này gần như không còn giá trị thu hồi kỳ vọng.
- Tài sản dài hạn chủ yếu là **TSCĐ thuê tài chính** 64,33 tỷ VND và chi phí trả trước dài hạn 8,954 tỷ VND.

**Thay đổi so với kỳ trước:** Không xác định – không có dữ liệu kỳ trước.  
**Cảnh báo kế toán:** Cần thuyết minh chi tiết tuổi nợ, bên liên quan, khả năng thu hồi của khoản phải thu khác; cần đánh giá lại giá trị thuần của hàng tồn kho và khoản đầu tư vào công ty con.

---

### 2.2. Cơ cấu nguồn vốn

| Chỉ tiêu | Giá trị (tỷ VND) | % tổng tài sản | Ghi chú |
|---|---:|---:|---|
| Nợ phải trả | 239,51 | 143,1% | Lớn hơn tổng tài sản |
| – Nợ ngắn hạn | 127,96 | 76,4% | |
| – Nợ dài hạn | 111,54 | 66,6% | Chủ yếu là vay và nợ thuê tài chính dài hạn |
| Vốn chủ sở hữu | -72,11 | -43,1% | Âm |
| – Vốn góp | 160,00 | 95,6% | |
| – Thặng dư vốn | 3,168 | 1,9% | |
| – Lợi nhuận sau thuế chưa phân phối | -236,16 | -141,1% | Lỗ lũy kế lớn |

**Phân tích:**

- **Nợ phải trả 239,51 tỷ VND** vượt tổng tài sản 72,11 tỷ VND. Điều này đồng nghĩa toàn bộ tài sản không đủ để thanh toán nợ.
- **Vay và nợ thuê tài chính** gồm:
  - Ngắn hạn: 33,02 tỷ VND.
  - Dài hạn: 111,54 tỷ VND.
  - Tổng nợ vay khoảng 144,56 tỷ VND, chiếm khoảng 60,4% tổng nợ phải trả và 86,3% tổng tài sản.
- **Vốn chủ sở hữu âm 72,11 tỷ VND**, chủ yếu do lỗ lũy kế 236,16 tỷ VND vượt xa vốn góp 160 tỷ VND và các quỹ.
- Chỉ số **Debt/Equity = -3,32** không có ý nghĩa phân tích thông thường vì mẫu số vốn chủ sở hữu âm.

**Thay đổi so với kỳ trước:** Không xác định – không có dữ liệu kỳ trước.  
**Cảnh báo kế toán:** Cần đánh giá khả năng hoạt động liên tục; nguy cơ vi phạm điều khoản vay, mất khả năng thanh toán và yêu cầu công bố thông tin về khả năng thanh toán nợ đến hạn.

---

### 2.3. Thanh khoản

| Chỉ tiêu | Giá trị | Nhận xét |
|---|---:|---|
| Hệ số thanh toán ngắn hạn | 94,11 / 127,96 = **0,74 lần** | < 1, thiếu hụt thanh khoản |
| Hệ số thanh toán nhanh | ~0,72 lần | < 1 |
| Hệ số tiền mặt | 0,0734 / 127,96 = **0,0006 lần** | Rất thấp |
| Vốn lưu động | 94,11 – 127,96 = **-33,85 tỷ VND** | Âm |
| Tiền cuối kỳ | 0,0734 tỷ VND | Quá mỏng |

**Phân tích:**

- Doanh nghiệp không đủ tài sản ngắn hạn để thanh toán nợ ngắn hạn.
- Tiền mặt cuối kỳ chỉ 73,4 triệu VND, trong khi nợ ngắn hạn 127,96 tỷ VND. Khả năng thanh toán tức thời gần như bằng không.
- Dòng tiền hoạt động âm, không có dòng tiền tài trợ mới, cho thấy doanh nghiệp rất khó xoay xở nếu không thu hồi được phải thu hoặc tái cấu trúc nợ.

**Thay đổi so với kỳ trước:** Không xác định – không có dữ liệu kỳ trước.  
**Cảnh báo kế toán:** Cần đánh giá chi tiết các khoản nợ đến hạn, lịch trả nợ và khả năng gia hạn.

---

### 2.4. Kết quả kinh doanh

| Chỉ tiêu | Giá trị (tỷ VND) | Ghi chú |
|---|---:|---|
| Doanh thu tài chính | 0,0000276 | Tương đương 27.579 VND |
| Chi phí tài chính | 2,426 | |
| Chi phí bán hàng | 0,000187 | |
| Lợi nhuận thuần kinh doanh | -2,426 | |
| Chi phí khác/lỗ khác | -1,513 | |
| Lợi nhuận trước thuế | -3,939 | |
| Lợi nhuận sau thuế | -3,939 | |

**Phân tích:**

- Doanh nghiệp gần như **không có doanh thu bán hàng**; doanh thu tài chính chỉ 27.579 VND, không đáng kể.
- Chi phí tài chính 2,426 tỷ VND và chi phí khác 1,513 tỷ VND là nguyên nhân chính gây lỗ.
- **Lỗ sau thuế 3,939 tỷ VND** trong kỳ, làm lỗ lũy kế tăng lên 236,16 tỷ VND.
- **Net Margin = 0,0%** phản ánh không có doanh thu thuần. Nếu dùng doanh thu tài chính làm mẫu số, biên lợi nhuận âm rất lớn và không có ý nghĩa so sánh.

**Thay đổi so với kỳ trước:** Không xác định – không có dữ liệu kỳ trước.  
**Cảnh báo kế toán:** Cần thuyết minh bản chất chi phí tài chính và chi phí khác; kiểm tra xem có khoản trích lập dự phòng hoặc chi phí không bằng tiền nào không.

---

### 2.5. Dòng tiền

| Chỉ tiêu | Giá trị (tỷ VND) |
|---|---:|
| Dòng tiền hoạt động kinh doanh (CFO) | -0,000187 |
| Dòng tiền đầu tư (CFI) | +0,0000276 |
| Dòng tiền tài chính (CFF) | 0,000 |
| Lưu chuyển tiền thuần trong kỳ | -0,000159 |
| Tiền đầu kỳ | 0,073558 |
| Tiền cuối kỳ | 0,073399 |

**Phân tích:**

- CFO âm nhưng mức âm rất nhỏ so với lỗ kế toán 3,939 tỷ VND. Điều này cho thấy phần lớn lỗ có thể đến từ chi phí phi tiền mặt, trích lập dự phòng hoặc các khoản phải trả chưa thanh toán.
- Không có dòng tiền từ vay/trả nợ hay phát hành vốn.
- Tiền mặt cuối kỳ giảm nhẹ 159.421 VND so với đầu kỳ, nhưng mức tiền mặt tuyệt đối quá thấp.

**Thay đổi so với kỳ trước:** Không xác định – không có dữ liệu kỳ trước.  
**Cảnh báo kế toán:** Cần đối chiếu lỗ kế toán với dòng tiền thực tế; làm rõ các khoản trích lập dự phòng và chi phí lãi vay chưa thanh toán.

---

### 2.6. Các chỉ số trọng yếu

| Chỉ số | Giá trị | Diễn giải |
|---|---:|---|
| ROE | 5,46% | Dương do vốn chủ sở hữu âm kết hợp lỗ; **không phản ánh hiệu quả tích cực** |
| ROA | -2,35% | Tài sản sinh lời âm |
| Debt/Equity | -3,32 | Âm do vốn chủ sở hữu âm; không có ý nghĩa so sánh |
| Net Margin | 0,0% | Không có doanh thu thuần; chỉ số không có ý nghĩa |

**Thay đổi so với kỳ trước:** Không xác định – không có dữ liệu kỳ trước.

---

## 3. Rủi ro và cảnh báo kế toán

1. **Rủi ro hoạt động liên tục:** Vốn chủ sở hữu âm, lỗ lớn, vốn lưu động âm, tiền mặt thấp.
2. **Mất khả năng thanh toán:** Nợ ngắn hạn 127,96 tỷ VND vượt tài sản ngắn hạn 94,11 tỷ VND; tiền mặt chỉ 0,0734 tỷ VND.
3. **Chất lượng tài sản thấp:** Phải thu khác gross 104,87 tỷ VND, dự phòng 27,58 tỷ VND; hàng tồn kho đã trích lập dự phòng 91,2%; đầu tư vào công ty con đã trích lập toàn bộ.
4. **Nợ vay lớn:** Tổng nợ vay khoảng 144,56 tỷ VND, gánh nặng chi phí tài chính 2,426 tỷ VND trong kỳ.
5. **Dữ liệu có dấu hiệu cần đối chiếu:** Một số chỉ tiêu như tài sản sinh học ngắn hạn/thuế GTGT, TSCĐ thuê tài chính, TSCĐ hữu hình, khấu hao có thể chồng lấn hoặc trình bày chưa rõ. Cần kiểm tra thuyết minh báo cáo tài chính.
6. **Thiếu dữ liệu so sánh:** Không có số liệu kỳ trước nên không thể đánh giá xu hướng QoQ/YoY.

---

## 4. Khuyến nghị

1. **Đánh giá khả năng hoạt động liên tục:** Xây dựng phương án tái cấu trúc tài chính, có thể cần tăng vốn, chuyển nợ thành vốn hoặc tìm nhà đầu tư mới.
2. **Ưu tiên thanh khoản:** Lập kế hoạch dòng tiền ngắn hạn, phân loại nợ đến hạn, đàm phán giãn nợ/hoán đổi nợ.
3. **Thu hồi công nợ:** Tập trung thu hồi phải thu khác và phải thu khách hàng; phân loại tuổi nợ, trích lập dự phòng đầy đủ.
4. **Xử lý tài sản kém hiệu quả:** Thanh lý hàng tồn kho, đánh giá lại khoản đầu tư vào công ty con, xem xét thoái vốn nếu không còn giá trị.
5. **Cắt giảm chi phí:** Kiểm soát chi phí tài chính, chi phí khác; hạn chế phát sinh lỗ thêm.
6. **Minh bạch thông tin:** Công bố rõ bản chất các khoản phải thu, giao dịch bên liên quan, dự phòng và khả năng thanh toán.
7. **Phương án pháp lý:** Nếu không có khả năng phục hồi, cần xem xét giải thể, phá sản hoặc phương án tái cơ cấu theo quy định.

---

## 5. Kết luận

Doanh nghiệp trong kỳ 2024Q4 đang ở tình trạng **âm vốn chủ sở hữu, lỗ lớn, thanh khoản cạn kiệt và nợ phải trả vượt tài sản**. Các rủi ro trọng yếu tập trung vào khả năng thu hồi phải thu, giá trị hàng tồn kho, nợ vay và khả năng hoạt động liên tục. Do không có dữ liệu kỳ trước, báo cáo không thể đánh giá mức độ cải thiện hay suy giảm so với quý trước. Khuyến nghị doanh nghiệp cần hành động khẩn cấp về tái cấu trúc tài chính, thu hồi công nợ và kiểm soát thanh khoản.

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

_Biểu đồ các chỉ số mục 1.1–1.5 (vẽ trên toàn bộ khoảng thời gian) được lưu tại `example_output/batch_20260917_103640_66ecb6/charts/`:_

- Mục 1.1 — Quy mô và cơ cấu tài sản: `example_output/batch_20260917_103640_66ecb6/charts/1.1/chart_1_1_asset_structure.png`
- Mục 1.2 — Cơ cấu nguồn vốn: `example_output/batch_20260917_103640_66ecb6/charts/1.2/chart_1_2_capital_structure.png`
- Mục 1.3 — Thanh khoản và khả năng trả nợ: `example_output/batch_20260917_103640_66ecb6/charts/1.3/chart_1_3_liquidity.png`
- Mục 1.4 — Kết quả kinh doanh: `example_output/batch_20260917_103640_66ecb6/charts/1.4/chart_1_4_profitability.png`
- Mục 1.5 — Dòng tiền: `example_output/batch_20260917_103640_66ecb6/charts/1.5/chart_1_5_cashflow.png`

## 8. Đánh giá rủi ro tài chính tổng hợp (LLM-generated)

# BÁO CÁO PHÂN TÍCH QUẢN TRỊ (MD&A) – KỲ 2024Q4

**Doanh nghiệp:** N/A  
**Phạm vi:** Báo cáo riêng (separate)  
**Kỳ báo cáo:** Quý 4/2024  
**Đơn vị trình bày:** tỷ VND (quy đổi từ dữ liệu gốc VND; 1 tỷ VND = 1.000.000.000 VND). Một số chỉ tiêu rất nhỏ được ghi chú thêm bằng VND.

> **Lưu ý quan trọng về dữ liệu:** Không có dữ liệu kỳ trước và không có tăng trưởng QoQ/YoY/CAGR. Do đó, báo cáo chỉ phân tích kỳ 2024Q4; mọi nhận định về thay đổi so với kỳ trước đều là **không xác định**.

---

## 1. Tóm tắt điều hành

Doanh nghiệp đang ở trạng thái tài chính rất yếu:

- **Tổng tài sản:** 167,40 tỷ VND.
- **Nợ phải trả:** 239,51 tỷ VND, lớn hơn tổng tài sản 72,11 tỷ VND.
- **Vốn chủ sở hữu:** âm 72,11 tỷ VND.
- **Kết quả kinh doanh:** lỗ sau thuế 3,94 tỷ VND; gần như không có doanh thu bán hàng, doanh thu tài chính chỉ 27.579 VND.
- **Thanh khoản:** tiền mặt cuối kỳ 0,0734 tỷ VND; hệ số thanh toán ngắn hạn khoảng 0,74 lần; vốn lưu động âm 33,85 tỷ VND.
- **Rủi ro trọng yếu:** mất khả năng thanh toán, vốn chủ sở hữu âm, phụ thuộc lớn vào khả năng thu hồi các khoản phải thu và tái cấu trúc nợ.

---

## 2. Phân tích chi tiết

### 2.1. Cơ cấu tài sản

| Chỉ tiêu | Giá trị (tỷ VND) | % tổng tài sản | Ghi chú |
|---|---:|---:|---|
| Tổng tài sản | 167,40 | 100,0% | |
| Tài sản ngắn hạn | 94,11 | 56,2% | |
| – Tiền và tương đương tiền | 0,0734 | 0,04% | Rất thấp |
| – Phải thu ngắn hạn | 91,69 | 54,8% | Chiếm tỷ trọng lớn nhất |
| – Hàng tồn kho (net) | 0,768 | 0,46% | Gross 8,747; dự phòng -7,979 |
| – Tài sản sinh học ngắn hạn/thuế GTGT được khấu trừ | 1,585 | 0,95% | Cần đối chiếu thuyết minh |
| Tài sản dài hạn | 73,29 | 43,8% | |
| – TSCĐ thuê tài chính | 64,33 | 38,4% | Chiếm tỷ trọng lớn |
| – Chi phí trả trước dài hạn | 8,954 | 5,3% | |
| – Đầu tư vào công ty con | 8,000 | 4,8% | Đã trích lập dự phòng toàn bộ -8,000, net 0 |

**Phân tích:**

- **Phải thu ngắn hạn** là khoản mục lớn nhất: 91,69 tỷ VND, chiếm 54,8% tổng tài sản. Trong đó, **phải thu khác ngắn hạn** gross lên tới 104,87 tỷ VND, đã trích lập dự phòng 27,58 tỷ VND. Đây là rủi ro trọng yếu vì chất lượng khoản phải thu khác thường khó đánh giá, có thể liên quan đến bên liên quan hoặc khoản tạm ứng/cho vay.
- **Hàng tồn kho** gross 8,747 tỷ VND nhưng đã trích lập dự phòng 7,979 tỷ VND, tức tỷ lệ dự phòng khoảng 91,2%. Giá trị thuần còn lại chỉ 0,768 tỷ VND, phản ánh hàng tồn kho có chất lượng rất thấp.
- **Đầu tư vào công ty con** 8,000 tỷ VND đã bị trích lập dự phòng toàn bộ, cho thấy khoản đầu tư này gần như không còn giá trị thu hồi kỳ vọng.
- Tài sản dài hạn chủ yếu là **TSCĐ thuê tài chính** 64,33 tỷ VND và chi phí trả trước dài hạn 8,954 tỷ VND.

**Thay đổi so với kỳ trước:** Không xác định – không có dữ liệu kỳ trước.  
**Cảnh báo kế toán:** Cần thuyết minh chi tiết tuổi nợ, bên liên quan, khả năng thu hồi của khoản phải thu khác; cần đánh giá lại giá trị thuần của hàng tồn kho và khoản đầu tư vào công ty con.

---

### 2.2. Cơ cấu nguồn vốn

| Chỉ tiêu | Giá trị (tỷ VND) | % tổng tài sản | Ghi chú |
|---|---:|---:|---|
| Nợ phải trả | 239,51 | 143,1% | Lớn hơn tổng tài sản |
| – Nợ ngắn hạn | 127,96 | 76,4% | |
| – Nợ dài hạn | 111,54 | 66,6% | Chủ yếu là vay và nợ thuê tài chính dài hạn |
| Vốn chủ sở hữu | -72,11 | -43,1% | Âm |
| – Vốn góp | 160,00 | 95,6% | |
| – Thặng dư vốn | 3,168 | 1,9% | |
| – Lợi nhuận sau thuế chưa phân phối | -236,16 | -141,1% | Lỗ lũy kế lớn |

**Phân tích:**

- **Nợ phải trả 239,51 tỷ VND** vượt tổng tài sản 72,11 tỷ VND. Điều này đồng nghĩa toàn bộ tài sản không đủ để thanh toán nợ.
- **Vay và nợ thuê tài chính** gồm:
  - Ngắn hạn: 33,02 tỷ VND.
  - Dài hạn: 111,54 tỷ VND.
  - Tổng nợ vay khoảng 144,56 tỷ VND, chiếm khoảng 60,4% tổng nợ phải trả và 86,3% tổng tài sản.
- **Vốn chủ sở hữu âm 72,11 tỷ VND**, chủ yếu do lỗ lũy kế 236,16 tỷ VND vượt xa vốn góp 160 tỷ VND và các quỹ.
- Chỉ số **Debt/Equity = -3,32** không có ý nghĩa phân tích thông thường vì mẫu số vốn chủ sở hữu âm.

**Thay đổi so với kỳ trước:** Không xác định – không có dữ liệu kỳ trước.  
**Cảnh báo kế toán:** Cần đánh giá khả năng hoạt động liên tục; nguy cơ vi phạm điều khoản vay, mất khả năng thanh toán và yêu cầu công bố thông tin về khả năng thanh toán nợ đến hạn.

---

### 2.3. Thanh khoản

| Chỉ tiêu | Giá trị | Nhận xét |
|---|---:|---|
| Hệ số thanh toán ngắn hạn | 94,11 / 127,96 = **0,74 lần** | < 1, thiếu hụt thanh khoản |
| Hệ số thanh toán nhanh | ~0,72 lần | < 1 |
| Hệ số tiền mặt | 0,0734 / 127,96 = **0,0006 lần** | Rất thấp |
| Vốn lưu động | 94,11 – 127,96 = **-33,85 tỷ VND** | Âm |
| Tiền cuối kỳ | 0,0734 tỷ VND | Quá mỏng |

**Phân tích:**

- Doanh nghiệp không đủ tài sản ngắn hạn để thanh toán nợ ngắn hạn.
- Tiền mặt cuối kỳ chỉ 73,4 triệu VND, trong khi nợ ngắn hạn 127,96 tỷ VND. Khả năng thanh toán tức thời gần như bằng không.
- Dòng tiền hoạt động âm, không có dòng tiền tài trợ mới, cho thấy doanh nghiệp rất khó xoay xở nếu không thu hồi được phải thu hoặc tái cấu trúc nợ.

**Thay đổi so với kỳ trước:** Không xác định – không có dữ liệu kỳ trước.  
**Cảnh báo kế toán:** Cần đánh giá chi tiết các khoản nợ đến hạn, lịch trả nợ và khả năng gia hạn.

---

### 2.4. Kết quả kinh doanh

| Chỉ tiêu | Giá trị (tỷ VND) | Ghi chú |
|---|---:|---|
| Doanh thu tài chính | 0,0000276 | Tương đương 27.579 VND |
| Chi phí tài chính | 2,426 | |
| Chi phí bán hàng | 0,000187 | |
| Lợi nhuận thuần kinh doanh | -2,426 | |
| Chi phí khác/lỗ khác | -1,513 | |
| Lợi nhuận trước thuế | -3,939 | |
| Lợi nhuận sau thuế | -3,939 | |

**Phân tích:**

- Doanh nghiệp gần như **không có doanh thu bán hàng**; doanh thu tài chính chỉ 27.579 VND, không đáng kể.
- Chi phí tài chính 2,426 tỷ VND và chi phí khác 1,513 tỷ VND là nguyên nhân chính gây lỗ.
- **Lỗ sau thuế 3,939 tỷ VND** trong kỳ, làm lỗ lũy kế tăng lên 236,16 tỷ VND.
- **Net Margin = 0,0%** phản ánh không có doanh thu thuần. Nếu dùng doanh thu tài chính làm mẫu số, biên lợi nhuận âm rất lớn và không có ý nghĩa so sánh.

**Thay đổi so với kỳ trước:** Không xác định – không có dữ liệu kỳ trước.  
**Cảnh báo kế toán:** Cần thuyết minh bản chất chi phí tài chính và chi phí khác; kiểm tra xem có khoản trích lập dự phòng hoặc chi phí không bằng tiền nào không.

---

### 2.5. Dòng tiền

| Chỉ tiêu | Giá trị (tỷ VND) |
|---|---:|
| Dòng tiền hoạt động kinh doanh (CFO) | -0,000187 |
| Dòng tiền đầu tư (CFI) | +0,0000276 |
| Dòng tiền tài chính (CFF) | 0,000 |
| Lưu chuyển tiền thuần trong kỳ | -0,000159 |
| Tiền đầu kỳ | 0,073558 |
| Tiền cuối kỳ | 0,073399 |

**Phân tích:**

- CFO âm nhưng mức âm rất nhỏ so với lỗ kế toán 3,939 tỷ VND. Điều này cho thấy phần lớn lỗ có thể đến từ chi phí phi tiền mặt, trích lập dự phòng hoặc các khoản phải trả chưa thanh toán.
- Không có dòng tiền từ vay/trả nợ hay phát hành vốn.
- Tiền mặt cuối kỳ giảm nhẹ 159.421 VND so với đầu kỳ, nhưng mức tiền mặt tuyệt đối quá thấp.

**Thay đổi so với kỳ trước:** Không xác định – không có dữ liệu kỳ trước.  
**Cảnh báo kế toán:** Cần đối chiếu lỗ kế toán với dòng tiền thực tế; làm rõ các khoản trích lập dự phòng và chi phí lãi vay chưa thanh toán.

---

### 2.6. Các chỉ số trọng yếu

| Chỉ số | Giá trị | Diễn giải |
|---|---:|---|
| ROE | 5,46% | Dương do vốn chủ sở hữu âm kết hợp lỗ; **không phản ánh hiệu quả tích cực** |
| ROA | -2,35% | Tài sản sinh lời âm |
| Debt/Equity | -3,32 | Âm do vốn chủ sở hữu âm; không có ý nghĩa so sánh |
| Net Margin | 0,0% | Không có doanh thu thuần; chỉ số không có ý nghĩa |

**Thay đổi so với kỳ trước:** Không xác định – không có dữ liệu kỳ trước.

---

## 3. Rủi ro và cảnh báo kế toán

1. **Rủi ro hoạt động liên tục:** Vốn chủ sở hữu âm, lỗ lớn, vốn lưu động âm, tiền mặt thấp.
2. **Mất khả năng thanh toán:** Nợ ngắn hạn 127,96 tỷ VND vượt tài sản ngắn hạn 94,11 tỷ VND; tiền mặt chỉ 0,0734 tỷ VND.
3. **Chất lượng tài sản thấp:** Phải thu khác gross 104,87 tỷ VND, dự phòng 27,58 tỷ VND; hàng tồn kho đã trích lập dự phòng 91,2%; đầu tư vào công ty con đã trích lập toàn bộ.
4. **Nợ vay lớn:** Tổng nợ vay khoảng 144,56 tỷ VND, gánh nặng chi phí tài chính 2,426 tỷ VND trong kỳ.
5. **Dữ liệu có dấu hiệu cần đối chiếu:** Một số chỉ tiêu như tài sản sinh học ngắn hạn/thuế GTGT, TSCĐ thuê tài chính, TSCĐ hữu hình, khấu hao có thể chồng lấn hoặc trình bày chưa rõ. Cần kiểm tra thuyết minh báo cáo tài chính.
6. **Thiếu dữ liệu so sánh:** Không có số liệu kỳ trước nên không thể đánh giá xu hướng QoQ/YoY.

---

## 4. Khuyến nghị

1. **Đánh giá khả năng hoạt động liên tục:** Xây dựng phương án tái cấu trúc tài chính, có thể cần tăng vốn, chuyển nợ thành vốn hoặc tìm nhà đầu tư mới.
2. **Ưu tiên thanh khoản:** Lập kế hoạch dòng tiền ngắn hạn, phân loại nợ đến hạn, đàm phán giãn nợ/hoán đổi nợ.
3. **Thu hồi công nợ:** Tập trung thu hồi phải thu khác và phải thu khách hàng; phân loại tuổi nợ, trích lập dự phòng đầy đủ.
4. **Xử lý tài sản kém hiệu quả:** Thanh lý hàng tồn kho, đánh giá lại khoản đầu tư vào công ty con, xem xét thoái vốn nếu không còn giá trị.
5. **Cắt giảm chi phí:** Kiểm soát chi phí tài chính, chi phí khác; hạn chế phát sinh lỗ thêm.
6. **Minh bạch thông tin:** Công bố rõ bản chất các khoản phải thu, giao dịch bên liên quan, dự phòng và khả năng thanh toán.
7. **Phương án pháp lý:** Nếu không có khả năng phục hồi, cần xem xét giải thể, phá sản hoặc phương án tái cơ cấu theo quy định.

---

## 5. Kết luận

Doanh nghiệp trong kỳ 2024Q4 đang ở tình trạng **âm vốn chủ sở hữu, lỗ lớn, thanh khoản cạn kiệt và nợ phải trả vượt tài sản**. Các rủi ro trọng yếu tập trung vào khả năng thu hồi phải thu, giá trị hàng tồn kho, nợ vay và khả năng hoạt động liên tục. Do không có dữ liệu kỳ trước, báo cáo không thể đánh giá mức độ cải thiện hay suy giảm so với quý trước. Khuyến nghị doanh nghiệp cần hành động khẩn cấp về tái cấu trúc tài chính, thu hồi công nợ và kiểm soát thanh khoản.

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