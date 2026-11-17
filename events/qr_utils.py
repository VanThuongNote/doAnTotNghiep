"""
Tiện ích sinh mã QR cục bộ (Offline QR Code Generator) bằng Python + Pillow.
Không phụ thuộc API bên thứ ba (như api.qrserver.com), hoạt động 100% offline.
Chuẩn ISO/IEC 18004 (Byte Mode, Error Correction Level L, Versions 1-10).
"""
import base64
import io
from PIL import Image, ImageDraw

# Bảng thông số cho QR Version 1..10 ở mức sửa lỗi L (Error Correction Level L):
# (total_codewords, ec_codewords_per_block, num_blocks_group1, data_cw_group1, num_blocks_group2, data_cw_group2)
_VERSION_L_PARAMS = {
    1:  (26,   7,  1, 19,  0, 0),
    2:  (44,  10,  1, 34,  0, 0),
    3:  (70,  15,  1, 55,  0, 0),
    4:  (100, 20,  1, 80,  0, 0),
    5:  (134, 26,  1, 108, 0, 0),
    6:  (172, 18,  2, 68,  0, 0),
    7:  (196, 20,  2, 78,  0, 0),
    8:  (242, 24,  2, 97,  0, 0),
    9:  (292, 30,  2, 116, 0, 0),
    10: (346, 18,  2, 68,  2, 69),
}

# Vị trí tâm các Alignment Pattern cho Version 1..10
_ALIGNMENT_POS = {
    1: [],
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
    5: [6, 30],
    6: [6, 34],
    7: [6, 22, 38],
    8: [6, 24, 42],
    9: [6, 26, 46],
    10: [6, 28, 50],
}

# Khởi tạo bảng GF(256) với đa thức nguyên thủy 0x11D
_GF_EXP = [0] * 512
_GF_LOG = [0] * 256
_x = 1
for _i in range(255):
    _GF_EXP[_i] = _x
    _GF_LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _GF_EXP[_i] = _GF_EXP[_i - 255]


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def _rs_generator_poly(nsym: int):
    g = [1]
    for i in range(nsym):
        nxt = [0] * (len(g) + 1)
        factor = _GF_EXP[i]
        for j, coef in enumerate(g):
            nxt[j] ^= coef
            nxt[j + 1] ^= _gf_mul(coef, factor)
        g = nxt
    return g


def _rs_encode(data_bytes, nsym: int):
    gen = _rs_generator_poly(nsym)
    res = list(data_bytes) + [0] * nsym
    for i in range(len(data_bytes)):
        coef = res[i]
        if coef != 0:
            for j in range(1, len(gen)):
                res[i + j] ^= _gf_mul(gen[j], coef)
    return res[len(data_bytes):]


def _choose_version(byte_len: int) -> int:
    for v in range(1, 11):
        _, _, b1, d1, b2, d2 = _VERSION_L_PARAMS[v]
        capacity = b1 * d1 + b2 * d2
        header_bits = 4 + (8 if v <= 9 else 16)
        needed_bytes = (header_bits + byte_len * 8 + 7) // 8
        if needed_bytes <= capacity:
            return v
    raise ValueError("Dữ liệu quá dài cho mã QR (tối đa ~270 bytes).")


def _encode_data_codewords(payload: bytes, version: int):
    _, _, b1, d1, b2, d2 = _VERSION_L_PARAMS[version]
    total_data_cw = b1 * d1 + b2 * d2

    bits = []

    def append_bits(val, length):
        for i in range(length - 1, -1, -1):
            bits.append((val >> i) & 1)

    # Mode indicator: Byte mode = 0100
    append_bits(0b0100, 4)
    # Character count indicator
    count_bits = 8 if version <= 9 else 16
    append_bits(len(payload), count_bits)
    for b in payload:
        append_bits(b, 8)

    # Terminator (tối đa 4 bit 0)
    rem = total_data_cw * 8 - len(bits)
    for _ in range(min(4, rem)):
        bits.append(0)

    # Đệm cho chẵn byte
    while len(bits) % 8 != 0:
        bits.append(0)

    codewords = []
    for i in range(0, len(bits), 8):
        byte_val = 0
        for bit in bits[i:i + 8]:
            byte_val = (byte_val << 1) | bit
        codewords.append(byte_val)

    # Pad bytes 0xEC, 0x11 luân phiên
    pad_Socket = [0xEC, 0x11]
    idx = 0
    while len(codewords) < total_data_cw:
        codewords.append(pad_Socket[idx % 2])
        idx += 1

    return codewords


def _interleave_codewords(data_cw, version: int):
    _, ec_len, b1, d1, b2, d2 = _VERSION_L_PARAMS[version]
    blocks_data = []
    blocks_ec = []
    pos = 0
    for _ in range(b1):
        blk = data_cw[pos:pos + d1]
        pos += d1
        blocks_data.append(blk)
        blocks_ec.append(_rs_encode(blk, ec_len))
    for _ in range(b2):
        blk = data_cw[pos:pos + d2]
        pos += d2
        blocks_data.append(blk)
        blocks_ec.append(_rs_encode(blk, ec_len))

    result = []
    max_d = max(d1, d2)
    for i in range(max_d):
        for blk in blocks_data:
            if i < len(blk):
                result.append(blk[i])
    for i in range(ec_len):
        for ec in blocks_ec:
            result.append(ec[i])
    return result


def _format_info_bits(ec_level_bits: int, mask: int) -> int:
    data = (ec_level_bits << 3) | mask
    rem = data << 10
    poly = 0b10100110111
    for i in range(14, 9, -1):
        if rem & (1 << i):
            rem ^= poly << (i - 10)
    return ((data << 10) | rem) ^ 0b101010000010010


def _build_matrix(version: int, final_codewords, mask: int = 0):
    size = 17 + 4 * version
    matrix = [[None] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]

    def place_finder(r0, c0):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = r0 + dr, c0 + dc
                if 0 <= r < size and 0 <= c < size:
                    if 0 <= dr <= 6 and 0 <= dc <= 6:
                        if dr in (0, 6) or dc in (0, 6) or (2 <= dr <= 4 and 2 <= dc <= 4):
                            matrix[r][c] = 1
                        else:
                            matrix[r][c] = 0
                    else:
                        matrix[r][c] = 0
                    reserved[r][c] = True

    place_finder(0, 0)
    place_finder(0, size - 7)
    place_finder(size - 7, 0)

    # Alignment patterns
    centers = _ALIGNMENT_POS[version]
    for r_c in centers:
        for c_c in centers:
            if reserved[r_c][c_c]:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    r, c = r_c + dr, c_c + dc
                    if max(abs(dr), abs(dc)) in (2, 0):
                        matrix[r][c] = 1
                    else:
                        matrix[r][c] = 0
                    reserved[r][c] = True

    # Timing patterns
    for i in range(8, size - 8):
        val = 1 if i % 2 == 0 else 0
        if not reserved[6][i]:
            matrix[6][i] = val
            reserved[6][i] = True
        if not reserved[i][6]:
            matrix[i][6] = val
            reserved[i][6] = True

    # Dark module & reserve format info areas
    matrix[4 * version + 9][8] = 1
    reserved[4 * version + 9][8] = True

    for i in range(9):
        if i < size:
            reserved[8][i] = True
            reserved[i][8] = True
    for i in range(8):
        reserved[8][size - 1 - i] = True
        reserved[size - 1 - i][8] = True

    # Data bits
    data_bits = []
    for cw in final_codewords:
        for b in range(7, -1, -1):
            data_bits.append((cw >> b) & 1)

    bit_idx = 0
    col = size - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
        row_range = range(size - 1, -1, -1) if upward else range(size)
        for row in row_range:
            for c_off in (0, -1):
                c = col + c_off
                if not reserved[row][c]:
                    bit = data_bits[bit_idx] if bit_idx < len(data_bits) else 0
                    bit_idx += 1
                    if mask == 0 and (row + c) % 2 == 0:
                        bit ^= 1
                    elif mask == 1 and row % 2 == 0:
                        bit ^= 1
                    elif mask == 2 and c % 3 == 0:
                        bit ^= 1
                    matrix[row][c] = bit
        upward = not upward
        col -= 2

    # Format info (EC Level L = 01)
    fmt = _format_info_bits(0b01, mask)
    fmt_bits = [(fmt >> i) & 1 for i in range(15)]  # bit 0..14

    # Đặt các bit Format Info quanh Finder
    coords_tl_row = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
                     (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    for idx_b, (r, c) in enumerate(coords_tl_row):
        matrix[r][c] = fmt_bits[14 - idx_b]

    for idx_b in range(7):
        matrix[size - 1 - idx_b][8] = fmt_bits[14 - idx_b]
    for idx_b in range(7, 15):
        matrix[8][size - 15 + idx_b] = fmt_bits[14 - idx_b]

    return matrix


def generate_qr_Matrix(text: str):
    payload = text.encode('utf-8')
    version = _choose_version(len(payload))
    data_cw = _encode_data_codewords(payload, version)
    final_cw = _interleave_codewords(data_cw, version)
    return _build_matrix(version, final_cw, mask=0)


def generate_qr_base64(text: str, box_size: int = 8, border: int = 3) -> str:
    """
    Sinh ảnh QR code dạng chuỗi Base64 Data URI (data:image/png;base64,...)
    Có thể gán trực tiếp vào <img src="{{ qr_code_data_uri }}">
    """
    matrix = generate_qr_Matrix(text)
    size = len(matrix)
    img_size = (size + border * 2) * box_size
    img = Image.new('RGB', (img_size, img_size), 'white')
    draw = ImageDraw.Draw(img)

    for r in range(size):
        for c in range(size):
            if matrix[r][c]:
                x0 = (c + border) * box_size
                y0 = (r + border) * box_size
                draw.rectangle([x0, y0, x0 + box_size - 1, y0 + box_size - 1], fill='#0f172a')

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return f"data:image/png;base64,{b64}"

