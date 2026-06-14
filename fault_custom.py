"""
fault_custom.py
===============
Fault simulation: CUSTOM FAULT
Composite: MOTOR OVERHEATING + PUMP CAVITATION (simultaneous)

Physical description
--------------------
This models a realistic compound failure scenario:
  A pump running with insufficient NPSH (net positive suction head) begins
  cavitating. The resulting efficiency loss forces the motor to work harder
  to maintain flow, generating excess heat. The thermal stress degrades
  winding insulation, accelerating into an overheating condition.

Both faults are present simultaneously but with different onset timings:
  • Cavitation begins first (onset = randomised as per run_fault_simulation)
  • Overheating onset is delayed by 6-10 uploads after cavitation
    (thermal mass of a 200kW motor means it takes time to heat up)

The challenge for the ML model is that the compound signature partially
masks individual fault features:
  • Current: rises (overheating) AND fluctuates (cavitation) simultaneously
  • Audio: crackling (cavitation) AND broadband hum rise (thermal fan noise)
  • Acceleration: broadband random (cavitation) AND slight 1× rise (thermal
    expansion imbalance from overheating)

This overlap makes it harder to classify and is intentional - the model
should learn that this is a distinct, more severe compound condition.

Sensor signatures
-----------------
Audio [LEAD, lag=0]
  • Cavitation crackling dominates early
  • Thermal fan noise adds broadband floor rise
  • Combined SPL higher than either fault alone (~98-103 dB peak)
  • Kurtosis high (crackle) but partially diluted by continuous thermal noise

Current [lag=1]
  • Net effect: rises due to overheating AND fluctuates due to cavitation
  • Mean ↑ (thermal) + Range ↑↑ (cavitation efficiency oscillation)
  • This combination - rising mean WITH high variance - is unique
  • At late stage: drops slightly as cavitation collapses hydraulic load
    but overheating keeps base current elevated - net ambiguity

Acceleration [lag=2]
  • Cavitation broadband impulses + thermal 1× rotational
  • Kurtosis ↑↑ (cavitation impulses)
  • Top frequency: 12.25 Hz (thermal imbalance grows over time)
  • Broadband floor elevated throughout
"""

import os
import math
import random
from datetime import datetime

from base_motor import (
    MOTOR, SAMPLE_RATE, N_SAMPLES, TOTAL_UPLOADS,
    sensor_deviation, make_timestamps, gaussian_noise,
    sinusoid, add_impulses,
    save_max_min_csvs, run_fault_simulation,
)

FAULT_NAME = 'custom_fault'

AUDIO_LAG   = random.randint(0, 1)
CURRENT_LAG = random.randint(1, 2)
ACCEL_LAG   = random.randint(2, 3)
THERMAL_LAG = random.randint(6, 10)

# Cavitation frequency bands
F_CAVITATION_LOW  = 120.0
F_CAVITATION_MID  = 220.0
F_CAVITATION_HIGH = 310.0


# ---------------------------------------------
# AUDIO GENERATOR
# ---------------------------------------------
def generate_audio(upload_num: int, onset: int,
                   data_dir: str, logger) -> None:
    """
    Audio leads with lag=0.

    Two overlapping contributions:
      1. Cavitation crackle/hiss (dominates early)
      2. Thermal fan noise rise (adds broadband floor, grows slowly)

    Combined SPL higher than either fault alone.
    Kurtosis initially high (cavitation), then partially diluted as
    continuous thermal noise fills in between crackle events.
    """
    # Cavitation develops from main onset
    dev_cav = sensor_deviation(upload_num, onset, lag=AUDIO_LAG, steepness=0.43)
    # Overheating thermal onset is delayed by THERMAL_LAG uploads after cavitation onset
    thermal_onset = onset + THERMAL_LAG
    dev_heat = sensor_deviation(upload_num, thermal_onset, lag=AUDIO_LAG, steepness=0.35)

    ts = make_timestamps(datetime.now())

    base_db = MOTOR['audio_db']    # 82 dB

    # Healthy baseline
    noise_sigma = 1.2
    signal = [base_db + v for v in gaussian_noise(noise_sigma)]

    if dev_cav < 0.01 and dev_heat < 0.01:
        save_max_min_csvs('audio', data_dir, ts, signal)
        return

    # -- Cavitation stages --
    cav_incipient  = min(dev_cav / 0.30, 1.0)
    cav_developed  = max(min((dev_cav - 0.30) / 0.45, 1.0), 0.0)
    cav_supercavit = max((dev_cav - 0.75) / 0.25, 0.0)

    # -- SPL: cavitation component --
    db_cav  = base_db + (cav_incipient * 3.0
                         + cav_developed * 9.0
                         + cav_supercavit * 5.0)

    # -- SPL: thermal fan noise component --
    # Fan noise is broadband, adds 4-8 dB at peak overheating
    db_heat = dev_heat * 8.0

    # Combined SPL (log-domain addition approximated linearly - close enough
    # for simulation where we're not doing exact acoustic physics)
    db_level = db_cav + db_heat * 0.70    # some masking effect

    # -- Cavitation broadband bands --
    cav_mid_amp  = base_db * 0.014 * (cav_incipient * 0.3 + cav_developed * 0.7)
    cav_high_amp = base_db * 0.010 * cav_developed
    sig_cav_mid  = sinusoid(F_CAVITATION_MID,  cav_mid_amp)
    sig_cav_high = sinusoid(F_CAVITATION_HIGH, cav_high_amp)

    # -- Thermal fan: broadband noise (no tonal component) --
    fan_broadband_sigma = dev_heat * 5.0

    # -- Combined broadband --
    broadband_sigma = 1.2 + dev_cav * 5.5 + fan_broadband_sigma
    noise_broadband = gaussian_noise(broadband_sigma)

    signal = [db_level * 0.04 + v + cm + ch
              for v, cm, ch
              in zip(noise_broadband, sig_cav_mid, sig_cav_high)]

    # -- Cavitation crackle impulses --
    if dev_cav > 0.05:
        crackle_rate = (3.0 * cav_incipient
                        + 18.0 * cav_developed
                        + 12.0 * cav_supercavit)
        crackle_mag  = db_level * (0.18 * cav_incipient
                                   + 0.12 * cav_developed
                                   + 0.07 * cav_supercavit)
        signal = add_impulses(signal, rate=crackle_rate,
                              magnitude=crackle_mag, decay=0.45)

    signal = [min(s, 110.0) for s in signal]

    save_max_min_csvs('audio', data_dir, ts, signal)
    logger.info(f'  [audio]   dev_cav={dev_cav:.3f}  dev_heat={dev_heat:.3f}  '
                f'SPL~{db_level:.1f}dB')


# ---------------------------------------------
# CURRENT GENERATOR
# ---------------------------------------------
def generate_current(upload_num: int, onset: int,
                     data_dir: str, logger) -> None:
    """
    Current lags audio by 1 upload.

    Compound current signature - unique combination:
      Overheating:  mean ↑ (resistance rise) - monotonic climb
      Cavitation:   mean fluctuates then drops (hydraulic load collapse)

    Net result:
      Early: mean rises (overheating dominates)
      Mid:   mean rises AND variance spikes (both active)
      Late:  mean partially pulled down by cavitation load loss
             but remains above normal due to thermal resistance increase
             - ambiguous mean level with very high variance
    """
    dev_cav  = sensor_deviation(upload_num, onset, lag=CURRENT_LAG, steepness=0.43)
    thermal_onset = onset + THERMAL_LAG
    dev_heat = sensor_deviation(upload_num, thermal_onset, lag=CURRENT_LAG, steepness=0.35)

    ts = make_timestamps(datetime.now())

    rated = MOTOR['rated_current_a']    # 375 A
    f_sup = MOTOR['f_supply']           # 50 Hz
    f_rot = MOTOR['f_rot']             # 12.25 Hz
    f_bpf = MOTOR['bpf']              # 73.5 Hz - blade pass (cavitation)

    # Healthy baseline
    noise_sigma = rated * 0.004
    signal = [rated + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal, sinusoid(f_sup, rated * 0.08))]

    if dev_cav < 0.01 and dev_heat < 0.01:
        save_max_min_csvs('current', data_dir, ts, signal)
        return

    # -- Overheating: gradual mean rise (resistance increase) --
    dc_heat_rise = dev_heat * rated * 0.18    # +18% max from thermal

    # -- Cavitation: load drop and variance --
    cav_load_drop = max((dev_cav - 0.40) / 0.35, 0.0) * rated * 0.12
    cav_variance  = dev_cav * 4.0    # variance multiplier

    # -- Net DC level --
    dc_level = rated + dc_heat_rise - cav_load_drop
    dc_level = max(dc_level, rated * 0.78)

    # -- Combined noise: overheating noise + cavitation efficiency fluctuation --
    variance_scale = 1.0 + cav_variance + dev_heat * 1.5
    noise_sigma_fault = rated * 0.004 * variance_scale

    # -- BPF modulation from cavitation --
    bpf_amp = rated * dev_cav * 0.035
    sig_bpf = sinusoid(f_bpf, bpf_amp)
    sig_sup = sinusoid(f_sup, rated * 0.08)

    signal = [dc_level + v + ss + sb
              for v, ss, sb
              in zip(gaussian_noise(noise_sigma_fault), sig_sup, sig_bpf)]

    # -- Air pocket spikes from cavitation --
    cav_developed = max(min((dev_cav - 0.30) / 0.45, 1.0), 0.0)
    if cav_developed > 0.20:
        spike_rate = 2.0 + cav_developed * 8.0
        spike_mag  = rated * 0.10 * cav_developed
        signal = add_impulses(signal, rate=spike_rate,
                              magnitude=spike_mag, decay=0.60)

    signal = [min(s, rated * MOTOR['locked_rotor_mult'] * 0.60) for s in signal]

    save_max_min_csvs('current', data_dir, ts, signal)
    logger.info(f'  [current] dev_cav={dev_cav:.3f}  dev_heat={dev_heat:.3f}  '
                f'DC={dc_level:.1f}A  variance_scale={variance_scale:.2f}')


# ---------------------------------------------
# ACCELERATION GENERATOR
# ---------------------------------------------
def generate_acceleration(upload_num: int, onset: int,
                           data_dir: str, logger) -> None:
    """
    Acceleration lags audio by 2 uploads.

    Two overlapping vibration sources:
      1. Cavitation: random broadband impulses (high kurtosis)
      2. Overheating: thermal expansion → shaft bow → 1× rotational grows

    The 1× rotational component growing over time while broadband kurtosis
    is also elevated creates a mixed signature the ML model must recognise
    as distinct from pure cavitation (no 1× growth) and pure overheating
    (no broadband kurtosis).
    """
    dev_cav  = sensor_deviation(upload_num, onset, lag=ACCEL_LAG, steepness=0.43)
    thermal_onset = onset + THERMAL_LAG
    dev_heat = sensor_deviation(upload_num, thermal_onset, lag=ACCEL_LAG, steepness=0.35)

    ts = make_timestamps(datetime.now())

    base_g = MOTOR['accel_rms_g']    # 0.50 g
    f_rot  = MOTOR['f_rot']          # 12.25 Hz
    f_bpf  = MOTOR['bpf']           # 73.5 Hz

    # Healthy baseline
    noise_sigma = base_g * 0.10
    signal = [base_g * 0.04 + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal, sinusoid(f_rot, base_g * 0.28))]

    if dev_cav < 0.01 and dev_heat < 0.01:
        save_max_min_csvs('acceleration', data_dir, ts, signal)
        return

    cav_incipient  = min(dev_cav / 0.30, 1.0)
    cav_developed  = max(min((dev_cav - 0.30) / 0.45, 1.0), 0.0)
    cav_supercavit = max((dev_cav - 0.75) / 0.25, 0.0)

    # -- 1× Rotational: baseline + thermal bow growth --
    # Thermal bow: shaft expands unevenly → growing 1× imbalance
    rot_amp = base_g * (0.28 + dev_heat * 0.85)
    sig_rot = sinusoid(f_rot, rot_amp)

    # -- BPF mild (impeller still running) --
    bpf_amp = base_g * 0.06 * (1.0 - cav_supercavit * 0.5)
    sig_bpf = sinusoid(f_bpf, bpf_amp)

    # -- Broadband from cavitation --
    broadband_rms = base_g * (0.10
                               + dev_cav * 1.10
                               + dev_heat * 0.20)
    noise_broad = gaussian_noise(broadband_rms)

    signal = [base_g * 0.04 + v + r + b
              for v, r, b in zip(noise_broad, sig_rot, sig_bpf)]

    # -- Cavitation collapse impulses --
    if dev_cav > 0.05:
        collapse_rate = (5.0 * cav_incipient
                         + 22.0 * cav_developed
                         + 35.0 * cav_supercavit)
        collapse_mag  = base_g * (0.32 * cav_incipient
                                  + 0.50 * cav_developed
                                  + 0.40 * cav_supercavit)
        signal = add_impulses(signal, rate=collapse_rate,
                              magnitude=collapse_mag, decay=0.50)

    rms_est = (sum(s**2 for s in signal) / len(signal)) ** 0.5
    save_max_min_csvs('acceleration', data_dir, ts, signal)
    logger.info(f'  [accel]   dev_cav={dev_cav:.3f}  dev_heat={dev_heat:.3f}  '
                f'RMS~{rms_est:.3f}g  rot={rot_amp:.3f}g')


# ---------------------------------------------
# COMBINED GENERATE FUNCTION
# ---------------------------------------------
def generate_all(upload_num: int, onset: int,
                 data_dir: str, logger) -> bool:
    generate_audio(upload_num, onset, data_dir, logger)
    generate_current(upload_num, onset, data_dir, logger)
    generate_acceleration(upload_num, onset, data_dir, logger)

    # Custom fault failure threshold: audio dev >= 0.75
    _dev = sensor_deviation(upload_num, onset, lag=AUDIO_LAG, steepness=0.43)
    return _dev >= 0.75


# ---------------------------------------------
# ENTRY POINT
# ---------------------------------------------
if __name__ == '__main__':
    run_fault_simulation(
        fault_name    = FAULT_NAME,
        generate_fn   = generate_all,
        sleep_seconds = 30,
    )
