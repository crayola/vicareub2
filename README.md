# PyViCareUB2

A monitoring tool for ViCare heating systems that collects data and displays it through a web interface.

## Features

- Real-time data collection from ViCare devices
- Two visualization options:
  - Traditional web interface with matplotlib charts
  - Modern interactive Streamlit interface with dynamic visualizations
- System metrics visualization
- Temperature metrics visualization
- Device/pump status visualization (boolean variables)
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
USE_STREAMLIT=false
TIMEZONE=Europe/Amsterdam
```

## Usage

Run the application with the traditional Flask + matplotlib interface:
```bash
vicareub2
```

Or run with the modern Streamlit interface:
```bash
vicareub2 --streamlit
```

You can also run in local mode (without device connection):
```bash
vicareub2 --local
```

Combine options:
```bash
vicareub2 --streamlit --local
```

Or run directly:
```bash
python vicareub2.py [options]
```

The web interfaces will be available at:
- Traditional interface: `http://localhost:8000`
- Streamlit interface: `http://localhost:8501`

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