# PyViCareUB2

A monitoring tool for ViCare heating systems that collects data and displays it through a web interface.

## Features

- Real-time data collection from ViCare devices
- Beautiful web interface with dark mode
- System metrics visualization
- Temperature metrics visualization
- Automatic data collection every 5 minutes
- Local mode for testing without device connection

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/vicareub2.git
cd vicareub2
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

## Configuration

Create a `.env` file in the project root with the following variables:

```
CLIENT_ID=your_client_id
EMAIL=your_email
PASSWORD=your_password
LOCAL_MODE=false
TIMEZONE=Europe/Amsterdam
```

## Usage

Run the application:
```bash
vicareub2
```

Or:
```bash
python vicareub2.py
```

The web interface will be available at `http://localhost:8000`.

## Development

To run in development mode:

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run in local mode:
```bash
LOCAL_MODE=true vicareub2
```

## License

MIT License 