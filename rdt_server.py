# rdt_server.py
import socket
import sys
import time
from utils import (unpack_packet, pack_packet, FLAG_ACK, FLAG_DATA,
                   HDR_LEN, maybe_lose, maybe_corrupt)

# Ajuste as probabilidades do canal aqui se quiser testar do lado do servidor
import utils
utils.LOSS_PROB = 0.0
utils.CORRUPT_PROB = 0.0

def log(msg, save_log=False):
    print(f"[SERVER {time.strftime('%H:%M:%S')}] {msg}", flush=True)

def main():
    if len(sys.argv) < 3:
        print("Uso: python rdt_server.py <ip> <porta>")
        print("Ex.: python rdt_server.py 127.0.0.1 9000")
        sys.exit(1)

    ip = sys.argv[1]
    port = int(sys.argv[2])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))
    sock.settimeout(1.0)

    expected_seq = 0
    received_bytes = 0
    start_t = None
    app_buffer = bytearray()

    log(f"Escutando em {ip}:{port}")
    client_addr = None

    while True:
        try:
            data, addr = sock.recvfrom(65535)
        except socket.timeout:
            # loop; servidor é passivo
            continue

        # aplica perda/corrupção no lado receptor para simular canal no caminho de volta
        if maybe_lose():
            log(">> Simulada PERDA de pacote de entrada")
            continue
        data = maybe_corrupt(data)

        pkt = unpack_packet(data)
        if pkt is None:
            log(">> Pacote malformado (sem ACK). DESCARTA")
            continue

        if pkt["flags"] & FLAG_DATA:
            if not pkt["valid"]:
                log(f">> DATA corrompido (seq={pkt['seq']}). DESCARTA")
                continue

            client_addr = addr
            if start_t is None:
                start_t = time.time()

            if pkt["seq"] == expected_seq:
                # entrega à aplicação
                app_buffer.extend(pkt["payload"])
                received_bytes += pkt["len"]
                log(f"Recebido DATA seq={pkt['seq']} len={pkt['len']} (entregue). Total={received_bytes}B")

                # envia ACK desse seq
                ackpkt = pack_packet(seq=0, ack=pkt["seq"], flags=FLAG_ACK, payload=b"")
                # simula perda/corrupção no envio do ACK
                if not maybe_lose():
                    out = maybe_corrupt(ackpkt)
                    sock.sendto(out, client_addr)
                    log(f"Enviado ACK={pkt['seq']}")
                else:
                    log(">> Simulada PERDA de ACK")

                expected_seq ^= 1  # alterna 0/1

            else:
                # duplicata: reenvia ACK do último entregado (que é o oposto do esperado)
                last_good = expected_seq ^ 1
                ackpkt = pack_packet(seq=0, ack=last_good, flags=FLAG_ACK, payload=b"")
                if not maybe_lose():
                    out = maybe_corrupt(ackpkt)
                    sock.sendto(out, client_addr)
                    log(f"Recebido DUPLICATA seq={pkt['seq']} -> Reenviei ACK={last_good}")
                else:
                    log(">> Simulada PERDA de ACK (duplicata)")

        else:
            # não é DATA; ignore ou trate FIN conforme desejar
            pass

        # estatística simples
        if start_t and received_bytes >= 1024*1024:  # quando chegar a 1MB, mostra taxa e limpa contador
            dt = max(1e-9, time.time() - start_t)
            thr_mbps = (received_bytes * 8) / (dt * 1e6)
            log(f"[Parcial] Vazão ~ {thr_mbps:.2f} Mbit/s (1MB recebido)")
            start_t = time.time()
            received_bytes = 0

if __name__ == "__main__":
    main()
