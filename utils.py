# utils.py
import random
import struct

# ----- Configurações do canal (edite no cliente/servidor antes de importar se quiser) -----
LOSS_PROB = 0.0         # probabilidade de "perder" pacote (não enviar/entregar)
CORRUPT_PROB = 0.0      # probabilidade de corromper bits do pacote entregue
MAX_PAYLOAD = 1024

# Cabeçalho: seq(1), ack(1), flags(1), len(2), cksum(2) = 7 bytes
HDR_FMT = "!BBBHH"
HDR_LEN = struct.calcsize(HDR_FMT)
FLAG_ACK = 0x01
FLAG_DATA = 0x02
FLAG_FIN = 0x04

def internet_checksum(data: bytes) -> int:
    """Checksum 16-bit estilo Internet (RFC 1071)."""
    if len(data) % 2 == 1:
        data += b"\x00"
    s = 0
    for i in range(0, len(data), 2):
        w = (data[i] << 8) + data[i+1]
        s += w
        s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF

def pack_packet(seq: int, ack: int, flags: int, payload: bytes) -> bytes:
    if payload is None:
        payload = b""
    plen = len(payload)
    hdr_wo_ck = struct.pack(HDR_FMT, seq & 1, ack & 1, flags & 0xFF, plen, 0)
    cks = internet_checksum(hdr_wo_ck + payload)
    hdr = struct.pack(HDR_FMT, seq & 1, ack & 1, flags & 0xFF, plen, cks)
    return hdr + payload

def unpack_packet(pkt: bytes):
    if len(pkt) < HDR_LEN:
        return None
    seq, ack, flags, plen, cks = struct.unpack(HDR_FMT, pkt[:HDR_LEN])
    payload = pkt[HDR_LEN:HDR_LEN+plen]
    # valida comprimento
    if len(payload) != plen:
        return None
    # valida checksum
    hdr_wo_ck = struct.pack(HDR_FMT, seq, ack, flags, plen, 0)
    ok = internet_checksum(hdr_wo_ck + payload) == cks
    return {
        "seq": seq, "ack": ack, "flags": flags,
        "len": plen, "checksum": cks, "payload": payload,
        "valid": ok
    }

def maybe_lose() -> bool:
    return random.random() < LOSS_PROB

def maybe_corrupt(data: bytes) -> bytes:
    if random.random() >= CORRUPT_PROB or len(data) == 0:
        return data
    # corrompe um byte aleatório
    i = random.randrange(len(data))
    # flip em 1 bit
    b = data[i] ^ (1 << random.randrange(8))
    return data[:i] + bytes([b]) + data[i+1:]
