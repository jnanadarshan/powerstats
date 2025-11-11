# Project Structure

```
powerstats/
├── architecture.md              # System architecture documentation
├── README.md                    # Main documentation
├── LICENSE                      # License file
├── CONTRIBUTING.md              # Contribution guidelines
├── requirements.txt             # Python dependencies
├── setup_wizard.py             # Interactive config generator
├── .gitignore                  # Git ignore rules
│
├── opt/
│   └── power-monitor/           # Main application directory
│       ├── collector.py         # Data collection script
│       ├── publisher.py         # GitHub publisher script
│       ├── config_manager.py    # Configuration management
│       ├── config.example.json  # Example configuration
│       └── templates/
│           └── dashboard.html   # Dashboard HTML template
│
├── var/
│   └── www/
│       └── html/                # Web root directory
│           └── admin.cgi        # Admin CGI interface
│
├── etc/                         # Configuration files
│   └── (monitor.conf created at runtime)
│
└── deployment/                  # Deployment scripts
    ├── install.sh              # Installation script
    ├── uninstall.sh            # Uninstallation script
    └── test.sh                 # Testing script

Runtime Generated Files:
├── /var/www/html/
│   ├── index.html              # Generated dashboard
│   └── data.json               # 7-day rolling data
│
└── /var/log/
    ├── power-monitor-collector.log
    ├── power-monitor-publisher.log
    └── lighttpd/
        ├── access.log
        └── error.log
```

## Key Components

### Core Scripts

- **collector.py**: Fetches data from Home Assistant every 10 minutes via cron
- **publisher.py**: Pushes updates to GitHub Pages after collection
- **config_manager.py**: Centralized configuration handling
- **admin.cgi**: Web-based admin interface for maintenance mode and manual sync

### Templates

- **dashboard.html**: Jinja2 template with Chart.js visualizations

### Deployment

- **install.sh**: Automated installation for Alpine Linux
- **uninstall.sh**: Clean removal of all components
- **test.sh**: Verification of installation and configuration

### Configuration

- **config.example.json**: Template configuration file
- **config.json**: Actual configuration (created by user, not in git)

## Data Flow

1. **Cron** triggers `collector.py` every 10 minutes
2. **Collector** checks maintenance mode
3. If not in maintenance mode:
   - Fetches current state from Home Assistant API
   - Updates `data.json` with rolling 7-day window
   - Generates `index.html` from template
4. **Publisher** is triggered automatically
5. **Publisher** checks maintenance mode
6. If not in maintenance mode:
   - Pushes `index.html` and `data.json` to GitHub
   - Updates GitHub Pages

## Web Interface

- **/** - Main dashboard (index.html)
- **/admin.cgi** - Admin panel (maintenance mode, manual sync)
- **/data.json** - Raw data API endpoint
