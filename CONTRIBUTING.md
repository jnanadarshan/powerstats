# Contributing to Power Consumption Monitoring System

Thank you for your interest in contributing! This project aims to provide a lightweight monitoring solution for embedded devices.

## Development Setup

1. Clone the repository
2. Install Python dependencies: `pip install -r requirements.txt`
3. Copy `opt/power-monitor/config.example.json` to `opt/power-monitor/config.json`
4. Update config with your test Home Assistant and GitHub credentials

## Testing

Before submitting a PR:

1. **Test locally**: Run collector and publisher scripts manually
2. **Check resource usage**: Monitor memory and CPU usage
3. **Test on target hardware**: If possible, test on Luckfox Pico Max or similar device
4. **Verify web interface**: Check dashboard rendering and admin panel functionality

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and modular

## Areas for Contribution

- **Additional visualizations**: More chart types or data views
- **Performance optimizations**: Reduce memory or storage usage
- **Security improvements**: Better authentication, HTTPS support
- **Additional data sources**: Support for other IoT platforms
- **Documentation**: Improve guides, add examples
- **Bug fixes**: Check issues for known problems

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with clear commit messages
4. Test thoroughly
5. Submit a pull request with description of changes

## Questions?

Open an issue for discussion before major changes.
