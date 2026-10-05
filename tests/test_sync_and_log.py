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


def test_log_analyze(tmp_path, monkeypatch):
    from harnesses.studio import content_log
    monkeypatch.setattr(content_log, "LOG", tmp_path / "log.csv")
    import csv
    with (tmp_path / "log.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=content_log.FIELDS)
        w.writeheader()
        for ht, watch in [("mistake", 60), ("mistake", 58), ("result_first", 30), ("result_first", 28)]:
            w.writerow({**{k: "" for k in content_log.FIELDS}, "hook_type": ht, "avg_watch_pct": watch, "views": 100, "pillar": "build-in-public", "length_s": "30"})
    res = content_log.analyze()
    assert any("'mistake' gets 2.0×" in f for f in res["findings"])
