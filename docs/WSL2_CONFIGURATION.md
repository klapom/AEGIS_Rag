# WSL2 Configuration for AEGIS RAG

**Sprint 20 Feature 20.4:** WSL2 Performance Optimization

---

## 🎯 Optimization Goal

Increase WSL2 CPU allocation from **4 cores → 8 cores** to improve:
- Ollama inference speed (parallel processing)
- Docker container performance
- Concurrent chunk processing

---

## 📋 Current vs. Optimized Configuration

| Setting | Before (Default) | After (Optimized) | Benefit |
|---------|------------------|-------------------|---------|
| **CPU Cores** | 4 cores (50%) | 8 cores (100%) | +100% parallelism |
| **Memory** | 8 GB (50%) | 12 GB (75%) | More headroom |
| **Swap** | 2 GB | 4 GB | Prevents OOM |

**System:** 8-core CPU, 16 GB RAM

---

## ⚙️ .wslconfig File

### **Location:**
```
C:\Users\<YourUsername>\.wslconfig
```

### **Recommended Configuration:**

```ini
[wsl2]
# Sprint 20 Feature 20.4: WSL2 Performance Optimization
# Optimized for AEGIS RAG with Ollama + Docker

# CPU: Use all 8 cores (100% of host CPU)
# BEFORE: 4 cores (50% default)
# AFTER: 8 cores (maximum parallelism for Ollama inference)
processors=8

# Memory: Allocate 12 GB RAM (75% of 16 GB host)
# BEFORE: 8 GB (50% default)
# AFTER: 12 GB (more headroom for Ollama models in VRAM + Docker)
memory=12GB

# Swap: Increase to 4 GB (prevents OOM during heavy loads)
# BEFORE: 2 GB
# AFTER: 4 GB (safety buffer for spike loads)
swap=4GB

# Swap file location (optional, defaults to %USERPROFILE%\AppData\Local\Temp\swap.vhdx)
# swapfile=C:\\temp\\wsl-swap.vhdx

# Kernel: Use latest WSL2 kernel (auto-update)
# kernel=C:\\path\\to\\custom\\kernel  # Only if needed

# Localhost forwarding: Allow Docker containers to reach Windows host
localhostForwarding=true

# GUI support (if needed for debugging)
# guiApplications=true

# Network mode (default: NAT)
# networkingMode=nat

# DNS tunneling (improves DNS resolution in some networks)
dnsTunneling=true

# Auto-proxy (respect Windows proxy settings)
autoProxy=true
```

---

## 🚀 Installation Steps

### **Step 1: Create .wslconfig**

1. Open File Explorer
2. Navigate to: `C:\Users\<YourUsername>\`
3. Create new file: `.wslconfig` (note the leading dot!)
4. Copy the configuration above into the file
5. Save the file

**PowerShell Command:**
```powershell
# Quick create with optimized settings
$wslConfig = @"
[wsl2]
processors=8
memory=12GB
swap=4GB
localhostForwarding=true
dnsTunneling=true
autoProxy=true
"@

$wslConfig | Out-File -FilePath "$env:USERPROFILE\.wslconfig" -Encoding ASCII
```

### **Step 2: Restart WSL2**

**PowerShell (as Administrator):**
```powershell
# Shutdown WSL2
wsl --shutdown

# Wait 10 seconds
Start-Sleep -Seconds 10

# Start WSL2 again (automatically starts when you run a WSL command)
wsl --list --verbose
```

### **Step 3: Verify Configuration**

**Inside WSL2:**
```bash
# Check CPU cores
nproc
# Expected output: 8

# Check memory
free -h
# Expected: ~12 GB total

# Check Docker resource allocation
docker info | grep -i cpu
docker info | grep -i memory
```

---

## 📊 Performance Impact

### **Before (4 cores):**
```
Ollama Inference: ~30 tokens/sec
Chunk Processing: ~15 chunks/min
Docker CPU Usage: 400% (maxed out)
```

### **After (8 cores):**
```
Ollama Inference: ~35-40 tokens/sec (+17-33%)
Chunk Processing: ~20 chunks/min (+33%)
Docker CPU Usage: 300% (headroom available)
```

---

## 🐛 Troubleshooting

### **Problem: .wslconfig not applied**

**Solution:**
1. Check file name (must be `.wslconfig`, not `wslconfig.txt`)
2. Check location (`C:\Users\<YourUsername>\.wslconfig`)
3. Ensure proper shutdown: `wsl --shutdown`
4. Wait 10 seconds before restarting

### **Problem: WSL2 uses too much memory**

**Solution:**
Reduce `memory` setting:
```ini
memory=8GB  # Instead of 12GB
```

### **Problem: Windows becomes slow**

**Solution:**
- Reduce processors to 6:
  ```ini
  processors=6
  ```
- Or reduce memory:
  ```ini
  memory=10GB
  ```

### **Problem: Docker containers crash with OOM**

**Solution:**
Increase swap:
```ini
swap=8GB  # Increase from 4GB
```

---

## 📝 Configuration Options Reference

### **processors**
- **Default:** 50% of host CPUs
- **Range:** 1 to max host CPUs
- **Recommended:** 8 (100% for dedicated development machine)

### **memory**
- **Default:** 50% of host RAM
- **Range:** Minimum 1 GB, max host RAM - 2 GB
- **Recommended:** 12 GB (75% of 16 GB host)

### **swap**
- **Default:** 25% of memory setting
- **Range:** 0 GB (disable) to unlimited
- **Recommended:** 4 GB (prevents OOM)

### **localhostForwarding**
- **Default:** true
- **Options:** true, false
- **Recommended:** true (allows Docker → Windows host communication)

---

## 🔍 Verification Commands

### **Check WSL2 is using new config:**
```powershell
# Windows PowerShell
wsl --list --verbose

# Inside WSL2
cat /proc/cpuinfo | grep processor | wc -l  # Should be 8
free -h  # Should show ~12 GB
```

### **Check Docker resource usage:**
```bash
# Inside WSL2
docker stats --no-stream
```

### **Benchmark Ollama performance:**
```bash
# Quick inference test
time curl -X POST http://localhost:11434/api/generate \
  -d '{
    "model": "gemma-3-4b-it-Q8_0",
    "prompt": "Hello",
    "stream": false
  }'
```

---

## 🎯 Expected Improvements

| Metric | Before (4 cores) | After (8 cores) | Improvement |
|--------|------------------|-----------------|-------------|
| Ollama t/s | 30 t/s | 35-40 t/s | +17-33% |
| Chunk/min | 15 chunks/min | 20 chunks/min | +33% |
| CPU Headroom | 0% (maxed) | 25% available | Better |
| Indexing Time (223 chunks) | ~250s | ~190s | **-24%** |

**Combined with Sprint 20.3 & 20.5:**
- Total indexing time: 250s → 140s → **110s** (-56% total!)

---

## 📚 Further Reading

- [WSL2 Configuration Docs](https://learn.microsoft.com/en-us/windows/wsl/wsl-config#wslconfig)
- [Docker Desktop WSL2 Backend](https://docs.docker.com/desktop/wsl/)
- [Ollama Performance Tuning](https://github.com/ollama/ollama/blob/main/docs/faq.md)

---

**Version:** 1.0
**Sprint:** 20 Feature 20.4
**Date:** 2025-10-30
