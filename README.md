# Predictive Maintenance System

Real-time sensor monitoring with FFT analysis and secure remote data upload.

## 🚀 Deploy to Cloud (Free) - 5 Minutes

👉 **[See DEPLOY_TO_RENDER.md for complete deployment guide](DEPLOY_TO_RENDER.md)**

Quick summary:
1. Push to GitHub
2. Connect to Render.com (free account)
3. Add your Namify domain
4. Done! ✅

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [**DEPLOY_TO_RENDER.md**](DEPLOY_TO_RENDER.md) | **Deploy to cloud in 5 min** ⭐ |
| [UPLOAD_ARCHITECTURE.md](UPLOAD_ARCHITECTURE.md) | Upload system design (15+ pages) |
| [CLIENT_SETUP_GUIDE.md](CLIENT_SETUP_GUIDE.md) | Client deployment guide (10+ pages) |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | One-page reference |

## 🎯 Features

- **Real-time Monitoring**: 3 sensor types (acceleration, current, audio)
- **FFT Analysis**: Full spectrum line graph + top 5 frequencies
- **Three View Modes**: MAX, MIN, COMBINED sensor data
- **Secure Upload**: API key authentication for remote sensors
- **Health Monitoring**: Automatic status detection (normal/warning/critical)
- **Web Dashboard**: React + TailwindCSS + Chart.js

## 💻 Quick Start (Local Development)

### Wilo Cloud Monitoring Service

A real-time cloud monitoring dashboard for sensor data analysis with comprehensive statistical parameter calculation and visualization.

## 🚀 Quick Start

### Option 1: NPM (Recommended)
```bash
# Install all dependencies
npm run install:all

# Run both frontend and backend concurrently
npm start
```

### Option 2: Windows Scripts
```powershell
# PowerShell
.\start.ps1

# Or Command Prompt
start.bat
```

### Option 3: Manual
```bash
# Terminal 1 - Backend
python app.py

# Terminal 2 - Frontend  
cd frontend && npm run dev
```

**Access the dashboard at:** http://localhost:5173

---

## Features

- **Multiple Charts**: Simultaneous visualization of different statistical parameters
- **Real-time Updates**: Live data streaming via Socket.IO
- **Comprehensive Statistics**: 21+ statistical parameters including amplitude, health ratios, and distribution features
- **Event Logging**: Manual failure event tracking with automatic slope analysis
- **Modern UI**: React + TailwindCSS with dark/light theme support
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Architecture

| Component | Technology |
|-----------|------------|
| Backend | Flask + Socket.IO |
| Frontend | React + Vite + TailwindCSS |
| Charts | Chart.js + react-chartjs-2 |
| Data Processing | NumPy + SciPy |

## Statistical Parameters

### Basic Amplitude Statistics
- Max, Min, Mean, Absolute Mean
- RMS, Variance, Standard Deviation
- Peak, Peak-to-Peak

### Severity / Health Ratios
- Crest Factor, Impulse Factor
- Shape Factor, Clearance Factor

### Distribution Features
- Skewness, Kurtosis, Excess Kurtosis

### Additional Parameters
- Energy, Zero-Crossing Rate
- Percentiles (90th, 95th, 99th)

## Installation

### Prerequisites
- Python 3.8+
- Node.js 18+

### Backend Setup
```bash
# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Install Python dependencies
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd frontend
npm install
```

### Root Dependencies (for concurrent running)
```bash
npm install
```

## NPM Scripts

| Command | Description |
|---------|-------------|
| `npm start` | Run both servers concurrently |
| `npm run dev` | Alias for `npm start` |
| `npm run backend` | Run Flask backend only |
| `npm run frontend` | Run Vite frontend only |
| `npm run install:all` | Install all dependencies |

## Generate Test Data

```bash
python generate_dummy_data.py
```

This creates sample sensor data in the `Data/` directory for testing.

## Data Format

The system expects CSV files with the following formats:

**Format 1** (Legacy):
```csv
timestamp,z
1000.0,0.1
1001.0,0.2
```

**Format 2** (ISO Timestamps):
```csv
timestamp,value
2025-11-24T21:26:22.463,6.508702
2025-11-24T21:26:22.464,1.497415
```

## API Endpoints

### Data Endpoints
- `GET /files` - List all CSV files
- `GET /parameter-data/<parameter>` - Get time-series data for specific parameter
- `GET /chart-data` - Get complete chart data with statistics
- `GET /view/<filename>` - View CSV file contents

### Event Logging Endpoints
- `POST /create-event` - Create new failure event with slope tracking
- `GET /events` - List all logged events
- `GET /event/<event_id>` - Get detailed event data
- `GET /event-names` - Get unique event names for dropdown

See [EVENTS_README.md](EVENTS_README.md) for detailed event logging documentation.

## Configuration

Edit `config.json` to adjust monitoring settings:
```json
{
  "interval_seconds": 300
}
```

## File Monitoring

The system automatically monitors the `Data/` directory for new CSV files matching the pattern `max_reading*.csv` and updates charts in real-time.

## Development

### Project Structure
```
├── app.py                 # Flask backend API
├── package.json          # Root package.json for concurrent running
├── start.ps1             # PowerShell startup script
├── start.bat             # Batch startup script
├── config.json           # Configuration settings
├── requirements.txt      # Python dependencies
├── generate_dummy_data.py # Test data generator
├── frontend/             # React application
│   ├── src/
│   │   ├── App.jsx      # Main React component
│   │   ├── index.css    # Styles with TailwindCSS
│   │   └── main.jsx     # React entry point
│   └── package.json     # Frontend dependencies
├── Data/                # CSV data files (auto-created)
├── Events/              # Event log files (auto-created)
└── Server/              # Additional server utilities
```

### Adding New Parameters

To add new statistical parameters:

1. Update the `calculate_statistics()` function in `app.py`
2. Add the parameter to the appropriate options array in `App.jsx`
3. Update the parameter label mapping in `getParameterLabel()`

## License

This project is licensed under the MIT License.
