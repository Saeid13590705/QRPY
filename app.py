# ============================================================
# app.py  —  Streamlit  (برای Hugging Face Spaces)
# ============================================================
import streamlit as st
from qr_core import calculate, b8, bvar

st.set_page_config(
    page_title="QRPY — آموزش ساخت QR",
    page_icon="🎓",
    layout="wide",
)

st.title("🎓 QRPY — آموزش گام‌به‌گام ساخت QR Code")
st.caption("Version 1 — Error Correction Level L — Byte Mode — Mask 0")

name = st.text_input(
    "نام انگلیسی (حداکثر ۱۷ کاراکتر):",
    max_chars=17,
    placeholder="مثلاً SAEID",
)

if not name:
    st.info("یک نام انگلیسی وارد کنید تا مراحل ساخت QR نمایش داده شود.")
    st.stop()

try:
    result = calculate(name)
except Exception as e:
    st.error(f"خطا: {e}")
    st.stop()

# ---------- گام ۱ ----------
st.header("گام ۱ — تبدیل نام به بیت")
st.markdown("**Mode** (۴ بیت) + **Count** (۸ بیت) + **هر کاراکتر** (۸ بیت)")

col1, col2 = st.columns(2)
with col1:
    st.write("**Mode**")
    st.code("".join(map(str, result["step1"]["mode_bits"])), language=None)
    st.caption("0100 = Byte Mode")
    st.write(f"**Character Count = {result['step1']['count']}**")
    st.code("".join(map(str, result["step1"]["count_bits"])), language=None)
with col2:
    st.write("**کاراکترها**")
    char_data = [
        {"حرف": c["char"], "Hex": c["hex"], "بیت‌ها": "".join(map(str, c["bits"]))}
        for c in result["step1"]["per_char"]
    ]
    st.dataframe(char_data, use_container_width=True)

st.write(f"**بیت‌های گام ۱ ({result['step1']['bit_length']} بیت):**")
st.code("".join(map(str, result["step1"]["all_bits"])), language=None)

# ---------- گام ۲ ----------
st.header("گام ۲ — Terminator و Byte Alignment")
col1, col2 = st.columns(2)
with col1:
    st.write(f"**بودجه:** {result['step2']['budget']} بیت = ۱۹ × ۸")
    st.write(f"**Terminator ({len(result['step2']['terminator'])} بیت):**")
    st.code("".join(map(str, result["step2"]["terminator"])) or "—", language=None)
    st.write(f"**Byte Alignment ({len(result['step2']['align_pad'])} بیت):**")
    st.code("".join(map(str, result["step2"]["align_pad"])) or "—", language=None)
with col2:
    st.metric("طول نهایی", f"{result['step2']['bit_length']} بیت")
    st.caption(f"= {result['step2']['bit_length'] // 8} بایت کامل")

st.write("**بیت‌های بعد از گام ۲:**")
st.code("".join(map(str, result["step2"]["bits"])), language=None)

# ---------- گام ۳ ----------
st.header("گام ۳ — Pad Codewords")
col1, col2 = st.columns(2)
with col1:
    st.write(f"**بایت‌های اولیه ({len(result['step3']['initial_codewords'])}):**")
    st.code(" ".join(f"{x:02X}" for x in result["step3"]["initial_codewords"]), language=None)
    st.write(f"**Pad اضافه‌شده ({len(result['step3']['pad_added'])}):**")
    st.code(" ".join(f"{x:02X}" for x in result["step3"]["pad_added"]) or "—", language=None)
with col2:
    st.write("**۱۹ Data Codeword نهایی:**")
    st.code(" ".join(f"{x:02X}" for x in result["step3"]["data_codewords"]), language=None)

# ---------- گام ۴ ----------
st.header("گام ۴ — Reed-Solomon")
st.markdown("Generator: `01 7F 7A 9A A4 0B 44 75` — GF(256) با `0x11D`")

for s in result["rs_stages"]:
    with st.expander(f"مرحله {s['stage']} — Factor = {s['factor']:02X}"):
        st.write("**Factor:**")
        st.code(f"{s['factor']:02X} = {b8(s['factor'])}", language=None)
        st.write("**ضرب‌ها در Generator:**")
        lines = []
        for i in range(8):
            lines.append(
                f"{s['factor']:02X} × {result['generator'][i]:02X} = {s['products'][i]:02X}"
            )
        st.code("\n".join(lines), language=None)
        st.write("**۸ بایت قبل از XOR:**")
        st.code(" ".join(f"{x:02X}" for x in s["before"]), language=None)
        st.write("**بعد از XOR:**")
        st.code(" ".join(f"{x:02X}" for x in s["after"]), language=None)

        with st.expander("جزئیات ضرب GF(256)"):
            for d in s["details"]:
                st.markdown(
                    f"**{d['factor']:02X} × {d['generator']:02X} = {d['result']:02X}**"
                )
                st.write("حاصل ضرب اولیه:")
                st.code(bvar(d["raw"]), language=None)
                if d["reductions"]:
                    for step in d["reductions"]:
                        st.code(
                            f"{bvar(step['before'])}\n"
                            f"XOR\n"
                            f"{bvar(step['aligned'])}\n"
                            f"----------------\n"
                            f"{bvar(step['after'])}",
                            language=None,
                        )
                st.divider()

st.write("**۷ ECC Codeword:**")
st.code(" ".join(f"{x:02X}" for x in result["ecc"]), language=None)

# ---------- گام ۵ ----------
st.header("گام ۵ — ۲۶ Codeword = ۲۰۸ بیت")
st.code(" ".join(f"{x:02X}" for x in result["all_codewords"]), language=None)
st.success(f"تعداد بیت: {len(result['all_bits'])}")

# ---------- گام ۶ ----------
st.header("گام ۶ — Function Patterns")

def matrix_to_html(m):
    html = '<table style="border-collapse:collapse;direction:ltr;">'
    for r in range(21):
        html += "<tr>"
        for c in range(21):
            v = m[r][c]
            if v is None:
                html += '<td style="width:22px;height:22px;border:1px solid #555;background:#1c2c3f;font-size:9px;text-align:center;color:#888;">·</td>'
            elif v == 1:
                html += '<td style="width:22px;height:22px;border:1px solid #555;background:#000;"></td>'
            else:
                html += '<td style="width:22px;height:22px;border:1px solid #555;background:#fff;"></td>'
        html += "</tr>"
    html += "</table>"
    return html

st.markdown(matrix_to_html(result["function_matrix"]), unsafe_allow_html=True)
st.caption("■ مشکی — □ سفید — · خانه آزاد (داده)")

# ---------- گام ۷ ----------
st.header("گام ۷ — الگوی Zig-Zag")
st.write(f"**تعداد مختصات:** {len(result['coordinates'])}")
st.write("۱۰ مختصات اول:")
st.code(" ".join(f"({r},{c})" for r, c in result["coordinates"][:10]), language=None)
st.write("۱۰ مختصات آخر:")
st.code(" ".join(f"({r},{c})" for r, c in result["coordinates"][-10:]), language=None)

# ---------- گام ۸ ----------
st.header("گام ۸ — شماره‌گذاری ۲۰۸ خانه")

def number_table_html(num_m, bit_m):
    html = '<table style="border-collapse:collapse;direction:ltr;">'
    for r in range(21):
        html += "<tr>"
        for c in range(21):
            n = num_m[r][c]
            if n == 0:
                html += '<td style="width:26px;height:26px;border:1px solid #555;background:#151515;color:#666;font-size:9px;text-align:center;">0</td>'
            else:
                html += f'<td style="width:26px;height:26px;border:1px solid #555;background:#1c2c3f;font-size:9px;text-align:center;color:#fff;">{n}:{bit_m[r][c]}</td>'
        html += "</tr>"
    html += "</table>"
    return html

st.markdown(
    number_table_html(result["number_matrix"], result["bit_matrix"]),
    unsafe_allow_html=True,
)

# ---------- گام ۹ ----------
st.header("گام ۹ — Mask + Format Information + QR نهایی")
st.write(f"**Format Information:** `{result['format_info']:04X}`")

def qr_html(m):
    html = '<table style="border-collapse:collapse;background:#fff;padding:10px;direction:ltr;">'
    for row in m:
        html += "<tr>"
        for v in row:
            color = "#000" if v == 1 else "#fff"
            html += f'<td style="width:12px;height:12px;background:{color};padding:0;"></td>'
        html += "</tr>"
    html += "</table>"
    return html

st.markdown(qr_html(result["final_matrix"]), unsafe_allow_html=True)

# ---------- گام ۱۰ ----------
st.header("گام ۱۰ — مسیر کامل")
st.code(f"""نام ({result['name']})
  ↓
ASCII ({result['step1']['raw_len']} بایت)
  ↓
Byte Mode = 0100
  ↓
Character Count (8 بیت)
  ↓
ASCII Binary ({len(result['step1']['data_bits'])} بیت)
  ↓
Terminator + Align
  ↓
Pad Codewords (0xEC, 0x11)
  ↓
19 Data Codewords
  ↓
Reed-Solomon (GF(256), 0x11D)
  ↓
7 ECC Codewords
  ↓
26 Codewords = 208 Bits
  ↓
Zig-Zag Placement (208 خانه)
  ↓
Mask Pattern 0
  ↓
Format Information = {result['format_info']:04X}
  ↓
Dark Module = 1
  ↓
21 × 21 QR نهایی""", language=None)
