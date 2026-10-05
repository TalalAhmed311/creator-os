"""edl.json → OpenTimelineIO → out/project.fcpxml (+ out/project.otio) for DaVinci Resolve / Final Cut.

  python -m harnesses.studio.export_nle <project>

Timeline: V1 = camera cuts from raw/ (source media, not the render), A1 = cleaned voice (work/voice.wav,
already synced to camera time), V2 = rendered final for reference. Beat names become clip names and
graphics become markers, so the edit is easy to tweak by hand.
"""
from __future__ import annotations

import argparse

import opentimelineio as otio

from core.common import Project, get_logger, load_json, validate
from harnesses.studio.timeline import layout

log = get_logger("export_nle")


def _rt(sec: float, fps: float) -> otio.opentime.RationalTime:
    return otio.opentime.RationalTime(round(sec * fps), fps)


def _tr(start: float, dur: float, fps: float) -> otio.opentime.TimeRange:
    return otio.opentime.TimeRange(_rt(start, fps), _rt(dur, fps))


def build_timeline(project: Project) -> otio.schema.Timeline:
    edl = load_json(project.root / "edl.json")
    validate(edl, "edl")
    media = project.media()
    fps = edl["output"]["fps"]
    lay = layout(edl["segments"], fps)
    cam = (project.root / edl["sources"]["cam"]).resolve()
    voice = (project.work / "voice.wav").resolve()
    cam_dur = media["cam"]["duration"]

    tl = otio.schema.Timeline(name=project.id)
    tl.global_start_time = _rt(0, fps)
    v1 = otio.schema.Track(name="V1 camera", kind=otio.schema.TrackKind.Video)
    a1 = otio.schema.Track(name="A1 voice", kind=otio.schema.TrackKind.Audio)
    cam_ref = lambda: otio.schema.ExternalReference(target_url=cam.as_uri(), available_range=_tr(0, cam_dur, fps))  # noqa: E731
    voice_ref = lambda: otio.schema.ExternalReference(target_url=voice.as_uri(), available_range=_tr(0, cam_dur, fps))  # noqa: E731
    for i, s in enumerate(lay):
        name = f"{i + 1:02d} {s.get('beat') or 'cut'}"
        v1.append(otio.schema.Clip(name=name, media_reference=cam_ref(), source_range=_tr(s["in"], s["dur"], fps)))
        a1.append(otio.schema.Clip(name=name, media_reference=voice_ref(), source_range=_tr(s["in"], s["dur"], fps)))
    tl.tracks.extend([v1, a1])
    final = project.out / "final.mp4"
    if final.exists():
        v2 = otio.schema.Track(name="V2 rendered reference", kind=otio.schema.TrackKind.Video)
        total = lay[-1]["out_end"]
        v2.append(otio.schema.Clip(name="final render", source_range=_tr(0, total, fps),
                                   media_reference=otio.schema.ExternalReference(target_url=final.resolve().as_uri(), available_range=_tr(0, total, fps))))
        tl.tracks.append(v2)
    for g in edl["graphics"]:
        label = g.get("text") or g.get("spec") or g["type"]
        v1.markers.append(otio.schema.Marker(name=f"{g['type']}: {label}", marked_range=_tr(g["start"], max(1 / fps, g["end"] - g["start"]), fps)))
    return tl


def export(project: Project) -> str:
    tl = build_timeline(project)
    otio.adapters.write_to_file(tl, str(project.out / "project.otio"))
    out = project.out / "project.fcpxml"
    try:
        otio.adapters.write_to_file(tl, str(out), adapter_name="fcpx_xml")
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"fcpxml export failed ({e}); is otio-fcpx-xml-adapter installed?")
    log.info(f"→ {out.relative_to(project.root)} (+ project.otio)")
    return str(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    a = ap.parse_args(argv)
    export(Project(a.project))


if __name__ == "__main__":
    main()
