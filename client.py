import socket
import hashlib
import struct
import os

CHUNK_SIZE = 1024

def compute_checksum(filename):
    sha256 = hashlib.sha256()
    with open(filename, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
    return sha256.hexdigest()

def send_file(client, filename):
    client.sendall(struct.pack("I", len(filename)) + filename.encode())
    with open(filename, "rb") as f:
        while (chunk := f.read(CHUNK_SIZE)):
            client.sendall(chunk)

def receive_file(client, filename):
    received_chunks = {}
    expected_chunks = 0

    server_checksum = client.recv(64).decode()
    print(f"[CHECKSUM] Received checksum: {server_checksum}")

    while True:
        chunk_header = client.recv(4)
        if not chunk_header:
            break

        chunk_number = struct.unpack("I", chunk_header)[0]
        if chunk_number == -1:
            break  # End of transmission

        chunk_data = client.recv(CHUNK_SIZE)
        received_chunks[chunk_number] = chunk_data
        expected_chunks += 1
    missing_chunks = [i for i in range(expected_chunks) if i not in received_chunks]
    for chunk_number in missing_chunks:
        client.sendall(struct.pack("I", chunk_number))
    for _ in range(len(missing_chunks)):
        chunk_header = client.recv(4)
        chunk_number = struct.unpack("I", chunk_header)[0]
        chunk_data = client.recv(CHUNK_SIZE)
        received_chunks[chunk_number] = chunk_data

        client.sendall(struct.pack("I", -1))
    with open(f"received_{filename}", "wb") as f:
        for i in sorted(received_chunks.keys()):
            f.write(received_chunks[i])
    local_checksum = compute_checksum(f"received_{filename}")
    if local_checksum == server_checksum:
        print(f"[SUCCESS] File {filename} received successfully.")
    else:
        print(f"[ERROR] Checksum mismatch! File may be corrupted.")

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", 5498))

    filename = input("Enter filename to send: ")
    send_file(client, filename)
    receive_file(client, filename)

    client.close()

if __name__ == "__main__":
    main()
