# ont-exporter

Prometheus metrics exporter for Huawei HG8010H optical terminals (ONTs) via Telnet.

## Usage

```bash
docker run -p 9222:9222 \
  -e ONT_HOST=192.168.100.1 \
  -e ONT_USER=admin \
  -e ONT_PASSWORD=your_password \
  ghcr.io/peruzzo/ont-exporter:latest
```

## Metrics

| Metric                | Description                      |
|-----------------------|----------------------------------|
| `ont_rx_power_dbm`    | Optical receiver power (dBm)     |
| `ont_tx_power_dbm`    | Optical transmitter power (dBm)  |
| `ont_voltage_mv`      | Optical module voltage (mV)      |
| `ont_bias_ma`         | Bias current (mA)                |
| `ont_temperature_c`   | Module temperature (°C)          |
| `ont_link_status`     | 1 = ok, 0 = fail                 |
| `ont_scrape_duration_ms` | Time to scrape (ms)           |

## Environment Variables

| Variable         | Default         | Description             |
|------------------|-----------------|-------------------------|
| `ONT_HOST`       | `192.168.100.1` | ONT IP address          |
| `ONT_PORT`       | `23`            | Telnet port             |
| `ONT_USER`       | (required)      | Telnet username         |
| `ONT_PASSWORD`   | (required)      | Telnet password         |
| `METRICS_PORT`   | `9222`          | HTTP listen port        |
| `SCRAPE_TIMEOUT` | `8`             | Telnet timeout (s)      |
| `CACHE_SECONDS`  | `30`            | Metrics cache TTL (s)   |

## Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ont-exporter
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ont-exporter
  template:
    metadata:
      labels:
        app: ont-exporter
    spec:
      hostNetwork: true
      containers:
        - name: exporter
          image: ghcr.io/peruzzo/ont-exporter:latest
          ports:
            - containerPort: 9222
              name: metrics
          env:
            - name: ONT_HOST
              value: "192.168.100.1"
            - name: ONT_USER
              valueFrom:
                secretKeyRef:
                  name: ont-credentials
                  key: ONT_USER
            - name: ONT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: ont-credentials
                  key: ONT_PASSWORD
```

## License

MIT
