from __future__ import annotations

import hashlib

_Q = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _Q - 2, _Q) % _Q
_I = pow(2, (_Q - 1) // 4, _Q)
_B = (
    15112221349535400772501151409588531511454012693041857206046113283949847762202,
    46316835694926478169428394003475163141307993866256225615783033603165251855960,
)
_IDENTITY = (0, 1)


def _inverse(value: int) -> int:
    return pow(value, _Q - 2, _Q)


def _recover_x(y: int) -> int:
    xx = (y * y - 1) * _inverse((_D * y * y + 1) % _Q) % _Q
    x = pow(xx, (_Q + 3) // 8, _Q)
    if (x * x - xx) % _Q != 0:
        x = (x * _I) % _Q
    if x % 2 != 0:
        x = _Q - x
    return x


def _is_on_curve(point: tuple[int, int]) -> bool:
    x, y = point
    return (-x * x + y * y - 1 - _D * x * x * y * y) % _Q == 0


def _point_add(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
    x1, y1 = left
    x2, y2 = right
    factor = (_D * x1 * x2 * y1 * y2) % _Q
    x3 = ((x1 * y2 + x2 * y1) * _inverse((1 + factor) % _Q)) % _Q
    y3 = ((y1 * y2 + x1 * x2) * _inverse((1 - factor) % _Q)) % _Q
    return x3, y3


def _scalar_mult(point: tuple[int, int], scalar: int) -> tuple[int, int]:
    result = _IDENTITY
    addend = point
    value = int(scalar)
    while value > 0:
        if value & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        value >>= 1
    return result


def _point_encode(point: tuple[int, int]) -> bytes:
    x, y = point
    encoded = bytearray(int(y).to_bytes(32, 'little'))
    encoded[31] |= (x & 1) << 7
    return bytes(encoded)


def _point_decode(data: bytes) -> tuple[int, int]:
    if len(data) != 32:
        raise ValueError('ed25519 points must be 32 bytes')
    encoded = bytearray(data)
    sign = (encoded[31] >> 7) & 1
    encoded[31] &= 0x7F
    y = int.from_bytes(encoded, 'little')
    if y >= _Q:
        raise ValueError('ed25519 point encoding is not canonical')
    x = _recover_x(y)
    if x & 1 != sign:
        x = _Q - x
    point = (x, y)
    if not _is_on_curve(point):
        raise ValueError('ed25519 point is not on the curve')
    return point


def _secret_scalar(seed: bytes) -> tuple[int, bytes]:
    if len(seed) != 32:
        raise ValueError('ed25519 seeds must be 32 bytes')
    digest = hashlib.sha512(seed).digest()
    scalar = int.from_bytes(digest[:32], 'little')
    scalar &= (1 << 254) - 8
    scalar |= 1 << 254
    return scalar, digest[32:]


def public_key_from_seed(seed: bytes) -> bytes:
    scalar, _ = _secret_scalar(seed)
    return _point_encode(_scalar_mult(_B, scalar))


def sign(seed: bytes, message: bytes) -> bytes:
    scalar, prefix = _secret_scalar(seed)
    public_key = _point_encode(_scalar_mult(_B, scalar))
    nonce = int.from_bytes(hashlib.sha512(prefix + message).digest(), 'little') % _L
    encoded_r = _point_encode(_scalar_mult(_B, nonce))
    challenge = int.from_bytes(hashlib.sha512(encoded_r + public_key + message).digest(), 'little') % _L
    s = (nonce + challenge * scalar) % _L
    return encoded_r + int(s).to_bytes(32, 'little')


def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    if len(public_key) != 32 or len(signature) != 64:
        return False
    encoded_r = signature[:32]
    s = int.from_bytes(signature[32:], 'little')
    if s >= _L:
        return False
    try:
        public_point = _point_decode(public_key)
        r_point = _point_decode(encoded_r)
    except ValueError:
        return False
    challenge = int.from_bytes(hashlib.sha512(encoded_r + public_key + message).digest(), 'little') % _L
    left = _scalar_mult(_B, s)
    right = _point_add(r_point, _scalar_mult(public_point, challenge))
    return _scalar_mult(left, 8) == _scalar_mult(right, 8)
