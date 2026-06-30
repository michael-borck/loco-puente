# loco-puente

Bridges Loco and Puente frameworks by providing integration utilities and middleware for seamless communication between the two Python web development platforms.

## Overview

loco-puente is a comprehensive integration layer designed to facilitate seamless communication and data exchange between the Loco and Puente Python web frameworks. This project provides utilities, middleware, and helper functions that enable developers to leverage the strengths of both frameworks within a unified application architecture.

Whether you're building a complex web application that requires the unique capabilities of both frameworks or migrating between them, loco-puente simplifies the integration process with well-tested utilities and clear architectural patterns.

## Features

- **Framework Integration**: Utilities for bridging Loco and Puente frameworks
- **Middleware Support**: Custom middleware for request/response handling across frameworks
- **Docker Support**: Pre-configured Dockerfiles for various AI/ML applications
- **Comprehensive Documentation**: Architecture guides and configuration examples
- **Production Ready**: MIT licensed with CI/CD pipelines

## Installation

### From Source

Clone the repository and install in development mode:

```bash
git clone https://github.com/michael-borck/loco-puente.git
cd loco-puente
pip install -e .
```

### Using pip

```bash
pip install loco-puente
```

### Requirements

- Python 3.8 or higher
- Loco framework
- Puente framework

## Usage

### Basic Integration

Import the integration utilities in your application:

```python
from loco_puente import LocoPuenteBridge

# Initialize the bridge
bridge = LocoPuenteBridge()
```

### Middleware Configuration

Add loco-puente middleware to your application:

```python
from loco_puente.middleware import PuenteMiddleware

# Configure middleware
app.add_middleware(PuenteMiddleware)
```

### Framework Communication

Enable seamless communication between Loco and Puente:

```python
from loco_puente import sync_frameworks

# Synchronize framework states
sync_frameworks(loco_app, puente_app)
```

## Architecture

For detailed information about the project architecture, integration patterns, and design decisions, refer to the [Architecture Documentation](./docs/architecture.md).

## Configuration

Configuration options and setup instructions are available in the [Configuration Guide](./docs/choosing.md).

## Docker Support

The project includes Docker support for various AI/ML applications:

- ComfyUI
- Fooocus
- NodePad
- SwarmUI

Build Docker images using the provided Dockerfiles in `puente/dockerfiles/`.

## Project Structure

```
loco-puente/
├── docs/                          # Documentation files
│   ├── architecture.md           # Architecture overview
│   └── choosing.md               # Configuration guide
├── puente/                        # Core integration code
│   └── dockerfiles/              # Docker configurations
├── .github/                       # GitHub workflows
│   └── workflows/                # CI/CD pipelines
└── README.md                      # This file
```

## Documentation

- [Architecture Guide](./docs/architecture.md) - Detailed architecture and design patterns
- [Hardware Configuration](./HARDWARE.md) - Hardware requirements and optimization
- [Framework Selection Guide](./CHOOSING.md) - Guide for choosing between frameworks

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests to help improve loco-puente.

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/michael-borck/loco-puente).