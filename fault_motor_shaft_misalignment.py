"""
fault_motor_shaft_misalignment.py
==================================
Simulates angular/parallel shaft misalignment between motor and pump.

Physical progression:
  Misalignment forces the shaft to flex on every revolution, creating:
    - Strong 1× rotational (parallel misalignment)
    - Strong 2× rotational (angular misalignment - dominant symptom)
    - Sometimes 3× rotational at severe misalignment
    - Axial vibration (angular misalignment pushes/pulls axially)
    - Coupling wear → looseness → broadband noise later
    - Bearing overload from radial/axial forces → secondary bearing wear

  Progression: minor offset → coupling distress → bearing loading → fatigue crack

  Motor: 735 RPM → f_rot = 12.25 Hz
  Key vibration frequencies: 12.25 Hz (1×), 24.5 Hz (2×), 36.75 Hz (3×)

Sensor lead/lag:
  Acceleration → leads (vibration is the primary symptom)
  Current      → lags 3 uploads (cyclic load variation shows in current)
  Audio        → lags 4 uploads (whining at rotational harmonics)

Key statistical signatures:
  - Acceleration: top freqs = 12.25 Hz AND 24.5 Hz (both present = misalignment),
                  range ↑↑, kurtosis ↑ (coupling impacts)
  - Current:      range ↑, skewness ↑ (cyclic load variation)
  - Audio:        top freq = 12.25 Hz or 24.5 Hz, mean dB ↑
"""

import math, random
from datetime import datetime
from base_motor import (MOTOR, N_SAMPLES, SAMPLE_RATE, LOCAL_DATA_DIR,
                         sensor_deviation, sinusoid, add_impulses,
                         save_max_min_csvs, make_timestamps,
                         run_fault_simulation)

FAULT_NAME = 'motor_shaft_misalignment'

F_ROT = MOTOR['f_rot']    # 12.25 Hz
F_2X  = MOTOR['f_2x']     # 24.50 Hz
F_3X  = 3 * F_ROT          # 36.75 Hz

ACCEL_LAG   = random.randint(0, 1)
CURRENT_LAG = random.randint(2, 4)
AUDIO_LAG   = random.randint(3, 5)



def generate(upload_num: int, onset: int, data_dir: str, logger):
    d_accel   = sensor_deviation(upload_num, onset, ACCEL_LAG,   steepness=0.42)
    d_current = sensor_deviation(upload_num, onset, CURRENT_LAG, steepness=0.38)
    d_audio   = sensor_deviation(upload_num, onset, AUDIO_LAG,   steepness=0.36)

    fs  = SAMPLE_RATE
    n   = N_SAMPLES
    ts  = make_timestamps(datetime.now(), n, fs)
    I_r = MOTOR['rated_current_a']

    # -- ACCELERATION ---------------------------------------------------------
    accel = [MOTOR['accel_rms_g'] + random.gauss(0, 0.06) for _ in range(n)]
    rot1x = sinusoid(F_ROT, 0.15)
    accel = [accel[i] + rot1x[i] for i in range(n)]

    if d_accel > 0.01:
        # 1× and 2× both grow; 2× grows faster (more indicative of misalignment)
        amp_1x = d_accel * 2.0    # g
        amp_2x = d_accel * 3.5    # g - 2× dominates in angular misalignment
        amp_3x = d_accel * 1.0    # g - appears at severe misalignment

        vib_1x = sinusoid(F_ROT, amp_1x)
        vib_2x = sinusoid(F_2X,  amp_2x, phase=math.pi * 0.3)
        vib_3x = sinusoid(F_3X,  amp_3x * max(0, d_accel - 0.5))  # only late stage
        accel = [accel[i] + vib_1x[i] + vib_2x[i] + vib_3x[i]
                 for i in range(n)]

        # Coupling wear impulses (once per revolution, grows with misalignment)
        coupling_impacts = sinusoid(F_ROT, 0)   # placeholder
        accel = add_impulses(accel, F_ROT, d_accel * 1.5, decay=0.60)

        # Broadband rise from coupling distress
        accel = [accel[i] + random.gauss(0, d_accel * 0.20)
                 for i in range(n)]

        # Axial vibration component (angular misalignment) - modelled as
        # an additional 1× with phase offset (axial plane)
        axial = sinusoid(F_ROT, d_accel * 1.8, phase=math.pi / 2)
        accel = [accel[i] + axial[i] for i in range(n)]

    save_max_min_csvs('acceleration', data_dir, ts, accel)
    logger.info(f'  Accel  dev={d_accel:.3f}  '
                f'peak={max(accel):.3f}g  rms={math.sqrt(sum(v**2 for v in accel)/n):.3f}g')

    # -- CURRENT --------------------------------------------------------------
    # Cyclic load variation: misalignment causes torque to vary once/twice per revolution
    # Motor compensates by drawing varying current at 1× and 2× rotational
    current = [I_r + random.gauss(0, 2.5) for _ in range(n)]
    fund    = sinusoid(50, I_r * 0.08)
    current = [current[i] + fund[i] for i in range(n)]

    if d_current > 0.01:
        # 1× and 2× rotational current modulation
        mod_1x = sinusoid(F_ROT, d_current * I_r * 0.04)
        mod_2x = sinusoid(F_2X,  d_current * I_r * 0.06)
        current = [current[i] + mod_1x[i] + mod_2x[i] for i in range(n)]

        # Mean current rises due to extra friction/load from misalignment
        extra_load = I_r * d_current * 0.08
        current = [current[i] + extra_load for i in range(n)]

        current = [current[i] + random.gauss(0, d_current * 3.0)
                   for i in range(n)]

    save_max_min_csvs('current', data_dir, ts, current)
    logger.info(f'  Current dev={d_current:.3f}  '
                f'peak={max(current):.1f}A  mean={sum(current)/n:.1f}A')

    # -- AUDIO ----------------------------------------------------------------
    audio = [MOTOR['audio_db'] + random.gauss(0, 1.2) for _ in range(n)]
    h50   = sinusoid(50, 4.0)
    h100  = sinusoid(100, 1.8)
    audio = [audio[i] + h50[i] + h100[i] for i in range(n)]

    if d_audio > 0.01:
        # Whining/rumbling at 1× and 2× rotational
        rot_whine_1x = sinusoid(F_ROT, d_audio * 5.0)
        rot_whine_2x = sinusoid(F_2X,  d_audio * 8.0)   # 2× more prominent
        audio = [audio[i] + rot_whine_1x[i] + rot_whine_2x[i]
                 for i in range(n)]

        # Coupling knock - impulsive at rotational frequency
        audio = add_impulses(audio, F_ROT, d_audio * 5.0, decay=0.55)

        # Overall dB rise
        audio = [audio[i] + d_audio * 5.0 + random.gauss(0, 1.5)
                 for i in range(n)]

    save_max_min_csvs('audio', data_dir, ts, audio)
    logger.info(f'  Audio  dev={d_audio:.3f}  '
                f'mean={sum(audio)/n:.2f}dB  peak={max(audio):.2f}dB')

    # Motor shaft misalignment failure threshold: accel dev >= 0.80 (severe orbital imbalance)
    return d_accel >= 0.80


if __name__ == '__main__':
    run_fault_simulation(FAULT_NAME, generate,
                          sleep_seconds=30,
                          data_dir=LOCAL_DATA_DIR)
