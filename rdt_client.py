# rdt_client.py
import socket
import sys
import time
from utils import (pack_packet, unpack_packet, FLAG_DATA, FLAG_ACK,
                   MAX_PAYLOAD, maybe_lose, maybe_corrupt)

# Ajuste as probabilidades do canal aqui para simular perdas/corrupção no caminho de ida
import utils
utils.LOSS_PROB = 0.1       # ex.: 10% de perda
utils.CORRUPT_PROB = 0.05   # ex.: 5% de corrupção

ALPHA = 0.125   # EWMA para SRTT (Jacobson/Karels style simplificado)
BETA  = 0.25    # EWMA para RTTDEV
INIT_TIMEOUT = 0.2
MIN_TO = 0.05
MAX_TO = 2.0

def log(msg):
    print(f"[CLIENT {time.strftime('%H:%M:%S')}] {msg}", flush=True)

def update_rto(srtt, rttvar, sample):
    if srtt is None:
        # primeira amostra
        srtt = sample
        rttvar = sample / 2
    else:
        rttvar = (1 - BETA) * rttvar + BETA * abs(srtt - sample)
        srtt = (1 - ALPHA) * srtt + ALPHA * sample
    rto = srtt + 4 * rttvar
    rto = max(MIN_TO, min(MAX_TO, rto))
    return srtt, rttvar, rto

def main():
    if len(sys.argv) < 5:
        print("Uso: python rdt_client.py <ip-servidor> <porta-servidor> <bytes_totais> <tamanho_segmento> | tee log_cliente.txt")
        print("Ex.: python rdt_client.py 127.0.0.1 9000 2000000 1000 | tee log_cliente.txt")
        sys.exit(1)

    ip = sys.argv[1]
    port = int(sys.argv[2])
    total_bytes = int(sys.argv[3])
    segsz = min(int(sys.argv[4]), MAX_PAYLOAD)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(INIT_TIMEOUT)

    # estatística
    sent_bytes = 0
    start_t = time.time()

    # EWMA
    srtt = None
    rttvar = None
    rto = INIT_TIMEOUT

    seq = 0
    # gera um buffer de dados para enviar
    data = bytearray(b'A' * total_bytes)

    idx = 0
    while idx < total_bytes:
        chunk = bytes(data[idx: idx + segsz])
        pkt = pack_packet(seq=seq, ack=255, flags=FLAG_DATA, payload=chunk)

        # tentativa de envio/retransmissão
        while True:
            # simula perda/corrupção no envio
            if not maybe_lose():
                wire = maybe_corrupt(pkt)
                sock.sendto(wire, (ip, port))
                log(f"Enviado DATA seq={seq} len={len(chunk)} timeout={rto:.3f}s")
            else:
                log(">> Simulada PERDA de envio DATA")

            t0 = time.time()
            sock.settimeout(rto)

            try:
                raw, _ = sock.recvfrom(65535)
            except socket.timeout:
                log("** TIMEOUT -> Retransmitir")
                # dobra um pouco o timeout para evitar agressividade (backoff leve)
                rto = min(MAX_TO, rto * 1.5)
                continue

            # simula perda/corrupção na volta (lado cliente)
            if maybe_lose():
                log(">> Simulada PERDA de ACK recebido")
                # força retransmissão (sem processar)
                rto = min(MAX_TO, rto * 1.5)
                continue
            raw = maybe_corrupt(raw)

            ackpkt = unpack_packet(raw)
            if ackpkt is None or not (ackpkt["flags"] & FLAG_ACK):
                log("ACK inválido/malformado -> ignora e retransmite")
                rto = min(MAX_TO, rto * 1.5)
                continue

            if not ackpkt["valid"]:
                log("ACK corrompido -> ignora e retransmite")
                rto = min(MAX_TO, rto * 1.5)
                continue

            if ackpkt["ack"] != seq:
                log(f"ACK errado (ack={ackpkt['ack']}!=seq={seq}) -> ignora e retransmite")
                rto = min(MAX_TO, rto * 1.5)
                continue

            # ACK correto
            sample = time.time() - t0
            srtt, rttvar, rto = update_rto(srtt, rttvar, sample)
            log(f"Recebido ACK={ackpkt['ack']} SampleRTT={sample:.4f}s SRTT={srtt:.4f}s RTO={rto:.3f}s")

            sent_bytes += len(chunk)
            idx += len(chunk)
            seq ^= 1
            break  # sai do loop de retransmissão e segue para o próximo bloco

    total_dt = max(1e-9, time.time() - start_t)
    thr_mbps = (sent_bytes * 8) / (total_dt * 1e6)
    log(f"Concluído: {sent_bytes} bytes em {total_dt:.3f}s -> Vazão ~ {thr_mbps:.2f} Mbit/s")

if __name__ == "__main__":
    main()
