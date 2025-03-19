"""
Utility functions for vital data processing
"""
import numpy as np
import vitaldb
import math
import neurokit2 as nk
from ani import calculate_area_segment

def chunk_data_for_track(data, vf, sample_rate=100):
    """
    Split data into chunks to prevent memory issues when adding to VitalFile.
    
    Args:
        data: The data array to chunk
        vf: VitalFile instance for timestamp reference
        sample_rate: The sample rate of the data
        
    Returns:
        List of record dictionaries with timestamps and values
    """
    recs = []
    chunk_size = int(sample_rate)
    for istart in range(0, len(data), chunk_size):
        end_idx = min(istart + chunk_size, len(data))
        recs.append({
            'dt': vf.dtstart + istart / sample_rate, 
            'val': data[istart:end_idx]
        })
    return recs

def prepare_ecg(file_path, sample_rate=100, nan_threshold=0.5, 
                max_threshold=3.0, min_threshold=-1.0):
    """Prepare ECG data for HRV and ANI calculations"""
    try:
        vf = vitaldb.VitalFile(file_path)
        ecg = vf.to_numpy('Intellivue/ECG_II', 1/sample_rate)
        # Check data length
        if len(ecg) == 0:
            return None, None, "No ECG data found"
        
        # Check for too many NaN values
        nan_count = np.isnan(ecg).sum()
        if nan_count > len(ecg) * nan_threshold:
            return None, None, f"Too many NaN values in ECG: {nan_count}/{len(ecg)} ({nan_count/len(ecg):.2%})"
        
        # Clean ECG data
        ecg[np.isnan(ecg)] = 0.
        idx_abn = (ecg >= max_threshold) | (ecg <= min_threshold)
        ecg[idx_abn] = 0.
        ecg_clean = nk.ecg_clean(ecg, sampling_rate=sample_rate).astype(np.float32)

        return ecg, ecg_clean, None
    except Exception as e:
        print(f"Error preparing ECG from {file_path}: {str(e)}")
        return None, None, f"Error preparing ECG: {str(e)}"

def prepare_ppg(file_path, sample_rate=100, nan_threshold=0.5,
                max_threshold=100.0, min_threshold=0.0):
    """Prepare PPG data for SPI calculation"""
    try:
        vf = vitaldb.VitalFile(file_path)
        ppg = vf.to_numpy('Intellivue/PLETH', 1/sample_rate)
        
        # Check data length
        if len(ppg) == 0:
            return None, None, "No PPG data found"
        
        # Check for too many NaN values
        nan_count = np.isnan(ppg).sum()
        if nan_count > len(ppg) * nan_threshold:
            return None, None, f"Too many NaN values in PPG: {nan_count}/{len(ppg)} ({nan_count/len(ppg):.2%})"
        
        # Clean PPG data
        ppg[np.isnan(ppg)] = 0.
        ppg = np.clip(ppg, min_threshold, max_threshold)
        ppg_clean = nk.ppg_clean(ppg, sampling_rate=sample_rate, method=None).astype(np.float32)
        
        return ppg, ppg_clean, None
    except Exception as e:
        print(f"Error preparing PPG from {file_path}: {str(e)}")
        return None, None, f"Error preparing PPG: {str(e)}"

def calculate_spi(file_path, ppg_clean, f_spi, sample_rate=100, color_blue=3634859):
    """Calculate SPI from cleaned PPG data"""
    if f_spi is None:
        return None, None, "SPI calculation module not available"
    
    try:
        vf = vitaldb.VitalFile(file_path)
        
        # Remove existing tracks if they exist
        vf.remove_track('Intellivue/PLETH')
        vf.remove_track('Intellivue/ECG_II')

        # Call the function to get chunked data
        recs = chunk_data_for_track(ppg_clean, vf, sample_rate)
        
        vf.add_track('PLETH', recs, srate=sample_rate, mindisp=0, maxdisp=100, col=color_blue)
        
        # Run SPI filter
        vf.run_filter(f_spi.run, f_spi.cfg)
        
        # Extract SPI values
        spi = vf.to_numpy('SPI', 1).flatten()
        # Interpolate NaN values in SPI data
        if np.any(np.isnan(spi)):
            # Find indices of non-NaN values
            valid_indices = np.where(~np.isnan(spi))[0]
            
            # If there are some valid values, interpolate
            if len(valid_indices) > 0:
                valid_values = spi[valid_indices]
                # Create interpolation function based on valid indices and values
                spi = np.interp(
                    np.arange(len(spi)),     # Target x-coordinates
                    valid_indices,           # Source x-coordinates
                    valid_values             # Source y-coordinates
                )
            else:
                print("Warning: All SPI values are NaN, interpolation not possible")
        spi = spi.astype(np.float32)
        # Calculate mean SPI
        mean_spi = np.nanmean(spi)
        min_spi = np.nanmin(spi) if not np.isnan(spi).all() else np.nan
        
        return mean_spi, min_spi, spi, None
    except Exception as e:
        print(f"Error calculating SPI from {file_path}: {str(e)}")
        return None, None, None, f"Error calculating SPI: {str(e)}"

def calculate_ani(ecg_clean, sample_rate=100, fs_interp=4):
    """Calculate ANI from cleaned ECG data"""
    L_W = 64 * sample_rate  # 64-second window
    L_B = 16 * fs_interp  # 16-second window
    
    Lecg_sec = math.floor(len(ecg_clean)/sample_rate)
    if Lecg_sec <= 64:
        return None, "ECG recording too short for ANI calculation (< 64 seconds)"

    # Calculate area between envelopes (normalized to 16-second window)
    ANI = []
    for i in range(Lecg_sec):
        start_idx = i * sample_rate
        ecg64 = ecg_clean[start_idx:start_idx+L_W+1]
        try:
            _, info_pk = nk.ecg_peaks(ecg64, sampling_rate=sample_rate)
            upper_envelope, lower_envelope, _ = calculate_area_segment(info_pk["ECG_R_Peaks"], sample_rate, fs_interp) # AUC_total
            areas = []
            # for j in range(4):
            #     area = np.trapz(upper_envelope[j*L_B:(j+1)*L_B+1] - lower_envelope[j*L_B:(j+1)*L_B+1], dx=1/fs_interp)
            #     areas.append(area.item())
            # ANI.append(100 * (5.1 * min(areas) + 1.2) / 12.8)
            area = np.trapz(upper_envelope - lower_envelope, dx=1/fs_interp)
            areas.append(area.item())
            ANI.append(100 * sum(areas) / 12.8)
        except:
            ANI.append(0)
    ANI = np.array(ANI, dtype=np.float32)
    ANI[np.isnan(ANI)] = 0
    return ANI, None