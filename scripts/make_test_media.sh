#!/usr/bin/env bash
# Recreate the synthetic test footage in tests/media/ (macOS `say` voice + test-pattern video).
# The script has a false start, fillers and pauses; the mic track starts 412 ms before the camera.
set -euo pipefail
cd "$(dirname "$0")/../tests/media"
say -v Samantha -r 175 -o speech.aiff "Um, this took me three hours instead of [[slnc 900]] This took me three hours instead of three weeks. [[slnc 800]] I rebuilt the whole onboarding flow today. [[slnc 1300]] Uh, the trick was letting Claude write the boring parts while I designed the flow. [[slnc 700]] Signups went from forty percent to seventy percent completion. [[slnc 1100]] Follow. Day thirteen tomorrow."
ffmpeg -hide_banner -loglevel error -y -i speech.aiff -af "adelay=1612:all=1,apad=pad_dur=2,aresample=48000" -ac 1 -c:a pcm_s16le mic.wav
ffmpeg -hide_banner -loglevel error -y -f lavfi -i "testsrc2=size=1080x1920:rate=30" -i speech.aiff \
  -f lavfi -i "anoisesrc=color=pink:amplitude=0.02:sample_rate=48000" \
  -filter_complex "[1:a]adelay=1200:all=1,aresample=48000,lowpass=f=6000,volume=0.8[s];[s][2:a]amix=inputs=2:duration=first:normalize=0,apad=pad_dur=2[a]" \
  -map 0:v -map "[a]" -t 24.5 -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p -c:a aac cam.mp4
ffmpeg -hide_banner -loglevel error -y -f lavfi -i "mandelbrot=size=1080x1920:rate=30" -t 5 -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p broll.mp4
echo "tests/media: cam.mp4 (phone), mic.wav (separate mic, +412 ms), broll.mp4, transcript.srt (sidecar)"
