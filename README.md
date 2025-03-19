# Vital Monitor

## Overview
Vital Monitor is a Python-based tool for processing and analyzing vital sign data from medical monitoring systems. It calculates key clinical parameters including Analgesia Nociception Index (ANI) and Surgical Pleth Index (SPI) from ECG and PPG signals.

## Features
- **ECG Processing**: Cleans and processes ECG signals for reliable analysis
- **PPG Processing**: Filters and prepares plethysmographic waveforms
- **ANI Calculation**: Computes Analgesia Nociception Index from heart rate variability
- **SPI Calculation**: Calculates Surgical Pleth Index from pleth waveforms
- **Parallel Processing**: Efficiently processes multiple files simultaneously
- **Data Visualization**: Adds processed tracks to vital files for visualization

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/vital_monitor.git
cd vital_monitor

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Directory Setup
Place your `.vital` files in the `data` directory. If it doesn't exist, create it:
```bash
mkdir -p data
```

### Processing Vital Files
```bash
python process_vital_data.py [--workers N]
```
Options:
- `--workers`: Number of parallel workers (defaults to available CPU cores)

The processed files will be saved to the `out` directory with additional tracks for ANI and SPI values.