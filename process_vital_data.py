import os
import pyvital.filters.pleth_spi as f_spi
import concurrent.futures
import argparse
import vitaldb

# Import utility functions
from utils import (
    prepare_ecg,
    prepare_ppg,
    calculate_spi,
    calculate_ani,
    chunk_data_for_track
)

# Constants
SAMPLE_RATE = 100
COLOR_BLUE = 3634859  # For PPG visualization

# Threshold configurations
ECG_MAX_THRESHOLD = 3.0
ECG_MIN_THRESHOLD = -1.0
PPG_MAX_THRESHOLD = 100.0
PPG_MIN_THRESHOLD = 0.0
NAN_THRESHOLD = 0.5  # Maximum proportion of NaN values allowed

DATA_DIR = "data"
OUTPUT_DIR = "out"

def process_file(file_path):
    """Process a single vital file to calculate HRV, SPI, and ANI"""
    file_name = os.path.basename(file_path)
    print(f"Processing {file_name}")
    
    vf = vitaldb.VitalFile(file_path)
    # Prepare ECG data
    ecg, ecg_clean, error = prepare_ecg(
        file_path, 
        sample_rate=SAMPLE_RATE,
        nan_threshold=NAN_THRESHOLD,
        max_threshold=ECG_MAX_THRESHOLD,
        min_threshold=ECG_MIN_THRESHOLD
    )
    
    if error:
        print(error)
    else:
        recs = chunk_data_for_track(ecg_clean, vf, SAMPLE_RATE)
        vf.add_track("Intellivue/ECG_II_clean", recs, SAMPLE_RATE, "mV", ECG_MIN_THRESHOLD, ECG_MAX_THRESHOLD)

    if ecg_clean is not None:
        # Calculate ANI if ECG is valid
        ANI, error = calculate_ani(ecg_clean, sample_rate=SAMPLE_RATE)
        if error:
            print(error)
        else:
            recs = [{'dt': vf.dtstart + 64, 'val': ANI}]
            vf.add_track("ANIMonitor2/custom_ANI", recs, 1, "", 0, 100)

    # Prepare PPG data
    ppg, ppg_clean, error = prepare_ppg(
        file_path,
        sample_rate=SAMPLE_RATE,
        nan_threshold=NAN_THRESHOLD,
        max_threshold=PPG_MAX_THRESHOLD,
        min_threshold=PPG_MIN_THRESHOLD
    )
    
    if error:
        print(error)
    else:
        recs = chunk_data_for_track(ppg_clean, vf, SAMPLE_RATE)
        vf.add_track("Intellivue/PLETH_clean", recs, SAMPLE_RATE, "", PPG_MIN_THRESHOLD, PPG_MAX_THRESHOLD)
    
    # Calculate SPI if PPG is valid and SPI module is available
    if ppg_clean is not None and f_spi is not None:
        mean_spi, min_spi, spi, error = calculate_spi(
            file_path, 
            ppg_clean, 
            f_spi, 
            sample_rate=SAMPLE_RATE, 
            color_blue=COLOR_BLUE
        )
        if error:
            print(error)
        else:
            recs = [{'dt': vf.dtstart, 'val': spi}]
            vf.add_track("ANIMonitor2/custom_SPI", recs, 1, "", 0, 100)
    # Generate output filename
    output_filename = os.path.join(OUTPUT_DIR, file_name)

    # Save the VitalFile with processed data
    vf.to_vital(output_filename)
    print(f"Saved processed vital file to {output_filename}")


def main():
    """Main function to process all vital files"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Process vital monitor data files")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help="Number of worker processes")
    args = parser.parse_args()

    # Setup directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Find all vital files
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.vital')]
    
    if not files:
        print(f"No vital files found in directory: {DATA_DIR}")
        return
    
    print(f"Found {len(files)} vital files. Processing with {args.workers} workers...")
    
    # Process files in parallel
    file_paths = [os.path.join(DATA_DIR, f) for f in files]
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        executor.map(process_file, file_paths)

if __name__ == "__main__":
    main()