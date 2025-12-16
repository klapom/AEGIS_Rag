# TD-061: Ollama Container GPU-Zugriff auf DGX Spark

**Status:** RESOLVED
**Priority:** Critical
**Created:** 2025-12-10
**Resolved:** 2025-12-10
**Sprint:** 42

## Problem

Der Ollama Container hatte keinen GPU-Zugriff, obwohl die docker-compose.yml korrekt konfiguriert war. Modelle liefen auf CPU statt GPU.

### Symptome

```bash
# Im Container:
docker exec aegis-ollama nvidia-smi
# → "Failed to initialize NVML: Unknown Error"

docker exec aegis-ollama ollama ps
# → NAME         SIZE     PROCESSOR
# → qwen3:32b    21 GB    100% CPU     ← Problem!
```

### Auswirkung

- **qwen3:32b** (21GB) lief auf CPU → 28GB RAM Verbrauch
- Extreme Latenz (CPU-Inferenz ~10x langsamer)
- 96% GPU-Util Anzeige war irreführend (kein echter GPU-Prozess)

## Ursache

Docker war nicht für den NVIDIA Container Runtime konfiguriert. Obwohl `nvidia-container-toolkit` installiert war, fehlte die `/etc/docker/daemon.json` Konfiguration.

Die docker-compose.yml hatte korrekte GPU-Reservierungen:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          capabilities: [gpu]
```

Aber Docker wusste nicht, wie es diese verarbeiten soll.

## Lösung

### 1. Als root einloggen
```bash
sudo -i
```

### 2. Docker für NVIDIA Runtime konfigurieren
```bash
nvidia-ctk runtime configure --runtime=docker
```

Dies erstellt `/etc/docker/daemon.json`:
```json
{
    "runtimes": {
        "nvidia": {
            "args": [],
            "path": "nvidia-container-runtime"
        }
    }
}
```

### 3. Docker neustarten
```bash
systemctl daemon-reload  # Falls Warning erscheint
systemctl restart docker
```

### 4. Ollama Container neu starten
```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag
docker compose -f docker-compose.dgx-spark.yml up -d ollama
```

### 5. Verifizieren
```bash
# GPU im Container sichtbar?
docker exec aegis-ollama nvidia-smi
# → Sollte GPU anzeigen

# Modell auf GPU?
docker exec aegis-ollama ollama ps
# → NAME         SIZE     PROCESSOR
# → qwen3:32b    21 GB    100% GPU     ← Erfolg!
```

## Ergebnis nach Fix

| Metrik | Vorher (CPU) | Nachher (GPU) |
|--------|--------------|---------------|
| Processor | 100% CPU | 100% GPU |
| RAM Verbrauch | ~28GB | ~2GB |
| VRAM Verbrauch | 0 | 21GB |
| Latenz pro Anfrage | ~20s | ~3-5s |

## Prävention

Bei Neuinstallation von DGX Spark oder Docker:

1. Nach Docker-Installation immer ausführen:
   ```bash
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

2. Verifizieren mit:
   ```bash
   docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
   ```

## Betroffene Komponenten

- `/etc/docker/daemon.json` - Neu erstellt
- `aegis-ollama` Container - Neustart erforderlich
- Alle GPU-abhängigen Modelle (qwen3:32b, qwen3-vl:32b, bge-m3)

## Referenzen

- [NVIDIA Container Toolkit Installation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- [Docker GPU Support](https://docs.docker.com/config/containers/resource_constraints/#gpu)
- DGX Spark Dokumentation
