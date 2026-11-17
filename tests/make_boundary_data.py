#!/usr/bin/env python3
"""Generates the 'vfr-boundary' regression material: a short VFR segment whose
head AND tail are non-zero, with the destination audio advanced by a negative
offset (0.15s) so subtitle events are shifted before t=0 (head crop) and exactly
onto the last destination frame (tail boundary).

Everything is deterministic (fixed seed), so the material is reproducible.
"""
import os
import wave

import numpy as np

SAMPLE_RATE = 12000          # sushi's internal rate: no resampling, sample-exact shift
SRC_SECONDS = 30.0
OFFSET_SECONDS = -0.15       # dst audio = src audio advanced by 0.15s (negative shift)
OFFSET_SAMPLES = int(OFFSET_SECONDS * SAMPLE_RATE)  # -1800
FPS = 24000.0 / 1001.0
SEED = 20161118

# (start, end) in seconds, centisecond-aligned; durations exceed --max-ts-duration
# so every line is its own search group
EVENTS = [
    (0.00, 1.20),    # head line: shifts to a negative start, must be cropped to 0
    (2.50, 3.90),
    (5.00, 6.40),
    (7.50, 8.80),
    (10.00, 11.50),
    (12.50, 14.00),
    (15.00, 16.40),
    (17.50, 19.00),
    (20.00, 21.50),
    (22.50, 24.00),
    (25.00, 26.40),
    (28.50, 30.00),  # tail line: shifted end lands exactly on the last dst frame
]

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, 'data', 'vfr-boundary')


def format_ass_time(seconds):
    cs = int(round(seconds * 100))
    return '{0}:{1:02d}:{2:02d}.{3:02d}'.format(cs // 360000, (cs // 6000) % 60, (cs // 100) % 60, cs % 100)


def write_wav(path, samples):
    with wave.open(path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(samples.tobytes())


def script_text(events):
    lines = [
        '[Script Info]',
        'Title: vfr-boundary regression',
        '',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        'Style: Default,Arial,36,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,1.7,0,2,0,0,28,1',
        '',
        '[Events]',
        'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
    ]
    for idx, (start, end) in enumerate(events):
        lines.append('Dialogue: 0,{0},{1},Default,,0,0,0,,Boundary line {2}'.format(
            format_ass_time(start), format_ass_time(end), idx))
    return '\n'.join(lines) + '\n'


def keyframes_text(frame_count, step=24):
    # SCXviD 2pass log: frame N is described by line N+3, keyframes start with 'i'
    lines = ['# XviD 2pass stat file (core 50)', '# frame count: {0}'.format(frame_count), '#']
    lines += ['i' if f % step == 0 else 'p' for f in range(frame_count)]
    return '\n'.join(lines) + '\n'


def timecodes_text(last_frame):
    # v1 timecodes with an override block: VFR content, default fps for extrapolation
    return ('# timecode format v1\n'
            'Assume {0}\n'
            '0,119,29.970029970029969\n'
            '120,{1},{0}\n').format(FPS, last_frame)


def main():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    # source: full-band deterministic noise, non-zero at the very first sample
    rng = np.random.RandomState(SEED)
    src = (rng.standard_normal(int(SRC_SECONDS * SAMPLE_RATE)) * 5000).astype('<i2')
    # destination: advanced by the negative offset, non-zero up to the last sample
    dst = src[-OFFSET_SAMPLES:] if OFFSET_SAMPLES else src
    dst_seconds = len(dst) / float(SAMPLE_RATE)

    write_wav(os.path.join(OUT_DIR, 'src.wav'), src)
    write_wav(os.path.join(OUT_DIR, 'dst.wav'), dst)

    # subtitles and the ideal output: shifted by the offset, cropped to [0, dst]
    write_file(os.path.join(OUT_DIR, 'script.ass'), script_text(EVENTS))
    ideal = [(max(start + OFFSET_SECONDS, 0.0), min(end + OFFSET_SECONDS, dst_seconds))
             for start, end in EVENTS]
    write_file(os.path.join(OUT_DIR, 'ideal.ass'), script_text(ideal))

    # keyframes every 24 frames; dst kf times equal src kf times + offset, so
    # keyframe correction is a no-op and the ideal output stays exact
    src_frames = int(SRC_SECONDS * FPS) + 1
    dst_frames = int(dst_seconds * FPS) + 1
    write_file(os.path.join(OUT_DIR, 'src.keyframes.txt'), keyframes_text(src_frames))
    write_file(os.path.join(OUT_DIR, 'dst.keyframes.txt'), keyframes_text(dst_frames))

    # VFR timecodes; the defined range ends before the stream does, so the tail
    # line exercises extrapolation past the last frame
    write_file(os.path.join(OUT_DIR, 'src.timecodes.txt'), timecodes_text(src_frames - 120))
    write_file(os.path.join(OUT_DIR, 'dst.timecodes.txt'), timecodes_text(dst_frames - 120))

    print('Generated boundary material in {0}'.format(OUT_DIR))
    print('src: {0:.2f}s, dst: {1:.2f}s, offset: {2}s, events: {3}'.format(
        SRC_SECONDS, dst_seconds, OFFSET_SECONDS, len(EVENTS)))


def write_file(path, text):
    with open(path, 'w') as f:
        f.write(text)


if __name__ == '__main__':
    main()
