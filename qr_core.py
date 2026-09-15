# ============================================================
# qr_core.py  —  منطق ساخت QR Version 1-L
# ============================================================

QR_SIZE = 21
DATA_CODEWORDS = 19
ECC_CODEWORDS = 7
TOTAL_CODEWORDS = 26
TOTAL_DATA_BITS = 208

GF_POLY = 0x11D
GENERATOR = [0x01, 0x7F, 0x7A, 0x9A, 0xA4, 0x0B, 0x44, 0x75]
EC_LEVEL_BITS = 0b01
MASK_PATTERN = 0


def b8(n):
    return format(n & 0xFF, "08b")


def bvar(n):
    return bin(n)[2:] if n else "0"


def bits_to_bytes(bits):
    result = []
    for i in range(0, len(bits), 8):
        value = 0
        for bit in bits[i:i + 8]:
            value = (value << 1) | bit
        result.append(value)
    return result


# ---------- GF(256) ----------
def gf_mul_trace(a, b):
    raw = 0
    for i in range(8):
        if (b >> i) & 1:
            raw ^= a << i
    reduction_steps = []
    value = raw
    while value.bit_length() > 8:
        shift = value.bit_length() - GF_POLY.bit_length()
        aligned = GF_POLY << shift
        before = value
        value ^= aligned
        reduction_steps.append({"before": before, "aligned": aligned, "after": value})
    return raw, reduction_steps, value


def gf_mul(a, b):
    return gf_mul_trace(a, b)[2]


# ---------- گام ۱ ----------
def step1_text_to_bits(name):
    if not name:
        raise ValueError("نام خالی است.")
    name = name.upper()
    try:
        raw = name.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("فقط حروف انگلیسی، عدد، فاصله و ASCII مجاز است.")
    if len(raw) > 17:
        raise ValueError("QR Version 1-L حداکثر ۱۷ بایت داده دارد.")

    mode_bits = [0, 1, 0, 0]
    count = len(raw)
    count_bits = [(count >> i) & 1 for i in range(7, -1, -1)]

    per_char = []
    data_bits = []
    for byte in raw:
        bits = [(byte >> i) & 1 for i in range(7, -1, -1)]
        per_char.append({"char": chr(byte), "hex": f"{byte:02X}", "bits": bits})
        data_bits.extend(bits)

    all_bits = mode_bits + count_bits + data_bits
    return {
        "name": name, "raw_len": len(raw),
        "mode_bits": mode_bits, "count": count, "count_bits": count_bits,
        "per_char": per_char, "data_bits": data_bits,
        "all_bits": all_bits, "bit_length": len(all_bits),
    }


# ---------- گام ۲ ----------
def step2_terminator_and_align(bits):
    budget = DATA_CODEWORDS * 8
    work = bits[:]
    remaining = budget - len(work)
    terminator_len = min(4, remaining) if remaining > 0 else 0
    terminator = [0] * terminator_len
    work.extend(terminator)

    align_pad = []
    while len(work) % 8 != 0:
        work.append(0)
        align_pad.append(0)

    return {
        "budget": budget, "terminator": terminator,
        "align_pad": align_pad, "bits": work, "bit_length": len(work),
    }


# ---------- گام ۳ ----------
def step3_pad_codewords(bits):
    data_bytes = bits_to_bytes(bits)
    initial_codewords = data_bytes[:]
    pad_added = []
    pad_cycle = [0xEC, 0x11]
    idx = 0
    while len(data_bytes) < DATA_CODEWORDS:
        b = pad_cycle[idx % 2]
        data_bytes.append(b)
        pad_added.append(b)
        idx += 1
    return {
        "initial_codewords": initial_codewords,
        "pad_added": pad_added,
        "data_codewords": data_bytes,
    }


# ---------- گام ۴ ----------
def reed_solomon_trace(data):
    work = data[:] + [0] * ECC_CODEWORDS
    stages = []
    for i in range(len(data)):
        factor = work[i]
        before_window = work[i:i + 8]
        products = [gf_mul(factor, g) for g in GENERATOR]
        after_window = [before_window[j] ^ products[j] for j in range(8)]
        for j in range(8):
            work[i + j] ^= products[j]

        details = []
        for g in GENERATOR:
            raw, reductions, result = gf_mul_trace(factor, g)
            details.append({
                "factor": factor, "generator": g,
                "raw": raw, "reductions": reductions, "result": result,
            })
        stages.append({
            "stage": i + 1, "factor": factor,
            "before": before_window, "products": products,
            "after": after_window, "details": details,
        })
    ecc = work[-ECC_CODEWORDS:]
    return ecc, stages


# ---------- گام ۵ ----------
def codewords_to_bits(codewords):
    bits = []
    for byte in codewords:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


# ---------- گام ۶ ----------
def get_format_copy1():
    return [
        (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5),
        (8, 7), (8, 8),
        (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8),
    ]


def get_format_copy2():
    return [
        (20, 8), (19, 8), (18, 8), (17, 8), (16, 8), (15, 8),
        (14, 8), (13, 8),
        (8, 20), (8, 19), (8, 18), (8, 17), (8, 16), (8, 15), (8, 14),
    ]


def create_function_matrix():
    matrix = [[None] * QR_SIZE for _ in range(QR_SIZE)]
    for r0, c0 in [(0, 0), (0, QR_SIZE - 8), (QR_SIZE - 8, 0)]:
        for r in range(r0, r0 + 8):
            for c in range(c0, c0 + 8):
                matrix[r][c] = 0
    for r0, c0 in [(0, 0), (0, QR_SIZE - 7), (QR_SIZE - 7, 0)]:
        for r in range(7):
            for c in range(7):
                black = (r == 0 or r == 6 or c == 0 or c == 6
                         or (2 <= r <= 4 and 2 <= c <= 4))
                matrix[r0 + r][c0 + c] = 1 if black else 0
    for c in range(8, 13):
        matrix[6][c] = 1 if (c % 2 == 0) else 0
    for r in range(8, 13):
        matrix[r][6] = 1 if (r % 2 == 0) else 0
    for (r, c) in get_format_copy1():
        matrix[r][c] = 0
    for (r, c) in get_format_copy2():
        matrix[r][c] = 0
    matrix[13][8] = 1
    return matrix


# ---------- گام ۷ ----------
def get_data_coordinates(function_matrix):
    coordinates = []
    direction = -1
    col = QR_SIZE - 1
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(QR_SIZE - 1, -1, -1) if direction == -1 else range(0, QR_SIZE)
        for row in rows:
            for c in (col, col - 1):
                if function_matrix[row][c] is None:
                    coordinates.append((row, c))
        col -= 2
        direction *= -1
    return coordinates


# ---------- گام ۸ ----------
def build_raw_map(data_bits, coordinates):
    number_matrix = [[0] * QR_SIZE for _ in range(QR_SIZE)]
    bit_matrix = [[None] * QR_SIZE for _ in range(QR_SIZE)]
    for index, ((r, c), bit) in enumerate(zip(coordinates, data_bits), start=1):
        number_matrix[r][c] = index
        bit_matrix[r][c] = bit
    return number_matrix, bit_matrix


# ---------- گام ۹ ----------
def bch_remainder(value, polynomial):
    while value.bit_length() >= polynomial.bit_length():
        shift = value.bit_length() - polynomial.bit_length()
        value ^= polynomial << shift
    return value


def format_information():
    data = (EC_LEVEL_BITS << 3) | MASK_PATTERN
    remainder = bch_remainder(data << 10, 0x537)
    return ((data << 10) | remainder) ^ 0x5412


def mask_bit(row, col):
    return (row + col) % 2 == 0


def place_format_information(matrix):
    bits = format_information()
    copy1 = get_format_copy1()
    copy2 = get_format_copy2()
    for i in range(15):
        bit = (bits >> i) & 1
        r1, c1 = copy1[i]
        r2, c2 = copy2[i]
        matrix[r1][c1] = bit
        matrix[r2][c2] = bit
    matrix[13][8] = 1
    return matrix


def build_final_matrix(function_matrix, coordinates, data_bits):
    matrix = [row[:] for row in function_matrix]
    for (r, c), bit in zip(coordinates, data_bits):
        value = bit
        if mask_bit(r, c):
            value ^= 1
        matrix[r][c] = value
    matrix = place_format_information(matrix)
    return matrix


# ---------- PIPELINE ----------
def calculate(name):
    s1 = step1_text_to_bits(name)
    s2 = step2_terminator_and_align(s1["all_bits"])
    s3 = step3_pad_codewords(s2["bits"])
    ecc, rs_stages = reed_solomon_trace(s3["data_codewords"])

    all_codewords = s3["data_codewords"] + ecc
    all_bits = codewords_to_bits(all_codewords)

    function_matrix = create_function_matrix()
    coordinates = get_data_coordinates(function_matrix)
    number_matrix, bit_matrix = build_raw_map(all_bits, coordinates)
    final_matrix = build_final_matrix(function_matrix, coordinates, all_bits)

    return {
        "name": s1["name"],
        "step1": s1,
        "step2": s2,
        "step3": s3,
        "ecc": ecc,
        "rs_stages": rs_stages,
        "generator": GENERATOR,
        "all_codewords": all_codewords,
        "all_bits": all_bits,
        "function_matrix": function_matrix,
        "coordinates": coordinates,
        "number_matrix": number_matrix,
        "bit_matrix": bit_matrix,
        "final_matrix": final_matrix,
        "format_info": format_information(),
    }
