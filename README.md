# 📡 Implementação do RDT 3.0 (Stop-and-Wait)

Este projeto implementa o **RDT 3.0 (Reliable Data Transfer)** utilizando o protocolo **Stop-and-Wait** sobre **UDP**, simulando um canal não confiável com **perda e corrupção de pacotes**.

O cliente envia dados de forma confiável para o servidor, que os confirma com ACKs.  
A confiabilidade é garantida através de **números de sequência (0/1)**, **verificação de integridade (checksum)** e **retransmissões controladas por timeout adaptativo (EWMA de RTT)**.

---

## 🧠 Conceitos Implementados

- **Camada de Transporte Confiável (RDT 3.0)**:
  - Parada e Espera (Stop-and-Wait);
  - Controle de duplicatas (seq = 0 / 1);
  - Checksum 16 bits estilo Internet (RFC 1071);
  - Detecção e descarte de pacotes corrompidos;
  - Retransmissão em caso de timeout;
  - Timeout dinâmico com **EWMA de RTT** (`RTO = SRTT + 4·RTTDEV`);
  - Simulação de **perdas** e **corrupções** configuráveis.

---

## 🗂 Estrutura do Projeto

## 📁 utils.py

- Define o **formato do pacote** (cabeçalho + payload);
- Implementa o **checksum 16-bit**;
- Funções de empacotamento/desempacotamento (`pack_packet`, `unpack_packet`);
- Simula **perda** e **corrupção de pacotes** via `LOSS_PROB` e `CORRUPT_PROB`.

---

## 💾 rdt_server.py

- Implementa a **FSM do receptor** (espera DATA, entrega em ordem, envia ACK);
- Detecta e descarta pacotes corrompidos;
- Reenvia ACKs em caso de duplicatas;
- Mede vazão e exibe logs de recepção.

---

## 🚀 rdt_client.py

- Implementa a **FSM do emissor** (envia DATA, espera ACK, retransmite em timeout);
- Mede **RTT** e ajusta o **RTO adaptativamente** com EWMA;
- Simula perdas e corrupções no envio/recebimento;
- Calcula **vazão final** e exibe logs detalhados de ACKs, retransmissões e tempos.

---

## ⚙️ Como Executar

### 1️⃣ Requisitos

- Python 3.8 ou superior
- Executar em terminais separados (cliente e servidor)

---

### 2️⃣ Execução

##### Terminal 1 — Servidor

```bash
python rdt_server.py 127.0.0.1 9000
```

##### Terminal 2 — Cliente
Envie 1 KB em blocos de 1000 bytes:

```bash
python rdt_client.py 127.0.0.1 9000 1000 1000
```

## 🧩 Parâmetros

### Cliente:

```bash
python rdt_client.py <ip-servidor> <porta-servidor> <bytes_totais> <tamanho_segmento> | tee log_cliente.txt
```
### Servidor:

```bash
python rdt_server.py <ip> <porta> | tee log_servidor.txt

```
### Configuração de Perda e Corrupção de Pacotes:

Edite no topo de rdt_client.py e/ou rdt_server.py:

```bash
utils.LOSS_PROB = 0.1        # 10% de perda
utils.CORRUPT_PROB = 0.05    # 5% de corrupção
```