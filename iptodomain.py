import csv
import datetime
import ipaddress
import socket
import threading
import time
import requests
from queue import Queue
from tqdm import tqdm

# configuration
PROXIES_FILE = "proxies.txt"
MAX_WORKERS = 10
MAX_RETRIES = 3
WAIT_TIME = 2
RESULTS_FILE = "results.csv"

# initialize queues
ips_queue = Queue()

# load proxies from file
proxies = []
with open(PROXIES_FILE, "r") as f:
    for line in f:
        proxy = line.strip()
        if proxy:
            proxies.append(proxy)

# initialize results
results = []

# lock for writing to file
results_lock = threading.Lock()

# function to check IP
def check_ip(ip):
    try:
        if ipaddress.ip_address(ip).is_private:
            return
        response = requests.get(f"http://{ip}", proxies=get_proxy())
        if response.status_code < 400:
            domain = socket.gethostbyaddr(ip)[0]
            with results_lock:
                results.append((ip, domain, "VALID"))
        else:
            with results_lock:
                results.append((ip, "", "INVALID"))
    except:
        with results_lock:
            results.append((ip, "", "ERROR"))

# function to get a proxy from the list
def get_proxy():
    return {"http": "http://" + proxies.pop(0)}

# function to run a worker
def run_worker():
    while True:
        item = ips_queue.get()
        if item is None:
            break
        check_ip(item)
        ips_queue.task_done()

# initialize workers
workers = []
for i in range(MAX_WORKERS):
    t = threading.Thread(target=run_worker)
    t.start()
    workers.append(t)

# loop over IPs
pbar = tqdm(total=2**32)
for i in range(2**32):
    ip = str(ipaddress.IPv4Address(i))
    ips_queue.put(ip)
    pbar.update(1)
    while ips_queue.qsize() >= MAX_WORKERS:
        time.sleep(WAIT_TIME)

# wait for workers to finish
for i in range(MAX_WORKERS):
    ips_queue.put(None)
for t in workers:
    t.join()

# write results to file
now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"{now}_{RESULTS_FILE}"
with open(filename, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["IP", "Domain", "Status"])
    for result in results:
        writer.writerow(result)

print(f"Results written to file: {filename}")
