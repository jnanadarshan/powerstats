# Quick Reference Card

## 🚀 Installation
```sh
cd /tmp/powerstats/deployment
chmod +x install.sh && ./install.sh
```

## ⚙️ Configuration
```sh
cp /opt/power-monitor/config.example.json /opt/power-monitor/config.json
vi /opt/power-monitor/config.json
chmod 600 /opt/power-monitor/config.json
```

## 🧪 Testing
```sh
# Run test suite
./test.sh

# Manual collection
python3 /opt/power-monitor/collector.py

# Manual publish
python3 /opt/power-monitor/publisher.py
```

## 📊 Access
- **Dashboard**: http://\<device-ip\>/
- **Admin Panel**: http://\<device-ip\>/admin.cgi

## 🔧 Maintenance Mode
```sh
# Enable
python3 /opt/power-monitor/utils.py maintenance on

# Disable
python3 /opt/power-monitor/utils.py maintenance off

# Toggle
python3 /opt/power-monitor/utils.py maintenance toggle
```

## 📈 Status & Logs
```sh
# System status
python3 /opt/power-monitor/utils.py status

# View logs
python3 /opt/power-monitor/utils.py logs collector
python3 /opt/power-monitor/utils.py logs publisher
python3 /opt/power-monitor/utils.py logs web

# Live log tail
tail -f /var/log/power-monitor-collector.log
```

## 💾 Data Management
```sh
# Export data
python3 /opt/power-monitor/utils.py export backup.json

# Clear data
python3 /opt/power-monitor/utils.py clear
```

## 🔄 Service Control
```sh
# Restart web server
rc-service lighttpd restart

# View cron jobs
crontab -l

# Manual sync from admin panel
curl -X POST http://localhost/admin.cgi -d "action=manual_sync&authenticated=1"
```

## 📝 File Locations
| Path | Description |
|------|-------------|
| `/opt/power-monitor/config.json` | Configuration |
| `/etc/monitor.conf` | Maintenance mode state |
| `/var/www/html/index.html` | Generated dashboard |
| `/var/www/html/data.json` | Data storage |
| `/var/log/power-monitor-*.log` | Application logs |

## 🔐 Security Checklist
- [ ] Change default admin password
- [ ] Set config.json permissions: `chmod 600`
- [ ] Use HTTPS for Home Assistant API
- [ ] Use fine-grained GitHub tokens
- [ ] Restrict admin panel access via firewall

## ⚠️ Troubleshooting
| Issue | Check |
|-------|-------|
| No data | Verify HA URL, token, entity ID |
| GitHub publish fails | Check token permissions, repo exists |
| Web interface down | `rc-service lighttpd status` |
| High memory | `ps aux \| grep python` |
| Cron not running | `crontab -l` |

## 📞 Support
- Logs: `/var/log/power-monitor-*.log`
- Config test: `python3 /opt/power-monitor/config_manager.py`
- System test: `./deployment/test.sh`

## 🔢 Resource Usage
- **Storage**: ~100MB total
- **RAM**: ~70MB peak
- **Network**: <1MB/hour

## 📚 Documentation
- `README.md` - Complete guide
- `architecture.md` - System design
- `PROJECT_STRUCTURE.md` - File layout
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
