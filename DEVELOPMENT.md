# Development Guide

## Quick Start

```bash
# Show all available commands
make help

# Install dependencies
make deps

# Run tests
make test

# Format code
make format

# Check code quality
make lint
make typecheck

# Clean build artifacts
make clean
```

## Makefile Targets

### `make help`
Show all available targets with descriptions

### `make deps`
Install all development and test dependencies in a virtual environment

### `make test`
Run the full test suite with coverage reporting
- Creates coverage report in `htmlcov/index.html`
- Shows coverage percentage in terminal

### `make lint`
Run code linters (ruff and flake8)

### `make format`
Auto-format code with black and isort

### `make typecheck`
Run mypy type checking

### `make clean`
Remove all build artifacts, cache files, and virtual environment

### `make release`
**Create a new release:**
1. Runs full test suite
2. Checks git working tree is clean
3. Extracts version from `manifest.json`
4. Creates and pushes git tag
5. Prints next steps for GitHub release

### `make version`
Show current version from manifest.json

## Development Workflow

### Setting Up
```bash
# Clone the repository
git clone <repo-url>
cd homeassistant-aws-bedrock-conversation-agent

# Install dependencies
make deps

# Activate virtual environment
source .venv/bin/activate
```

### Making Changes
```bash
# Make your changes
vim custom_components/bedrock_conversation/some_file.py

# Format code
make format

# Run tests
make test

# Check code quality
make lint
make typecheck
```

### Testing Locally
```bash
# Copy to Home Assistant
cp -r custom_components/bedrock_conversation ~/.homeassistant/custom_components/

# Restart Home Assistant
# Test your changes
```

### Releasing
```bash
# Update version in manifest.json
vim custom_components/bedrock_conversation/manifest.json

# Commit changes
git add .
git commit -m "Release v1.0.1"

# Create release (runs tests, creates tag, pushes)
make release

# Create GitHub release with release notes
# Submit to HACS
```

## Project Structure

```
.
├── Makefile                 # Build automation
├── custom_components/       # The actual integration
│   └── bedrock_conversation/
├── tests/                   # Unit tests
├── requirements-test.txt    # Test dependencies
├── requirements-dev.txt     # Dev tools
└── pytest.ini              # Test configuration
```

## Code Style

- **Formatter**: black (line length 88)
- **Import sorting**: isort
- **Linter**: ruff + flake8
- **Type checking**: mypy
- Follow Home Assistant coding standards

## Testing

### Test Organization
- `tests/conftest.py` - Shared fixtures
- `tests/test_*.py` - Test files matching module names
- Mock AWS calls - never make real API requests

### Writing Tests
```python
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_my_feature(hass, mock_config_entry):
    """Test description."""
    # Your test code
    assert result is True
```

### Running Specific Tests
```bash
# Single file
pytest tests/test_utils.py

# Single test
pytest tests/test_utils.py::test_closest_color -v

# With output
pytest tests/ -v -s
```

## Debugging

### Enable Debug Logging
Add to Home Assistant `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.bedrock_conversation: debug
```

### VS Code
Add to `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  ]
}
```

## Version Management

Version is stored in `custom_components/bedrock_conversation/manifest.json`:
```json
{
  "version": "1.0.0"
}
```

The Makefile automatically extracts this version for releases.

## Release Checklist

- [ ] Update version in `manifest.json`
- [ ] Update `CHANGELOG.md`
- [ ] Run `make test` - all tests pass
- [ ] Run `make lint` - no issues
- [ ] Commit all changes
- [ ] Run `make release`
- [ ] Create GitHub release with notes
- [ ] Test installation from HACS
- [ ] Announce on Home Assistant Community

## Troubleshooting

### Tests Fail
```bash
# Reinstall dependencies
make clean
make deps
make test
```

### Import Errors
```bash
# Activate virtual environment
source .venv/bin/activate
```

### Release Fails
```bash
# Check working tree is clean
git status

# Check version extraction
make version

# Check no tag exists
git tag | grep v1.0.0
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linters
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.
