import numpy as np
from scipy.signal import find_peaks, butter, filtfilt
from scipy.interpolate import interp1d

def calculate_area_segment(r_peaks, sampling_rate=100, fs_interp=4):
    """
    Calculate area segment from ECG signal
    
    Parameters:
    - r_peaks: array-like, R peak indices in the ECG signal
    - sampling_rate: int, sampling frequency in Hz
    - fs_interp: int, interpolation frequency in Hz
    
    Returns:
    - ani_value: float, ANI value between 0 and 100
    - visualization_data: dict, additional data for visualization
    """
    # Calculate R-R intervals
    rr_intervals = calculate_rr_intervals(r_peaks, sampling_rate)
    
    # Convert to evenly sampled time series
    rr_times, rr_interpolated = interpolate_rr(r_peaks, rr_intervals, sampling_rate, fs_interp)
    
    # Filter in HF band and analyze in time domain
    upper_envelope, lower_envelope, rr_hf = analyze_hf_time_domain(rr_interpolated, fs_interp)
    
    return upper_envelope, lower_envelope, rr_hf


def calculate_rr_intervals(r_peaks, sampling_rate):
    """Calculate R-R intervals in seconds"""
    rr_intervals = np.diff(r_peaks) / sampling_rate
    # Normalize
    rr_intervals = rr_intervals - np.mean(rr_intervals)
    rr_intervals = rr_intervals / np.sqrt(np.sum(rr_intervals**2))
    return rr_intervals

def interpolate_rr(r_peaks, rr_intervals, sampling_rate, fs_interp):
    """Interpolate RR intervals to create evenly sampled time series"""
    # Get timestamps for each R peak in seconds
    r_times = r_peaks / sampling_rate
    
    # Get timestamps for each RR interval (midpoint between R peaks)
    rr_times = r_times[:-1] + rr_intervals/2
    
    # Create evenly sampled time series through interpolation (4 Hz)
    t_interp = np.arange(0, 64+1/fs_interp, 1/fs_interp)
    
    interpolator = interp1d(rr_times, rr_intervals, kind='linear', bounds_error=False, fill_value='extrapolate')
        
    rr_interp = interpolator(t_interp)
    
    # Return both the timestamps and interpolated values
    return t_interp, rr_interp

def analyze_hf_time_domain(rr_interp, fs_interp):
    """
    Analyze HF band in time domain to calculate ANI
    
    Parameters:
    - rr_interp: Interpolated RR intervals
    - fs_interp: Interpolation frequency (Hz)
    
    Returns:
    - ani_value: calculated ANI value
    - upper_envelope: upper envelope of the signal
    - lower_envelope: lower envelope of the signal
    """
    # Apply high-pass filter to isolate HF band (0.15-0.4 Hz)
    nyquist = fs_interp / 2
    low = 0.15 / nyquist
    high = 0.4 / nyquist
    b, a = butter(2, [low, high], btype='band')
        
    rr_hf = filtfilt(b, a, rr_interp)
    
    # Find local maxima and minima to create the envelope
    max_peaks, _ = find_peaks(rr_hf)
    min_peaks, _ = find_peaks(-rr_hf)
    
    # Create envelopes by interpolating between peaks
    t = np.arange(len(rr_hf)) / fs_interp
    
    # Upper envelope
    upper_interp = interp1d(t[max_peaks], rr_hf[max_peaks], kind='linear', 
                           bounds_error=False, fill_value='extrapolate')
    upper_envelope = upper_interp(t)
    upper_envelope = np.clip(upper_envelope, -0.1, 0.1)  # Clip to [-0.1, 0.1]

    # Lower envelope
    lower_interp = interp1d(t[min_peaks], rr_hf[min_peaks], kind='linear',
                           bounds_error=False, fill_value='extrapolate')
    lower_envelope = lower_interp(t)
    lower_envelope = np.clip(lower_envelope, -0.1, 0.1)  # Clip to [-0.1, 0.1]
    
    return upper_envelope, lower_envelope, rr_hf