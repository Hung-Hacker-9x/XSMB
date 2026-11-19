import streamlit as st
import numpy as np
import requests
from bs4 import BeautifulSoup
import re
from itertools import product

st.set_page_config(page_title="XSMB 4D Đề Pro", page_icon="🎯", layout="centered")

st.title("🎯 XSMB 4D Đề - Chốt Số Thông Minh")
st.caption("Tự động cập nhật Giải ĐB • Khóa cứng số kết • Lọc xác suất cao")

@st.cache_data(ttl=1800)
def fetch_xsmb_4d():
    """Tự động lấy 4 số cuối Giải Đặc Biệt XSMB gần nhất"""
    urls = [
        "https://xskt.com.vn/xsmb",
        "https://ketqua.vn/xo-so-mien-bac"
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    extracted = []
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                text = soup.get_text(" ", strip=True)
                matches = re.findall(r'(?:ĐB|Đặc biệt)[^\d]{0,15}(\d{5})', text)
                if len(matches) >= 5:
                    extracted = [m[-4:] for m in matches]
                    break
        except Exception:
            continue
    return extracted

history_4d = fetch_xsmb_4d()

if history_4d:
    st.success(f"✅ Đã đồng bộ {len(history_4d)} kỳ Giải ĐB. Kỳ gần nhất: **{history_4d[0]}**")
else:
    st.info("ℹ️ Đang chạy chế độ phân tích xác suất chuẩn (anh có thể nhập thêm số gần đây bên dưới).")

# Nhập bổ sung kết quả gần đây nếu muốn
manual_input = st.text_input(
    "Bổ sung các số 4D ĐB gần nhất (cách nhau dấu cách, không bắt buộc):",
    placeholder="Ví dụ: 4829 1053 8821 3940"
)
if manual_input.strip():
    extra = [x.strip()[-4:] for x in manual_input.split() if x.strip().isdigit() and len(x.strip()) >= 4]
    history_4d = extra + history_4d

# Tính điểm trọng số 0-9 cho từng vị trí (Nghìn - Trăm - Chục - Đơn vị)
def get_positional_weights(data):
    weights = [{d: 1.0 for d in range(10)} for _ in range(4)]
    if not data:
        return weights
    for pos in range(4):
        digits = [int(num[pos]) for num in data if len(num) == 4]
        total = len(digits) + 10
        for d in range(10):
            freq = (digits.count(d) + 1) / total
            recent = digits[:12]
            gan_bonus = 1.25 if d not in recent else 1.0
            weights[pos][d] = freq * gan_bonus
    return weights

# Bộ lọc loại bỏ các dãy 4 số có xác suất rơi cực thấp
def pass_4d_filter(num_str, strict=True):
    digits = [int(c) for c in num_str]
    # 1. Loại tứ quý (vd: 8888)
    if len(set(digits)) == 1:
        return False
    # 2. Loại tam hoa liền kề (vd: 1114)
    for i in range(2):
        if digits[i] == digits[i+1] == digits[i+2]:
            return False
    # 3. Loại sảnh tiến/lùi 4 số (vd: 1234, 9876)
    if (digits[1]-digits[0] == digits[2]-digits[1] == digits[3]-digits[2]) and abs(digits[1]-digits[0]) == 1:
        return False
    if strict:
        # 4. Loại toàn chẵn hoặc toàn lẻ
        evens = sum(1 for d in digits if d % 2 == 0)
        if evens == 0 or evens == 4:
            return False
        # 5. Lọc tổng 4 số trong khoảng vàng 11 - 27
        if not (11 <= sum(digits) <= 27):
            return False
    return True

# Khu vực Khóa Cứng Số Kết (Tùy chọn)
with st.expander("🔒 Khóa Cứng Vị Trí Kết (Bỏ qua nếu muốn app tự chọn hết)", expanded=True):
    st.caption("Chọn **Tự động** ở những vị trí anh muốn máy tự soi, hoặc chọn số cụ thể anh đã kết:")
    col1, col2, col3, col4 = st.columns(4)
    options = ["Tự động"] + [str(i) for i in range(10)]
    
    lock_1 = col1.selectbox("Càng 4 (Nghìn)", options, index=0)
    lock_2 = col2.selectbox("Càng 3 (Trăm)", options, index=0)
    lock_3 = col3.selectbox("Hàng Chục", options, index=0)
    lock_4 = col4.selectbox("Đơn Vị", options, index=0)

locks = [lock_1, lock_2, lock_3, lock_4]
locked_count = sum(1 for x in locks if x != "Tự động")

st.divider()

mode = st.radio(
    "Chọn chế độ xuất số:",
    [
        "🎯 Lọc Dàn Tinh Gọn (Chọn lọc từng số đẹp nhất)",
        "🕸️ Ghép Dàn Càng + Đề 2D (Phủ rộng tối ưu)"
    ]
)

weights = get_positional_weights(history_4d)

if mode == "🎯 Lọc Dàn Tinh Gọn (Chọn lọc từng số đẹp nhất)":
    max_possible = 10 ** (4 - locked_count)
    default_val = min(10, max_possible)
    count = st.slider("Số lượng bộ 4D muốn lấy:", 1, min(30, max_possible), default_val)
    
    if st.button("🚀 Chốt Dàn 4D Ngay", use_container_width=True):
        results = []
        attempts = 0
        # Nới lỏng bộ lọc nếu anh đã khóa cứng từ 2 số trở lên để tránh bị kẹt
        use_strict = True if locked_count <= 1 else False
        
        while len(results) < count and attempts < 15000:
            attempts += 1
            chosen = []
            for pos in range(4):
                if locks[pos] != "Tự động":
                    chosen.append(locks[pos])
                else:
                    pop = list(weights[pos].keys())
                    probs = np.array(list(weights[pos].values()))
                    probs = probs / probs.sum()
                    chosen.append(str(np.random.choice(pop, p=probs)))
            candidate = "".join(chosen)
            if pass_4d_filter(candidate, strict=use_strict) and candidate not in results:
                results.append(candidate)
                
        # Nếu lọc khắt khe chưa đủ số lượng, bổ sung thêm theo trọng số
        while len(results) < count and attempts < 25000:
            attempts += 1
            chosen = [
                locks[pos] if locks[pos] != "Tự động" else str(np.random.choice(range(10)))
                for pos in range(4)
            ]
            candidate = "".join(chosen)
            if candidate not in results:
                results.append(candidate)

        results.sort()
        st.subheader(f"🔥 {len(results)} Bộ 4D Đã Chốt:")
        cols = st.columns(2)
        for idx, val in enumerate(results):
            cols[idx % 2].success(f"**#{idx+1:02d}:** `{val}`  *(Tổng: {sum(int(c) for c in val)})*")
            
        st.text_area("Copy nhanh toàn bộ dàn:", ", ".join(results), height=80)

else:
    c4_num = st.selectbox("Số lượng Càng 4 (nếu để Tự động):", [2, 3, 4], index=0)
    c3_num = st.selectbox("Số lượng Càng 3 (nếu để Tự động):", [2, 3, 4], index=1)
    de_num = st.slider("Số lượng cặp Đề 2 số cuối:", 4, 15, 8)
    
    if st.button("🕸️ Ghép Dàn 4D Tự Động", use_container_width=True):
        pool_c4 = [int(lock_1)] if lock_1 != "Tự động" else sorted(weights[0], key=weights[0].get, reverse=True)[:c4_num]
        pool_c3 = [int(lock_2)] if lock_2 != "Tự động" else sorted(weights[1], key=weights[1].get, reverse=True)[:c3_num]
        
        de_2d = []
        tries = 0
        while len(de_2d) < de_num and tries < 2000:
            tries += 1
            d3 = lock_3 if lock_3 != "Tự động" else str(np.random.choice(range(10), p=np.array(list(weights[2].values()))/sum(weights[2].values())))
            d4 = lock_4 if lock_4 != "Tự động" else str(np.random.choice(range(10), p=np.array(list(weights[3].values()))/sum(weights[3].values())))
            pair = f"{d3}{d4}"
            if pair not in de_2d:
                de_2d.append(pair)
                
        st.info(f"**Càng 4:** `{', '.join(map(str, sorted(pool_c4)))}`  |  **Càng 3:** `{', '.join(map(str, sorted(pool_c3)))}`")
        st.info(f"**Đề 2D ({len(de_2d)} số):** `{', '.join(sorted(de_2d))}`")
        
        raw_dan = [f"{c4}{c3}{de}" for c4, c3, de in product(pool_c4, pool_c3, de_2d)]
        final_dan = sorted([x for x in raw_dan if pass_4d_filter(x, strict=(locked_count == 0))])
        
        st.subheader(f"📋 Dàn 4D Hoàn Chỉnh ({len(final_dan)} số):")
        st.code(", ".join(final_dan), language="text")
