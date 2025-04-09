# test_stdin.py
import sys

count = 0
while True:
    chunk = sys.stdin.buffer.read(1024)
    if not chunk:
        print("Fin du flux.")
        break
    count += len(chunk)
    if count % (1024*1024) < 1024:
        print(f"Déjà lu ~{count/1024/1024:.1f} MB ...")