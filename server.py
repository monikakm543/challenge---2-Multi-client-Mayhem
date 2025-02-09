import socket
import threading
import hashlib
import os
import random
import struct

CHUNK_SIZE = 1024
PACKET_LOSS_PROBABILITY = 0.1  # 10% chance of packet drop
PACKET_CORRUPTION_PROBABILITY = 0.05  # 5% chance of corruption

def compute_checksum(filename):
    sha256 = hashlib.sha256()
    with open(filename, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
    return sha256.hexdigest()

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    filename_size = struct.unpack("I", conn.recv(4))[0]
    filename = conn.recv(filename_size).decode()
    with open(f"server_{filename}", "wb") as f:
        while True:
            data = conn.recv(CHUNK_SIZE)
            if not data:
                break
            f.write(data)
    print(f"[RECEIVED] {filename} from {addr}")
    checksum = compute_checksum(f"server_{filename}")
    conn.sendall(checksum.encode())  # Send checksum
    with open(f"server_{filename}", "rb") as f:
        chunk_number = 0
        while (chunk := f.read(CHUNK_SIZE)):
            # Introduce artificial packet loss or corruption
            if random.random() < PACKET_LOSS_PROBABILITY:
                print(f"[LOSS] Dropped chunk {chunk_number}")
                chunk_number += 1
                continue
            if random.random() < PACKET_CORRUPTION_PROBABILITY:
                print(f"[CORRUPTION] Corrupting chunk {chunk_number}")
                chunk = b"X" * len(chunk)  # Corrupt data

            # Send chunk with sequence number
            conn.sendall(struct.pack("I", chunk_number) + chunk)
            chunk_number += 1
    conn.sendall(struct.pack("I", -1))
    while True:
        missing_chunk_data = conn.recv(8)
        if not missing_chunk_data:
            break
        missing_chunk_number = struct.unpack("I", missing_chunk_data[:4])[0]
        if missing_chunk_number == -1:
            break 
        print(f"[RETRANSMIT] Resending chunk {missing_chunk_number}")
        with open(f"server_{filename}", "rb") as f:
            f.seek(missing_chunk_number * CHUNK_SIZE)
            chunk = f.read(CHUNK_SIZE)
            conn.sendall(struct.pack("I", missing_chunk_number) + chunk)
    print(f"[DONE] File {filename} sent successfully to {addr}")
    conn.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5498))
    server.listen(5)
    print("[SERVER STARTED] Waiting for connections...")

    while True:
        conn, addr = server.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()

if __name__ == "__main__":
    main()
