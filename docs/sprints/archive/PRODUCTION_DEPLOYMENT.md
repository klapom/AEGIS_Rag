# AEGIS RAG Production Deployment Guide

## 🎯 Ziel

AEGIS RAG so auf der DGX Spark deployen, dass es dauerhaft läuft und über `http://<dgx-spark-ip>` erreichbar ist - auch wenn VS Code nicht läuft.

## 📋 Voraussetzungen

- DGX Spark mit Docker installiert
- Root/Sudo-Zugriff auf DGX Spark
- Netzwerk-Zugriff auf die DGX Spark IP-Adresse

## 🚀 Deployment Schritte

### Schritt 1: Environment konfigurieren

```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag

# Kopiere Production Environment Template
cp .env.production .env.production.local

# Bearbeite die Konfiguration
nano .env.production.local
```

**Wichtige Einstellungen in `.env.production.local`:**

```bash
# DGX Spark IP-Adresse (ersetze mit deiner IP)
VITE_API_BASE_URL=http://192.168.1.100  # Deine DGX Spark IP!

# Sichere Passwörter setzen
NEO4J_PASSWORD=dein-sicheres-passwort
GRAFANA_PASSWORD=dein-grafana-passwort

# LLM Modelle
OLLAMA_MODEL_GENERATION=nemotron-no-think:latest
OLLAMA_MODEL_EXTRACTION=gpt-oss:20b
OLLAMA_MODEL_VISION=qwen3-vl:32b

# Production Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
CORS_ORIGINS=*  # In Production auf spezifische Domain setzen!
```

### Schritt 2: Frontend Build konfigurieren

```bash
# Frontend Environment für Production Build
cd frontend
nano .env.production
```

**frontend/.env.production:**
```bash
VITE_API_BASE_URL=http://192.168.1.100  # Deine DGX Spark IP!
```

### Schritt 3: Deployment ausführen

```bash
# Zurück zum Hauptverzeichnis
cd /home/admin/projects/aegisrag/AEGIS_Rag

# Deployment starten (baut Frontend + startet alle Services)
./deploy-production.sh
```

**Was passiert beim Deployment:**

1. ✅ Frontend wird als Production Build erstellt (`npm run build`)
2. ✅ Docker Services werden gestartet (API, Ollama, Qdrant, Neo4j, Redis, Nginx)
3. ✅ Ollama Modelle werden gepullt (nemotron, gpt-oss, qwen3-vl)
4. ✅ Nginx Reverse Proxy wird konfiguriert

**Ausgabe nach erfolgreichem Deployment:**

```
=========================================
AEGIS RAG is now running!
=========================================

Frontend:    http://192.168.1.100
API:         http://192.168.1.100/api
Health:      http://192.168.1.100/health

Monitoring:
  Prometheus: http://192.168.1.100:9090
  Grafana:    http://192.168.1.100:3000 (admin/admin)

Database Admin (Internal):
  Neo4j:      http://192.168.1.100/neo4j
  Qdrant:     http://192.168.1.100/qdrant

Logs:        docker compose -f docker-compose.production.yml logs -f
Stop:        ./deploy-production.sh --stop
=========================================
```

### Schritt 4: Automatischer Start beim Booten (Optional)

Damit AEGIS RAG automatisch startet, wenn die DGX Spark neu bootet:

```bash
# Systemd Service installieren
sudo cp aegis-rag.service /etc/systemd/system/

# Systemd neu laden
sudo systemctl daemon-reload

# Service aktivieren (automatischer Start)
sudo systemctl enable aegis-rag

# Service starten
sudo systemctl start aegis-rag

# Status prüfen
sudo systemctl status aegis-rag
```

**Systemd Service Management:**

```bash
# Status anzeigen
sudo systemctl status aegis-rag

# Stoppen
sudo systemctl stop aegis-rag

# Neu starten
sudo systemctl restart aegis-rag

# Logs anzeigen
sudo journalctl -u aegis-rag -f

# Automatischen Start deaktivieren
sudo systemctl disable aegis-rag
```

### Schritt 5: Firewall konfigurieren (wenn nötig)

Falls eine Firewall aktiv ist, Ports öffnen:

```bash
# UFW (Ubuntu Firewall)
sudo ufw allow 80/tcp      # HTTP (Frontend + API)
sudo ufw allow 443/tcp     # HTTPS (optional, für SSL)
sudo ufw allow 9090/tcp    # Prometheus (optional)
sudo ufw allow 3000/tcp    # Grafana (optional)

# Firewall neu laden
sudo ufw reload

# Status prüfen
sudo ufw status
```

**Für iptables:**

```bash
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 9090 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 3000 -j ACCEPT

# Regeln speichern
sudo netfilter-persistent save
```

## 🔧 Verwaltung & Wartung

### Docker Services verwalten

```bash
# Status aller Services anzeigen
./deploy-production.sh --status

# Logs anzeigen (live)
./deploy-production.sh --logs

# Logs eines einzelnen Services
docker compose -f docker-compose.production.yml logs -f api
docker compose -f docker-compose.production.yml logs -f nginx
docker compose -f docker-compose.production.yml logs -f ollama

# Services neu starten
docker compose -f docker-compose.production.yml restart

# Services stoppen
./deploy-production.sh --stop

# Services neu builden (nach Code-Änderungen)
./deploy-production.sh --rebuild
```

### Ollama Modelle verwalten

```bash
# Verfügbare Modelle anzeigen
docker exec aegis-ollama ollama list

# Neues Modell pullen
docker exec aegis-ollama ollama pull llama3.2:8b

# Modell entfernen
docker exec aegis-ollama ollama rm llama3.2:8b

# Modell testen
docker exec aegis-ollama ollama run nemotron-no-think "Hello, how are you?"
```

### Health Checks

```bash
# API Health Check
curl http://192.168.1.100/health

# Qdrant Health
curl http://192.168.1.100:6333/health

# Neo4j Health (Bolt Port)
echo "RETURN 1" | docker exec -i aegis-neo4j cypher-shell -u neo4j -p <password>

# Redis Health
docker exec aegis-redis redis-cli ping
```

### Backup & Restore

```bash
# Volumes sichern
docker run --rm -v aegis_neo4j_data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/neo4j-backup-$(date +%Y%m%d).tar.gz /data

docker run --rm -v aegis_qdrant_data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/qdrant-backup-$(date +%Y%m%d).tar.gz /data

# Volume wiederherstellen
docker run --rm -v aegis_neo4j_data:/data -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/neo4j-backup-20250125.tar.gz -C /
```

## 📊 Monitoring

### Prometheus (Metriken)

- URL: `http://192.168.1.100:9090`
- Zeigt Performance-Metriken, Resource-Usage, API-Latenz

### Grafana (Dashboards)

- URL: `http://192.168.1.100:3000`
- Login: `admin` / `<GRAFANA_PASSWORD>`
- Vorkonfigurierte Dashboards für AEGIS RAG

### Logs zentral

```bash
# Alle Logs
docker compose -f docker-compose.production.yml logs -f

# Nur Fehler
docker compose -f docker-compose.production.yml logs -f | grep ERROR

# Nur API
docker compose -f docker-compose.production.yml logs -f api
```

## 🔒 Security Best Practices

### Für Production Deployment

1. **Passwörter ändern:**
   - Neo4j Password: `NEO4J_PASSWORD`
   - Grafana Password: `GRAFANA_PASSWORD`
   - Niemals Default-Passwörter verwenden!

2. **CORS konfigurieren:**
   ```bash
   # In .env.production.local
   CORS_ORIGINS=https://your-domain.com  # Nicht "*" in Production!
   ```

3. **HTTPS einrichten:**
   - SSL-Zertifikate in `nginx/ssl/` platzieren
   - Nginx-Konfiguration für HTTPS aktivieren (siehe `nginx/nginx.conf`)

4. **Firewall:**
   - Nur notwendige Ports öffnen (80, 443)
   - Monitoring-Ports (9090, 3000) nur intern freigeben

5. **Database Admin Interfaces:**
   - Neo4j Browser (`/neo4j`) nur intern freigeben
   - Qdrant Dashboard (`/qdrant`) nur intern freigeben
   - In Production diese Routen in Nginx auskommentieren

## 🐛 Troubleshooting

### Problem: Services starten nicht

```bash
# Status prüfen
docker compose -f docker-compose.production.yml ps

# Logs prüfen
docker compose -f docker-compose.production.yml logs

# Service neu starten
docker compose -f docker-compose.production.yml restart <service-name>
```

### Problem: Frontend zeigt "API not reachable"

```bash
# 1. API Health Check
curl http://192.168.1.100/health

# 2. Nginx Logs prüfen
docker compose -f docker-compose.production.yml logs nginx

# 3. API Logs prüfen
docker compose -f docker-compose.production.yml logs api

# 4. Frontend Environment prüfen
cat frontend/.env.production  # VITE_API_BASE_URL muss stimmen!
```

### Problem: Ollama Modelle nicht verfügbar

```bash
# Modelle prüfen
docker exec aegis-ollama ollama list

# Modelle neu pullen
docker exec aegis-ollama ollama pull nemotron-no-think:latest
docker exec aegis-ollama ollama pull gpt-oss:20b
docker exec aegis-ollama ollama pull qwen3-vl:32b
```

### Problem: Hoher Memory-Verbrauch

```bash
# Resource Usage anzeigen
docker stats

# Services einzeln neu starten
docker compose -f docker-compose.production.yml restart ollama
docker compose -f docker-compose.production.yml restart api
```

### Problem: Port bereits belegt

```bash
# Port-Belegung prüfen
sudo lsof -i :80
sudo lsof -i :8000

# Prozess stoppen
sudo kill <PID>

# Oder anderen Port verwenden (in docker-compose.production.yml)
```

## 📚 Weitere Ressourcen

- **AEGIS RAG Dokumentation:** `docs/`
- **Sprint Plans:** `docs/sprints/`
- **ADRs:** `docs/adr/`
- **Feature Docs:** `docs/features/`

## ✅ Checkliste: Production Ready

- [ ] `.env.production.local` konfiguriert mit DGX Spark IP
- [ ] `frontend/.env.production` konfiguriert mit DGX Spark IP
- [ ] Alle Passwörter geändert (nicht Default!)
- [ ] `./deploy-production.sh` erfolgreich ausgeführt
- [ ] Frontend erreichbar unter `http://<dgx-spark-ip>`
- [ ] API Health Check erfolgreich: `curl http://<dgx-spark-ip>/health`
- [ ] Systemd Service installiert (automatischer Start)
- [ ] Firewall konfiguriert (Ports 80, 443 offen)
- [ ] Backup-Strategie definiert
- [ ] Monitoring eingerichtet (Prometheus, Grafana)

---

**Support:**
Bei Problemen: Logs prüfen (`./deploy-production.sh --logs`) und Issue auf GitHub erstellen.
