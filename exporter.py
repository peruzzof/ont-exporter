#!/usr/bin/env python3
"""
Huawei ONT Exporter — Prometheus metrics endpoint for HG8010H optical terminals.

Connects via Telnet, runs ``display optic``, and exposes metrics on :9222.

Configuration (environment variables)
--------------------------------------
* ONT_HOST        – ONT IP address (default: 192.168.100.1)
* ONT_PORT        – Telnet port  (default: 23)
* ONT_USER        – Telnet username
* ONT_PASSWORD    – Telnet password
* METRICS_PORT    – HTTP listen port (default: 9222)
* SCRAPE_TIMEOUT  – Telnet read timeout in seconds (default: 8)
* CACHE_SECONDS   – Seconds to cache scraped values (default: 30)
"""

import socket, time, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Lock

ONT_HOST = os.getenv("ONT_HOST", "192.168.100.1")
ONT_PORT = int(os.getenv("ONT_PORT", "23"))
ONT_USER = os.getenv("ONT_USER", "")
ONT_PASS = os.getenv("ONT_PASSWORD", "")
METRICS_PORT = int(os.getenv("METRICS_PORT", "9222"))
SCRAPE_TIMEOUT = int(os.getenv("SCRAPE_TIMEOUT", "8"))
CACHE_SECONDS = int(os.getenv("CACHE_SECONDS", "30"))

_cache: dict = {}
_cache_lock = Lock()
_cache_time: float = 0


def telnet_cmd(cmd: str) -> str:
    """Connect, login, run *cmd*, return output."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(SCRAPE_TIMEOUT)
    try:
        s.connect((ONT_HOST, ONT_PORT))
        s.recv(4096)
        s.send(f"{ONT_USER}\n".encode())
        time.sleep(0.2)
        s.recv(4096)
        s.send(f"{ONT_PASS}\n".encode())
        time.sleep(0.3)
        s.recv(4096)

        s.send(f"{cmd}\n".encode())
        time.sleep(0.3)
        data = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"WAP>" in data or b"success!" in data.lower():
                break
        return data.decode("utf-8", errors="replace")
    except Exception as exc:
        return f"ERROR: {exc}"
    finally:
        s.close()


def parse_optical(raw: str) -> dict:
    """Parse ``Key : Value`` lines from *display optic* output."""
    result: dict = {}
    for line in raw.split("\n"):
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        # Strip trailing unit hints (dBm), (mV), (mA), (C), etc.
        if "(" in val:
            val = val[: val.index("(")].strip()
        try:
            result[key] = float(val) if "." in val else int(val)
        except ValueError:
            result[key] = val
    return result


def scrape() -> str:
    """Scrape ONT and return Prometheus text."""
    global _cache, _cache_time

    with _cache_lock:
        now = time.time()
        if _cache and (now - _cache_time) < CACHE_SECONDS:
            return _cache

        optic = parse_optical(telnet_cmd("display optic"))

        def _add(name: str, value, help_text: str) -> None:
            lines.append(f"# HELP ont_{name} {help_text}")
            lines.append(f"# TYPE ont_{name} gauge")
            lines.append(f"ont_{name} {value}")

        lines: list[str] = []
        _add("rx_power_dbm", optic.get("RxPower", 0), "Optical receiver power in dBm")
        _add("tx_power_dbm", optic.get("TxPower", 0), "Optical transmitter power in dBm")
        _add("voltage_mv", optic.get("Voltage", 0), "Optical module voltage in mV")
        _add("bias_ma", optic.get("Bias", 0), "Optical module bias current in mA")
        _add("temperature_c", optic.get("Temperature", 0), "Optical module temperature in Celsius")
        _add("link_status", 1 if optic.get("LinkStatus") == "ok" else 0, "Optical link status (1=ok, 0=fail)")

        lines.append(f"# HELP ont_scrape_duration_ms Time to scrape ONT")
        lines.append(f"# TYPE ont_scrape_duration_ms gauge")
        lines.append(f"ont_scrape_duration_ms {int((time.time() - now) * 1000)}")

        _cache = "\n".join(lines) + "\n"
        _cache_time = time.time()
        return _cache


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/metrics":
            try:
                data = scrape()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.end_headers()
                self.wfile.write(data.encode())
            except Exception as exc:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"ERROR: {exc}\n".encode())
        elif self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress default access log


if __name__ == "__main__":
    import sys
    print(f"ONT exporter listening on :{METRICS_PORT}", flush=True)
    server = HTTPServer(("0.0.0.0", METRICS_PORT), MetricsHandler)
    server.serve_forever()
