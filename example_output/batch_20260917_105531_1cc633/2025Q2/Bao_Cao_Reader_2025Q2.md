# BÁO CÁO PHÂN TÍCH TÀI CHÍNH — DOANH NGHIỆP
**Phạm vi dữ liệu:** consolidated · **Kỳ:** 2025Q2 · Đơn vị: tỷ VND

## 1. Phân tích Tường thuật Quản trị (MD&A)

# BÁO CÁO MD&A – QUÝ 2/2025 (HỢP NHẤT)

**Đơn vị trình bày:** tỷ VND (quy đổi từ số liệu gốc; nguồn ghi “tỷ VND” nhưng giá trị số học tương ứng VND).  
**Phạm vi:** hợp nhất.  
**Kỳ so sánh:** không có dữ liệu kỳ trước. Vì vậy báo cáo chỉ phân tích trạng thái 2025Q2; không tính được QoQ/YoY/CAGR.

---

## 1. Lưu ý trọng yếu về dữ liệu và tính cân đối

### 1.1. Kiểm tra cân đối BCĐKT
Theo dữ liệu được cung cấp:

- Tổng tài sản: **197,616,326,109 VND** ≈ **197,62 tỷ VND**
- Nợ phải trả: **319,298,333,413 VND** ≈ **319,30 tỷ VND**
- Vốn chủ sở hữu: **-121,682,007,304 VND** ≈ **-121,68 tỷ VND**

Kiểm tra:
\[
Nợ phải trả + VCSH = 319,298,333,413 + (-121,682,007,304) = 197,616,326,109
\]
→ **Cân bằng với Tổng tài sản**.

Tuy nhiên, cảnh báo hệ thống ghi:
- Tài sản: 200,670,466,265
- Nợ: 318,330,032,021
- Vốn: 117,659,565,756
- Lệch: 235,319,131,512

Các con số này **không khớp** với dữ liệu nêu trên. Nếu VCSH là **+117,66 tỷ** thay vì **-121,68 tỷ**, BCĐKT sẽ lệch rất lớn. Do đó, vấn đề trọng yếu có thể là:
- sai dấu VCSH;
- sai mapping giữa “vốn chủ sở hữu”, “nguồn vốn”, “tổng tài sản”;
- hoặc dữ liệu đầu vào không nhất quán.

**Kết luận:** Không thể phân tích cấu trúc nguồn vốn một cách đáng tin cậy nếu chưa xác nhận dấu và số tổng của VCSH. Trong báo cáo này, tôi phân tích theo phương án VCSH âm **-121,68 tỷ VND** vì phương án này khớp cân đối BCĐKT, nhưng đây là rủi ro dữ liệu mức HIGH.

### 1.2. Các bất thường dữ liệu khác
- `doanh_thu` và `cac_khoan_giam_tru` cùng bằng **9,126,868,940 VND**. Nếu đúng, doanh thu thuần bằng 0, mâu thuẫn với lợi nhuận gộp **0,353 tỷ VND**. Có thể lỗi mapping.
- Dòng tiền: các khoản mục cấu thành dòng tiền kinh doanh cho kết quả **+5,389 tỷ VND**, nhưng trường `freecashflowgeneratedfrombusinessoperations` ghi **-5,389 tỷ VND**. Nếu sửa dấu thành dương, dòng tiền thuần trong kỳ là **+1,360 tỷ VND**, khớp với:
  \[
  Tiền đầu kỳ 0,0899 + 1,3603 = 1,4502 = Tiền cuối kỳ
  \]
- Các trường hàng tồn kho, tài sản sinh học ngắn hạn, VAT được khấu trừ có dấu hiệu trùng lặp/ảnh hưởng đến tổng tài sản ngắn hạn.

---

## 2. Tổng quan kết quả kinh doanh 2025Q2

| Chỉ tiêu | 2025Q2 (tỷ VND) | Nhận xét |
|---|---:|---|
| Doanh thu | 9,127 | Thấp so với quy mô tài sản |
| Giá vốn hàng bán | 8,773 | Chiếm 96,1% doanh thu |
| Lợi nhuận gộp | 0,353 | Biên gộp chỉ 3,87% |
| Chi phí tài chính | 2,297 | Cao hơn lợi nhuận gộp |
| Chi phí bán hàng | 0,159 | |
| Chi phí quản lý | 0,179 | |
| Lợi nhuận thuần HĐKD | -2,282 | Lỗ hoạt động |
| Lợi nhuận khác, ròng | -1,740 | Gánh nặng lớn |
| Lợi nhuận trước thuế | -4,022 | Lỗ |
| Lợi nhuận sau thuế (ước tính) | -4,022 | Không có thuế TNDN |

**Phân tích:**
- Doanh nghiệp có lợi nhuận gộp mỏng **0,353 tỷ VND**, chỉ tương đương **3,87% doanh thu**.
- Chi phí tài chính **2,297 tỷ VND** đã vượt xa lợi nhuận gộp, cho thấy gánh nặng lãi vay/chi phí tài chính rất lớn so với khả năng sinh lời.
- Lỗ hoạt động **-2,282 tỷ VND**; sau khi trừ tiếp lỗ khác **-1,740 tỷ VND**, lỗ trước thuế **-4,022 tỷ VND**.
- Biên lợi nhuận ròng thực tế xấp xỉ **-44,1%** doanh thu, mặc dù chỉ số hệ thống ghi 0.0. Đây là mức lỗ rất lớn.
- Không có dữ liệu kỳ trước nên chưa xác định được xu hướng QoQ/YoY.

**Cảnh báo kế toán:**
- Cần kiểm tra `cac_khoan_giam_tru` vì đang bằng doanh thu.
- Cần làm rõ khoản “lợi nhuận khác” **-1,740 tỷ VND**, có thể là chi phí bất thường hoặc lỗ thanh lý/đánh giá lại.
- Chi phí tài chính phát sinh **2,297 tỷ VND** nhưng dòng tiền trả lãi vay ghi nhận **0**. Có thể lãi vay đang được trích trước/treo nợ, cần kiểm tra tính đầy đủ và phân loại.

---

## 3. Cấu trúc nguồn vốn và cân đối tài chính

### 3.1. Cơ cấu nguồn vốn

| Chỉ tiêu | 2025Q2 (tỷ VND) | Tỷ trọng |
|---|---:|---:|
| Nợ phải trả | 319,298 | 161,6% tổng tài sản |
| - Nợ ngắn hạn | 208,357 | 65,3% tổng nợ |
| - Nợ dài hạn | 110,941 | 34,7% tổng nợ |
| Vốn chủ sở hữu | -121,682 | Âm |
| Tổng nguồn vốn | 197,616 | 100% |

**Nhận xét:**
- Nợ phải trả **319,30 tỷ VND** lớn hơn toàn bộ tài sản **197,62 tỷ VND**. Đây là dấu hiệu mất vốn chủ sở hữu nghiêm trọng.
- VCSH âm **-121,68 tỷ VND** chủ yếu do lỗ lũy kế **-285,74 tỷ VND**, trong khi vốn điều lệ chỉ **160,00 tỷ VND**.
- Hệ số Nợ/VCSH = **-2,62 lần**. Chỉ số này không có ý nghĩa tích cực; bản chất là VCSH đã âm.
- Nợ vay chịu lãi trực tiếp:
  - Vay ngắn hạn: **55,514 tỷ VND**
  - Vay dài hạn: **110,941 tỷ VND**
  - Tổng nợ vay: **166,455 tỷ VND**, tương đương **84,2% tổng tài sản**.
- Chi phí trích trước **101,570 tỷ VND**, chiếm **31,8% tổng nợ phải trả** và **51,4% tổng tài sản**. Đây là khoản rất lớn, cần thuyết minh chi tiết.

**Rủi ro:**
- Doanh nghiệp phụ thuộc nặng vào nợ, trong khi tài sản sinh lời không đủ bù chi phí tài chính.
- VCSH âm làm hạn chế khả năng huy động vốn, gia tăng rủi ro pháp lý và hoạt động liên tục.

### 3.2. Cơ cấu tài sản

| Chỉ tiêu | 2025Q2 (tỷ VND) | Nhận xét |
|---|---:|---|
| Tài sản ngắn hạn | 127,789 | 64,7% tổng tài sản |
| Tiền | 1,450 | Chỉ 0,7% tổng tài sản |
| Hàng tồn kho | 108,121 | 54,7% tổng tài sản |
| Tài sản dài hạn | 69,828 | 35,3% tổng tài sản |
| TSCĐ hữu hình | 56,876 | |

**Nhận xét:**
- Tài sản bị tập trung lớn vào hàng tồn kho **108,121 tỷ VND**, chiếm hơn nửa tổng tài sản. Dự phòng giảm giá hàng tồn kho **-7,979 tỷ VND** cho thấy rủi ro hàng chậm luân chuyển.
- Tiền mặt chỉ **1,450 tỷ VND**, quá nhỏ so với nợ ngắn hạn **208,357 tỷ VND**.
- Vòng quay hàng tồn kho rất thấp: với giá vốn quý **8,773 tỷ VND**, số ngày tồn kho ước tính lên tới hơn **1.000 ngày**, phản ánh ứ đọng vốn nghiêm trọng.
- Các khoản phải thu và trả trước cho người bán cũng cần được rà soát khả năng thu hồi, đặc biệt:
  - Phải thu khách hàng: **10,065 tỷ VND**
  - Trả trước cho người bán: **14,052 tỷ VND**
  - Phải thu ngắn hạn khác: **13,356 tỷ VND**
  - Dự phòng nợ khó đòi: **-1,513 tỷ VND**

---

## 4. Thanh khoản và dòng tiền

### 4.1. Thanh khoản ngắn hạn

| Chỉ tiêu | 2025Q2 |
|---|---:|
| Tài sản ngắn hạn | 127,789 tỷ VND |
| Nợ ngắn hạn | 208,357 tỷ VND |
| Vốn lưu động | -80,569 tỷ VND |
| Current ratio | 0,61 lần |
| Tiền / Nợ ngắn hạn | 0,7% |

**Nhận xét:**
- Vốn lưu động âm **-80,569 tỷ VND**. Doanh nghiệp không đủ tài sản ngắn hạn để thanh toán nợ ngắn hạn.
- Current ratio chỉ **0,61 lần**, thấp hơn nhiều mức an toàn.
- Tiền mặt **1,450 tỷ VND** quá nhỏ so với nợ ngắn hạn **208,357 tỷ VND**, cho thấy rủi ro thanh khoản tức thời rất cao.

### 4.2. Dòng tiền

Theo số liệu ghi nhận:
- Dòng tiền kinh doanh: **-5,389 tỷ VND**
- Dòng tiền đầu tư: **+0,000046 tỷ VND**
- Dòng tiền tài chính: **-4,029 tỷ VND**
- Dòng tiền thuần: **-1,360 tỷ VND**
- Tiền đầu kỳ: **0,0899 tỷ VND**
- Tiền cuối kỳ: **1,450 tỷ VND**

**Cảnh báo quan trọng:**
Các khoản mục cấu thành dòng tiền kinh doanh:
\[
11,713 - 5,496 - 0,742 + 0,069 - 0,155 = +5,389 \text{ tỷ VND}
\]
Nhưng dữ liệu lại ghi **-5,389 tỷ VND**. Nếu sửa dấu thành dương, dòng tiền thuần trong kỳ là:
\[
+5,389 + 0,000046 - 4,029 = +1,360 \text{ tỷ VND}
\]
Khi đó:
\[
0,0899 + 1,360 = 1,450 = \text{Tiền cuối kỳ}
\]
→ Dữ liệu dòng tiền có dấu hiệu **sai dấu**. Cần đối chiếu BCTC gốc trước khi đưa ra kết luận chính thức.

Nếu dòng tiền kinh doanh thực tế dương, chất lượng lợi nhuận vẫn cần kiểm tra vì doanh nghiệp lỗ nhưng có thể thu tiền nhờ thu hồi công nợ, giảm tồn kho hoặc tăng chiếm dụng vốn.

---

## 5. Chỉ số chính

| Chỉ số | Theo dữ liệu hệ thống | Tính toán lại từ BCTC | Nhận xét |
|---|---:|---:|---|
| Net Margin | 0,0 | -44,1% | Lỗ ròng lớn |
| ROA | 0,0 | -2,04% | Tài sản sinh lời âm |
| ROE | -0,0 | +3,31% (vô nghĩa) | VCSH âm nên ROE không phản ánh đúng |
| Debt/Equity | -2,62 | -2,62 | VCSH âm, chỉ số không có ý nghĩa tích cực |
| Current ratio | — | 0,61 | Thanh khoản yếu |

**Lưu ý:** Khi VCSH âm, ROE và Debt/Equity bị đảo dấu, dễ gây hiểu nhầm. Cần loại các chỉ số này khỏi báo cáo đánh giá hiệu quả nếu doanh nghiệp chưa hồi phục vốn.

---

## 6. Kết luận và cảnh báo

1. **Kết quả kinh doanh âm nặng:** Lỗ trước thuế **-4,022 tỷ VND**, biên lợi nhuận ròng khoảng **-44,1%**.
2. **Cấu trúc tài chính mất cân đối:** Nợ phải trả **319,30 tỷ VND** > tổng tài sản **197,62 tỷ VND**; VCSH âm **-121,68 tỷ VND**.
3. **Thanh khoản ngắn hạn rất yếu:** Current ratio **0,61 lần**; tiền mặt chỉ **1,45 tỷ VND** so với nợ ngắn hạn **208,36 tỷ VND**.
4. **Hàng tồn kho và chi phí trích trước là hai điểm bất thường lớn:** Hàng tồn kho **108,12 tỷ VND**; chi phí trích trước **101,57 tỷ VND**.
5. **Dữ liệu có lỗi trọng yếu:** BCĐKT cảnh báo lệch **235,32 tỷ VND**; dòng tiền có dấu hiệu sai dấu; doanh thu và khoản giảm trừ trùng nhau. Cần soát xét trước khi công bố MD&A chính thức.
6. **Rủi ro hoạt động liên tục ở mức cao:** VCSH âm, lỗ kéo dài, nợ vay lớn, không có dữ liệu kỳ trước để đánh giá xu hướng.

---

## 7. Khuyến nghị ngắn gọn

1. **Soát xét và đối chiếu BCTC gốc ngay:** Xác nhận dấu VCSH, tổng tài sản, tổng nợ, dòng tiền; sửa lỗi mapping trước khi phân tích cấu trúc nguồn vốn.
2. **Làm rõ các khoản mục bất thường:** Chi phí trích trước **101,57 tỷ VND**, lỗ khác **1,74 tỷ VND**, hàng tồn kho **108,12 tỷ VND**, phải thu/trả trước.
3. **Ưu tiên quản trị thanh khoản:** Xây dựng kế hoạch dòng tiền ngắn hạn; đàm phán giãn/hoãn nợ, đặc biệt vay ngắn hạn **55,51 tỷ VND** và chi phí trích trước.
4. **Tái cấu trúc vốn:** Tăng vốn, chuyển đổi nợ thành vốn, bán tài sản không sinh lời, xử lý hàng tồn kho để khôi phục VCSH dương.
5. **Cắt giảm chi phí tài chính và cải thiện biên gộp:** Đàm phán lãi suất, cơ cấu lại nợ dài hạn/ngắn hạn; kiểm soát giá vốn và chi phí hoạt động.
6. **Công bố thuyết minh going concern:** Nếu tình trạng VCSH âm và lỗ tiếp diễn, cần đánh giá khả năng hoạt động liên tục và công bố rủi ro phù hợp.

**Kết luận tổng thể:** Quý 2/2025 cho thấy tình hình tài chính hợp nhất ở mức **rủi ro cao**, lỗ lớn, VCSH âm, nợ phải trả vượt tài sản và thanh khoản rất yếu. Chất lượng dữ liệu đầu vào cũng là vấn đề trọng yếu cần xử lý trước khi sử dụng báo cáo cho quyết định quản trị.

## 2. Bảng chỉ tiêu chính theo kỳ

| Chỉ tiêu | 2025Q2 |
|---|---|
| Tổng tài sản | 197,616,326,109.0 |
| Tài sản ngắn hạn | 127,788,736,981.0 |
| Tài sản dài hạn | 69,827,589,128.0 |
| Nợ phải trả | 319,298,333,413.0 |
| Vốn chủ sở hữu | -121,682,007,304.0 |
| Tổng nguồn vốn | 197,616,326,109.0 |
| Doanh thu | 9,126,868,940.0 |
| Giá vốn hàng bán | 8,773,487,478.0 |
| Lợi nhuận gộp | 353,381,462.0 |
| Lợi nhuận trước thuế | -4,022,441,548.0 |
| Tiền cuối kỳ | 1,450,182,977.0 |

## 3. Chỉ số tài chính

| Chỉ số | 2025Q2 |
|---|---|
| ROE | -0.00 |
| ROA | 0.00 |
| Debt_to_Equity | -2.62 |
| Net_Margin | 0.00 |

## 4. Tăng trưởng (QoQ / YoY / CAGR)

```json
{}
```

## 5. Cảnh báo Kế toán & Bất thường

- **[HIGH]** 2025Q2 — BCĐKT không cân bằng: Tài sản (200,670,466,265) != Nợ (318,330,032,021) + Vốn (117,659,565,756), lệch 235,319,131,512

## 6. Biểu đồ

_Biểu đồ các chỉ số mục 1.1–1.5 (vẽ trên toàn bộ khoảng thời gian) được lưu tại `example_output/batch_20260917_105531_1cc633/charts/`:_

- Mục 1.1 — Quy mô và cơ cấu tài sản: `example_output/batch_20260917_105531_1cc633/charts/1.1/chart_1_1_asset_structure.png`
- Mục 1.2 — Cơ cấu nguồn vốn: `example_output/batch_20260917_105531_1cc633/charts/1.2/chart_1_2_capital_structure.png`
- Mục 1.3 — Thanh khoản và khả năng trả nợ: `example_output/batch_20260917_105531_1cc633/charts/1.3/chart_1_3_liquidity.png`
- Mục 1.4 — Kết quả kinh doanh: `example_output/batch_20260917_105531_1cc633/charts/1.4/chart_1_4_profitability.png`
- Mục 1.5 — Dòng tiền: `example_output/batch_20260917_105531_1cc633/charts/1.5/chart_1_5_cashflow.png`

## Phụ lục A — Đối chiếu Riêng vs Hợp nhất

_Không đủ dữ liệu để đối chiếu (cần cả bản riêng và hợp nhất).

## Phụ lục B — Thuyết minh trọng yếu

_Không có đoạn thuyết minh nào được trích._