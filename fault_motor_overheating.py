"""
fault_motor_overheating.py
==========================
Simulates progressive thermal overload / overheating fault.

Physical progression:
  Class F insulation rated to 155°C (rise limited to Class B = 80°C over 40°C ambient).
  Overheating pathway:
    → Increased load / poor ventilation → winding temp rises
    → Winding resistance increases (copper: +0.39%/°C)
    → Higher resistance → higher I²R losses → more heat (thermal runaway)
    → Insulation softens → inter-turn leakage → partial discharge
    → Cooling fan struggles (if TEFC fan degrades from heat)
    → Thermal protection trips → brief recovery → re-overload cycle
    → Eventual insulation failure / winding short

  This script models the THERMAL LOADING phase before winding failure.
  Winding failure itself is a separate fault script.

Sensor lead/lag:
  Current      → leads (thermal loading shows as current rise first)
  Audio        → lags 5 uploads (cooling fan noise increases)
  Acceleration → lags 7 uploads (thermal expansion → slight imbalance)

Key statistical signatures:
  - Current:      mean ↑ gradually (resistance effect), range ↑, thermal trip events
                  → occasional sharp drops then re-surge (trip/restart signature)
  - Audio:        mean dB ↑ (fan working harder), broadband noise floor ↑
  - Acceleration: mean ↑ slightly, 1× rotational ↑ (thermal imbalance)
"""

import math, random
from datetime import datetime
from base_motor import (MOTOR, N_SAMPLES, SAMPLE_RATE, LOCAL_DATA_DIR,
                         sensor_deviation, gaussian_noise, sinusoid,
                         add_impulses, save_max_min_csvs, make_timestamps,
                         run_fault_simulation)

FAULT_NAME = 'motor_overheating'

CURRENT_LAG = random.randint(0, 1)
AUDIO_LAG   = random.randint(4, 6)
ACCEL_LAG   = random.randint(6, 8)


# Thermal trip signature: at high deviation, simulate thermal cutout events
# Motor trips (current drops to 0) then restarts after a few samples
TRIP_THRESHOLD_DEV = 0.75    # deviation at which trips start occurring


def generate(upload_num: int, onset: int, data_dir: str, logger):
    d_current = sensor_deviation(upload_num, onset, CURRENT_LAG, steepness=0.35)
    d_audio   = sensor_deviation(upload_num, onset, AUDIO_LAG,   steepness=0.32)
    d_accel   = sensor_deviation(upload_num, onset, ACCEL_LAG,   steepness=0.30)

    fs  = SAMPLE_RATE
    n   = N_SAMPLES
    ts  = make_timestamps(datetime.now(), n, fs)
    I_r = MOTOR['rated_current_a']
    F_r = MOTOR['f_rot']

    # ── CURRENT ──────────────────────────────────────────────────────────────
    # As temperature rises, winding resistance R increases → V = IR means
    # for constant V supply, if load is constant, I stays similar BUT
    # efficiency drops so motor draws more current to maintain output power.
    # Net effect: gradual current rise ~10–15% above rated at thermal limit.
    current = [I_r + random.gauss(0, 2.5) for _ in range(n)]
    fund    = sinusoid(50, I_r * 0.08)
    current = [current[i] + fund[i] for i in range(n)]

    if d_current > 0.01:
        # Gradual current increase due to thermal derating
        thermal_rise = I_r * d_current * 0.15   # up to 15% above rated
        current = [current[i] + thermal_rise for i in range(n)]

        # Increased noise / fluctuation as thermal stress increases
        current = [current[i] + random.gauss(0, d_current * 5.0)
                   for i in range(n)]

        # Thermal trip events at high deviation
        if d_current > TRIP_THRESHOLD_DEV:
            # Simulate 1–3 trip events within the 2-second window
            n_trips = random.randint(1, 2)
            trip_width = int(0.12 * fs)     # ~120ms trip + restart transient
            for _ in range(n_trips):
                trip_start = random.randint(0, n - trip_width - 1)
                # Current drops sharply
                for j in range(trip_start, min(trip_start + trip_width // 3, n)):
                    current[j] *= (1.0 - (j - trip_start) / (trip_width / 3))
                # Then surges on restart (inrush ~3× normal for brief moment)
                inrush_end = min(trip_start + trip_width, n)
                for j in range(trip_start + trip_width // 3, inrush_end):
                    t_norm = (j - trip_start - trip_width // 3) / (2 * trip_width / 3)
                    current[j] += I_r * 2.5 * math.exp(-t_norm * 5)

    save_max_min_csvs('current', data_dir, ts, current)
    logger.info(f'  Current dev={d_current:.3f}  '
                f'peak={max(current):.1f}A  mean={sum(current)/n:.1f}A')

    # ── AUDIO ────────────────────────────────────────────────────────────────
    # TEFC motor: cooling fan is integral. As windings heat up:
    # - Cooling demand increases but fan speed is fixed (no variable fan)
    # - Fan noise stays but overall machine noise rises (thermal expansion rattles)
    # - Partial discharge at high temp → faint crackling (captured by mic)
    audio = [MOTOR['audio_db'] + random.gauss(0, 1.2) for _ in range(n)]
    h50   = sinusoid(50, 4.0)
    h100  = sinusoid(100, 1.8)
    audio = [audio[i] + h50[i] + h100[i] for i in range(n)]

    if d_audio > 0.01:
        # Fan noise increase — broadband rise
        audio = [audio[i] + d_audio * 7.0 + random.gauss(0, 1.8)
                 for i in range(n)]

        # Thermal expansion causes casing resonance → slight tonal at ~350 Hz
        resonance = sinusoid(350, d_audio * 3.0)
        audio = [audio[i] + resonance[i] for i in range(n)]

        # Partial discharge crackling (high kurtosis, random)
        if d_audio > 0.5:
            audio = add_impulses(audio, d_audio * 15, d_audio * 4.0, decay=0.50)

    save_max_min_csvs('audio', data_dir, ts, audio)
    logger.info(f'  Audio  dev={d_audio:.3f}  '
                f'mean={sum(audio)/n:.2f}dB  peak={max(audio):.2f}dB')

    # ── ACCELERATION ─────────────────────────────────────────────────────────
    # Thermal expansion of rotor/shaft → slight mass imbalance → 1× vibration
    # Also: differential thermal expansion between rotor and stator
    # → air gap asymmetry → unbalanced magnetic pull → vibration
    accel = [MOTOR['accel_rms_g'] + random.gauss(0, 0.06) for _ in range(n)]
    rot1x = sinusoid(F_r, 0.15)
    accel = [accel[i] + rot1x[i] for i in range(n)]

    if d_accel > 0.01:
        # 1× rotational grows (thermal imbalance)
        thermal_imbalance = sinusoid(F_r, d_accel * 0.5)
        accel = [accel[i] + thermal_imbalance[i] for i in range(n)]

        # General broadband rise from increased mechanical stress
        accel = [accel[i] + random.gauss(0, d_accel * 0.15)
                 for i in range(n)]

        # At high deviation: thermal stress causes occasional structural microslip
        if d_accel > 0.6:
            accel = add_impulses(accel, d_accel * 2.0,
                                 d_accel * 0.4, decay=0.70)

    save_max_min_csvs('acceleration', data_dir, ts, accel)
    logger.info(f'  Accel  dev={d_accel:.3f}  '
                f'peak={max(accel):.3f}g  rms={math.sqrt(sum(v**2 for v in accel)/n):.3f}g')


if __name__ == '__main__':
    run_fault_simulation(FAULT_NAME, generate,
                          sleep_seconds=30,
                          data_dir=LOCAL_DATA_DIR)
