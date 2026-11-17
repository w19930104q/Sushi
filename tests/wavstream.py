import os
import tempfile
import unittest
import wave

import numpy as np

from wav import WavStream


def write_noise_wav(path, seconds, sample_rate=12000, seed=1234):
    rng = np.random.RandomState(seed)
    samples = (rng.standard_normal(int(seconds * sample_rate)) * 5000).astype('<i2')
    with wave.open(path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.tobytes())


class WavStreamContractTestCase(unittest.TestCase):
    """Contracts for timestamp sampling and window padding."""

    SAMPLE_RATE = 12000

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()
        cls.wav_path = os.path.join(cls._tmp, 'noise.wav')
        write_noise_wav(cls.wav_path, 5.0, cls.SAMPLE_RATE)
        cls.stream = WavStream(cls.wav_path, sample_rate=cls.SAMPLE_RATE, sample_type='uint8')

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.wav_path)
        os.rmdir(cls._tmp)

    def test_sample_for_time_uses_floor_for_negative_offsets(self):
        # int() truncates towards zero, shifting negative times by one sample;
        # the unified contract is floor semantics on both sides of zero
        padding = self.stream.padding_size
        self.assertEqual(padding - 2, self.stream._get_sample_for_time(-0.0001))
        self.assertEqual(padding - 1, self.stream._get_sample_for_time(-1.0 / self.SAMPLE_RATE))
        self.assertEqual(padding, self.stream._get_sample_for_time(0))
        self.assertEqual(padding + 1, self.stream._get_sample_for_time(0.0001))

    def test_find_substream_locates_pattern(self):
        pattern = self.stream.get_substream(0.5, 0.7)
        diff, found = self.stream.find_substream(pattern, window_center=0.6, window_size=1)
        self.assertAlmostEqual(0.5, found, places=4)
        self.assertLess(diff, 0.01)

    def test_find_substream_window_is_padded_symmetrically(self):
        # a pattern starting before t=0 (negative offset) must be found at its
        # actual position - the window extends by PADDING_SECONDS on BOTH sides
        pattern = self.stream.get_substream(-0.2, 0.3)
        diff, found = self.stream.find_substream(pattern, window_center=0.05, window_size=1)
        self.assertAlmostEqual(-0.2, found, places=4)

    def test_find_substream_result_stays_inside_padded_range(self):
        pattern = self.stream.get_substream(1.0, 1.5)
        for center in (-100.0, -0.5, 0.0, 4.9, 100.0):
            diff, found = self.stream.find_substream(pattern, window_center=center, window_size=10)
            self.assertGreaterEqual(found, -self.stream.PADDING_SECONDS)
            self.assertLessEqual(found, self.stream.duration_seconds + self.stream.PADDING_SECONDS)
