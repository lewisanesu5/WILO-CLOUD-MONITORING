"""
fault_motor_winding_failure.py
==============================
Fault simulation: MOTOR WINDING FAILURE

Physical description
--------------------
Progressive insulation breakdown in stator windings.
Stages: inter-turn short → coil-to-coil short → phase-to-ground fault →
catastrophic failure.

Inter-turn shorts create a circulating current loop within the affected coil,
reducing effective turns, increasing winding temperature, and producing
asymmetric magnetic flux in the air gap. This flux asymmetry drives
torque pulsations at 2× supply frequency (100 Hz) and its harmonics.

As the fault worsens, arcing events begin - these appear as high-kurtosis
current spikes and crackling audio bursts.

Sensor signatures
-----------------
Current [LEAD, lag=0]
  • Phase imbalance grows - neutral current rises
  • Sidebands appear at f_supply ± slip harmonics
  • Impulsive spikes at arcing events (high kurtosis)
  • Mean ↑ (reduced impedance in shorted turns draws more current)
  • Skewness ↑↑ (arcing spikes are always positive)

Audio [lag=1]
  • Arcing/buzzing at 100 Hz (2× supply) - electrical origin
  • Crackling bursts at arc ignition events
  • Kurtosis ↑↑ from crackle impulses
  • Top frequency = 100 Hz, growing harmonics at 200 Hz, 300 Hz

Acceleration [lag=3]
  • Magnetic imbalance → torque asymmetry at 100 Hz
  • Vibration at 2× supply frequency builds
  • Top frequency shifts from 12.25 Hz to 100 Hz as fault develops
  • Range ↑, kurtosis ↑ from torque shocks
"""

import os
import math
import random
from datetime import datetime

from base_motor import (
    MOTOR, SAMPLE_RATE, N_SAMPLES, TOTAL_UPLOADS,
    sensor_deviation, make_timestamps, gaussian_noise,
    sinusoid, add_impulses, amplitude_modulate,
    save_max_min_csvs, run_fault_simulation,
)

FAULT_NAME = 'motor_winding_failure'

CURRENT_LAG = random.randint(0, 1)
AUDIO_LAG   = random.randint(1, 2)
ACCEL_LAG   = random.randint(2, 4)


# ---------------------------------------------
# CURRENT GENERATOR
# ---------------------------------------------
def generate_current(upload_num: int, onset: int,
                     data_dir: str, logger) -> None:
    """
    Current leads with lag=0.

    Key signatures:
      • Reduced winding impedance → mean current rises
      • Phase imbalance modelled as asymmetric amplitude modulation
      • Sidebands at 50 ± 1 Hz (slip sidebands from asymmetric flux)
      • Arcing impulse spikes - always positive, high kurtosis
      • Late stage: abrupt surge before protection trip
    """
    dev = sensor_deviation(upload_num, onset, lag=CURRENT_LAG, steepness=0.44)
    ts  = make_timestamps(datetime.now())

    rated  = MOTOR['rated_current_a']     # 375 A
    f_sup  = MOTOR['f_supply']            # 50 Hz
    f_rot  = MOTOR['f_rot']              # 12.25 Hz
    slip   = MOTOR['slip']               # 0.02
    f_slip = f_sup * slip                # 1.0 Hz slip frequency

    # Healthy baseline
    noise_sigma = rated * 0.004
    signal = [rated + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal, sinusoid(f_sup, rated * 0.08))]

    if dev < 0.01:
        save_max_min_csvs('current', data_dir, ts, signal)
        return

    # -- Mean current rise (shorted turns draw more current) --
    # Max +35% over rated at critical stage
    dc_rise = rated + dev * rated * 0.35

    # -- Supply component --
    sig_sup = sinusoid(f_sup, rated * 0.08)

    # -- Sidebands at 50 ± slip_freq (asymmetric rotor flux) --
    sideband_amp = rated * dev * 0.12
    sig_sb_lower = sinusoid(f_sup - f_slip, sideband_amp)
    sig_sb_upper = sinusoid(f_sup + f_slip, sideband_amp)

    # -- Phase imbalance: amplitude modulation at 2× slip --
    # Simulates unequal phase currents beating at 2sf
    imbalance_depth = dev * 0.22
    mod_signal = [dc_rise + v + ss + sl + su
                  for v, ss, sl, su
                  in zip(gaussian_noise(rated * 0.006),
                         sig_sup, sig_sb_lower, sig_sb_upper)]
    mod_signal = amplitude_modulate(mod_signal,
                                    mod_freq=2 * f_slip,
                                    mod_depth=imbalance_depth)

    signal = mod_signal

    # -- Arcing impulse spikes (always positive - arcs are unipolar) --
    if dev > 0.15:
        # Arc rate increases with fault severity - 0.5 to 8 arcs/sec
        arc_rate = 0.5 + dev * 7.5
        arc_mag  = rated * dev * 2.80    # arcs can be 3× rated current
        n = len(signal)
        fs = SAMPLE_RATE
        interval = max(1, int(fs / arc_rate))
        i = random.randint(0, interval)
        while i < n:
            mag = arc_mag * random.uniform(0.6, 1.4)
            # Arcs are sharp spikes with fast decay
            for j in range(i, min(i + int(0.015 * fs), n)):
                signal[j] += abs(mag) * (0.70 ** (j - i))
            i += interval + random.randint(-interval // 3, interval // 3)

    # -- Late-stage surge (dev > 0.85): protection is about to trip --
    if dev > 0.85:
        surge_factor = (dev - 0.85) / 0.15
        signal = [s * (1.0 + surge_factor * 0.45) for s in signal]

    # Physical ceiling: 2× rated (protection should have tripped)
    signal = [min(s, rated * 2.2) for s in signal]

    save_max_min_csvs('current', data_dir, ts, signal)
    logger.info(f'  [current] dev={dev:.3f}  DC={dc_rise:.0f}A  '
                f'sideband={sideband_amp:.1f}A  '
                f'arc_rate={0.5+dev*7.5:.1f}/s' if dev > 0.15
                else f'  [current] dev={dev:.3f}  DC={dc_rise:.0f}A  no arcing yet')


# ---------------------------------------------
# AUDIO GENERATOR
# ---------------------------------------------
def generate_audio(upload_num: int, onset: int,
                   data_dir: str, logger) -> None:
    """
    Audio lags current by 1 upload.

    Key signatures:
      • 100 Hz buzzing (2× supply) - electrical origin, not mechanical
      • Crackling bursts at arc events
      • Harmonics at 200 Hz, 300 Hz grow
      • Kurtosis ↑↑ from crackle impulses
      • SPL rises moderately (82 → ~97 dB at critical)
    """
    dev = sensor_deviation(upload_num, onset, lag=AUDIO_LAG, steepness=0.44)
    ts  = make_timestamps(datetime.now())

    base_db = MOTOR['audio_db']    # 82 dB
    f_sup   = MOTOR['f_supply']    # 50 Hz

    # Healthy baseline
    noise_sigma = 1.2
    signal = [base_db + v for v in gaussian_noise(noise_sigma)]

    if dev < 0.01:
        save_max_min_csvs('audio', data_dir, ts, signal)
        return

    # -- SPL rise --
    max_db_rise = 15.0
    db_level    = base_db + dev * max_db_rise

    # -- 100 Hz electrical buzz (dominant) --
    buzz_100 = (db_level - base_db) * 0.70
    buzz_200 = (db_level - base_db) * 0.20
    buzz_300 = (db_level - base_db) * 0.10

    sig_100 = sinusoid(f_sup * 2, buzz_100)
    sig_200 = sinusoid(f_sup * 4, buzz_200)
    sig_300 = sinusoid(f_sup * 6, buzz_300)

    noise_broadband = gaussian_noise(1.5 + dev * 3.0)

    signal = [db_level * 0.04 + v + s1 + s2 + s3
              for v, s1, s2, s3
              in zip(noise_broadband, sig_100, sig_200, sig_300)]

    # -- Crackling arc audio bursts --
    if dev > 0.12:
        crackle_rate = 1.0 + dev * 9.0    # 1-10 crackles/sec
        crackle_mag  = db_level * 0.22 * dev
        signal = add_impulses(signal, rate=crackle_rate,
                              magnitude=crackle_mag, decay=0.55)

    signal = [min(s, 110.0) for s in signal]

    save_max_min_csvs('audio', data_dir, ts, signal)
    logger.info(f'  [audio]   dev={dev:.3f}  SPL~{db_level:.1f}dB  '
                f'buzz_100={buzz_100:.1f}  crackle_rate~{1.0+dev*9.0:.1f}/s'
                if dev > 0.12 else
                f'  [audio]   dev={dev:.3f}  SPL~{db_level:.1f}dB  no crackling yet')


# ---------------------------------------------
# ACCELERATION GENERATOR
# ---------------------------------------------
def generate_acceleration(upload_num: int, onset: int,
                           data_dir: str, logger) -> None:
    """
    Acceleration lags current by 3 uploads.

    Key signatures:
      • Magnetic imbalance → torque pulsation at 100 Hz (2× supply)
      • Top frequency shifts from 12.25 Hz (rotational) to 100 Hz
      • Range ↑, kurtosis ↑ from torque shocks at arc events
      • Overall RMS rise moderate compared to vibration anomaly fault
    """
    dev = sensor_deviation(upload_num, onset, lag=ACCEL_LAG, steepness=0.44)
    ts  = make_timestamps(datetime.now())

    base_g = MOTOR['accel_rms_g']    # 0.50 g
    f_rot  = MOTOR['f_rot']          # 12.25 Hz
    f_sup  = MOTOR['f_supply']       # 50 Hz

    # Healthy baseline
    noise_sigma = base_g * 0.10
    signal = [base_g * 0.04 + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal, sinusoid(f_rot, base_g * 0.28))]

    if dev < 0.01:
        save_max_min_csvs('acceleration', data_dir, ts, signal)
        return

    # -- Rotational component (always present) --
    sig_rot = sinusoid(f_rot, base_g * 0.28)

    # -- 100 Hz torque pulsation component - grows with dev --
    # This is the key electrical-origin vibration signature
    torque_100_amp = base_g * dev * 1.60
    torque_200_amp = base_g * dev * 0.55
    sig_100 = sinusoid(f_sup * 2, torque_100_amp)
    sig_200 = sinusoid(f_sup * 4, torque_200_amp)

    # Broadband noise
    noise_sigma_fault = base_g * (0.10 + dev * 0.45)
    noise_fault = gaussian_noise(noise_sigma_fault)

    signal = [base_g * 0.04 + v + r + t1 + t2
              for v, r, t1, t2
              in zip(noise_fault, sig_rot, sig_100, sig_200)]

    # -- Torque shock impulses at arc events --
    if dev > 0.20:
        shock_rate = 0.8 + dev * 5.0
        shock_mag  = base_g * dev * 1.20
        signal = add_impulses(signal, rate=shock_rate,
                              magnitude=shock_mag, decay=0.72)

    save_max_min_csvs('acceleration', data_dir, ts, signal)
    logger.info(f'  [accel]   dev={dev:.3f}  100Hz={torque_100_amp:.3f}g  '
                f'200Hz={torque_200_amp:.3f}g')


# ---------------------------------------------
# COMBINED GENERATE FUNCTION
# ---------------------------------------------
def generate_all(upload_num: int, onset: int,
                 data_dir: str, logger) -> bool:
    generate_current(upload_num, onset, data_dir, logger)
    generate_audio(upload_num, onset, data_dir, logger)
    generate_acceleration(upload_num, onset, data_dir, logger)

    # Motor winding failure threshold: current dev >= 0.85 (insulation breakdown / arcing)
    _dev = sensor_deviation(upload_num, onset, lag=CURRENT_LAG, steepness=0.44)
    return _dev >= 0.85


# ---------------------------------------------
# ENTRY POINT
# ---------------------------------------------
if __name__ == '__main__':
    run_fault_simulation(
        fault_name    = FAULT_NAME,
        generate_fn   = generate_all,
        sleep_seconds = 30,
    )
