import numpy as np

from harnesses.studio.sync_audio import SR, find_offset


def test_cross_correlation_recovers_offset():
    rng = np.random.default_rng(0)
    speech = rng.standard_normal(SR * 12) * np.repeat(rng.random(12 * 20) > 0.5, SR // 20)  # bursty "speech"
    offset = 0.412
    pad = int(offset * SR)
    cam = speech + 0.3 * rng.standard_normal(len(speech))           # noisy phone mic
    mic = np.concatenate([np.zeros(pad), speech * 0.5])[: len(speech)]  # mic started 412 ms earlier
    est, conf = find_offset(cam.astype(np.float32), mic.astype(np.float32))
    assert abs(est - offset) < 0.005
    assert conf > 0.15
