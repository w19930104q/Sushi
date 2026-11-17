import unittest
from demux import Timecodes


class CfrTimecodesTestCase(unittest.TestCase):
    def test_get_frame_time_zero(self):
        tcs = Timecodes.cfr(23.976)
        t = tcs.get_frame_time(0)
        self.assertEqual(t, 0)

    def test_get_frame_time_sane(self):
        tcs = Timecodes.cfr(23.976)
        t = tcs.get_frame_time(10)
        self.assertAlmostEqual(10.0/23.976, t)

    def test_get_frame_time_insane(self):
        tcs = Timecodes.cfr(23.976)
        t = tcs.get_frame_time(100000)
        self.assertAlmostEqual(100000.0/23.976, t)

    def test_get_frame_size(self):
        tcs = Timecodes.cfr(23.976)
        t1 = tcs.get_frame_size(0)
        t2 = tcs.get_frame_size(1000)
        self.assertAlmostEqual(1.0/23.976, t1)
        self.assertAlmostEqual(t1, t2)

    def test_get_frame_number(self):
        tcs = Timecodes.cfr(24000.0/1001.0)
        self.assertEqual(tcs.get_frame_number(0), 0)
        self.assertEqual(tcs.get_frame_number(1145.353), 27461)
        self.assertEqual(tcs.get_frame_number(1001.0/24000.0 * 1234567), 1234567)


class TimecodesTestCase(unittest.TestCase):
    def test_cfr_timecodes_v2(self):
        text = '# timecode format v2\n' + '\n'.join(str(1000 * x / 23.976) for x in range(0, 30000))
        parsed = Timecodes.parse(text)

        self.assertAlmostEqual(1.0/23.976, parsed.get_frame_size(0))
        self.assertAlmostEqual(1.0/23.976, parsed.get_frame_size(25))
        self.assertAlmostEqual(1.0/23.976*100, parsed.get_frame_time(100))
        self.assertEqual(0, parsed.get_frame_time(0))
        self.assertEqual(0, parsed.get_frame_number(0))
        # unified sampling contract: VFR and CFR both use floor semantics, so this
        # matches Timecodes.cfr(23.976).get_frame_number(1145.353) exactly
        # (1145.353s is 27460.98 frames - the old ceil-like sampling was one frame off)
        self.assertEqual(27460, parsed.get_frame_number(1145.353))
        self.assertEqual(27460, Timecodes.cfr(23.976).get_frame_number(1145.353))

    def test_cfr_timecodes_v1(self):
        text = '# timecode format v1\nAssume 23.976024'
        parsed = Timecodes.parse(text)
        self.assertAlmostEqual(1.0/23.976024, parsed.get_frame_size(0))
        self.assertAlmostEqual(1.0/23.976024, parsed.get_frame_size(25))
        self.assertAlmostEqual(1.0/23.976024*100, parsed.get_frame_time(100))
        self.assertEqual(0, parsed.get_frame_time(0))
        self.assertEqual(0, parsed.get_frame_number(0))
        self.assertEqual(27461, parsed.get_frame_number(1145.353))

    def test_cfr_timecodes_v1_with_overrides(self):
        text = '# timecode format v1\nAssume 23.976000\n0,2000,23.976000\n3000,5000,23.976000'
        parsed = Timecodes.parse(text)
        self.assertAlmostEqual(1.0/23.976, parsed.get_frame_size(0))
        self.assertAlmostEqual(1.0/23.976, parsed.get_frame_size(25))
        self.assertAlmostEqual(1.0/23.976*100, parsed.get_frame_time(100))
        self.assertEqual(0, parsed.get_frame_time(0))

    def test_vfr_timecodes_v1_frame_size_at_first_frame(self):
        text = '# timecode format v1\nAssume 23.976000\n0,2000,29.970000\n3000,4000,59.940000'
        parsed = Timecodes.parse(text)
        self.assertAlmostEqual(1.0/29.97, parsed.get_frame_size(timestamp=0))

    def test_vfr_timecodes_v1_frame_size_outside_of_defined_range(self):
        text = '# timecode format v1\nAssume 23.976000\n0,2000,29.970000\n3000,4000,59.940000'
        parsed = Timecodes.parse(text)
        self.assertAlmostEqual(1.0/23.976, parsed.get_frame_size(timestamp=5000.0))

    def test_vft_timecodes_v1_frame_size_inside_override_block(self):
        text = '# timecode format v1\nAssume 23.976000\n0,2000,29.970000\n3000,4000,59.940000'
        parsed = Timecodes.parse(text)
        self.assertAlmostEqual(1.0/29.97, parsed.get_frame_size(timestamp=49.983))

    def test_vft_timecodes_v1_frame_size_between_override_blocks(self):
        text = '# timecode format v1\nAssume 23.976000\n0,2000,29.970000\n3000,4000,59.940000'
        parsed = Timecodes.parse(text)
        self.assertAlmostEqual(1.0/23.976, parsed.get_frame_size(timestamp=87.496))

    def test_vfr_timecodes_v1_frame_time_at_first_frame(self):
        text = '# timecode format v1\nAssume 23.976000\n0,2000,29.970000\n3000,4000,59.940000'
        parsed = Timecodes.parse(text)
        self.assertAlmostEqual(0, parsed.get_frame_time(number=0))

    def test_vfr_timecodes_v1_frame_time_outside_of_defined_range(self):
        text = '# timecode format v1\nAssume 23.976000\n0,2000,29.970000\n3000,4000,59.940000'
        parsed = Timecodes.parse(text)
        self.assertAlmostEqual(1000.968, parsed.get_frame_time(number=25000), places=3)

    def test_vft_timecodes_v1_frame_time_inside_override_block(self):
        text = '# timecode format v1\nAssume 23.976000\n0,2000,29.970000\n3000,4000,59.940000'
        parsed = Timecodes.parse(text)
        self.assertAlmostEqual(50.05, parsed.get_frame_time(number=1500), places=3)

    def test_vft_timecodes_v1_frame_time_between_override_blocks(self):
        text = '# timecode format v1\nAssume 23.976000\n0,2000,29.970000\n3000,4000,59.940000'
        parsed = Timecodes.parse(text)
        self.assertAlmostEqual(87.579, parsed.get_frame_time(number=2500), places=3)




class TimecodesBoundaryContractTestCase(unittest.TestCase):
    """Contracts for negative offsets and the last-frame boundary."""

    V2_TEXT = '# timecode format v2\n0.0\n41.708\n83.416\n125.124'

    def test_v2_frame_size_at_last_frame_is_not_zero(self):
        # the last defined frame has no successor; it must reuse the previous
        # interval instead of reporting a zero frame size
        parsed = Timecodes.parse(self.V2_TEXT)
        self.assertAlmostEqual(0.041708, parsed.get_frame_size(0.125124))
        self.assertAlmostEqual(0.041708, parsed.get_frame_size(0.125))

    def test_v2_frame_size_before_first_frame(self):
        parsed = Timecodes.parse(self.V2_TEXT)
        self.assertAlmostEqual(0.041708, parsed.get_frame_size(-0.5))

    def test_v2_frame_time_never_wraps_around(self):
        # negative frame numbers used to wrap around to the END of the list
        parsed = Timecodes.parse(self.V2_TEXT)
        self.assertAlmostEqual(0.0, parsed.get_frame_time(-1))
        self.assertAlmostEqual(0.0, parsed.get_frame_time(-100))

    def test_v2_frame_time_past_the_end_clamps(self):
        parsed = Timecodes.parse(self.V2_TEXT)
        self.assertAlmostEqual(0.125124, parsed.get_frame_time(100))

    def test_v1_frame_time_negative_extrapolates_backwards(self):
        parsed = Timecodes.parse('# timecode format v1\nAssume 25')
        self.assertAlmostEqual(-2.0 / 25, parsed.get_frame_time(-2))

    def test_v1_frame_number_past_the_last_frame_extrapolates(self):
        # used to subtract sum(self.times), landing on a garbage frame
        parsed = Timecodes.parse('# timecode format v1\nAssume 25\n0,9,25')
        self.assertEqual(11, len(parsed.times))
        self.assertEqual(10, parsed.get_frame_number(0.4))
        self.assertEqual(11, parsed.get_frame_number(0.44))
        self.assertEqual(15, parsed.get_frame_number(0.6))

    def test_v2_frame_number_past_the_last_frame_clamps(self):
        parsed = Timecodes.parse(self.V2_TEXT)
        self.assertEqual(3, parsed.get_frame_number(100.0))

    def test_frame_number_before_first_frame_is_negative(self):
        parsed = Timecodes.parse('# timecode format v1\nAssume 25\n0,9,25')
        self.assertEqual(-1, parsed.get_frame_number(-0.02))
        self.assertEqual(-2, parsed.get_frame_number(-0.05))

    def test_cfr_frame_number_uses_floor_for_negative_times(self):
        # int() truncates towards zero; the unified contract is floor semantics
        tcs = Timecodes.cfr(25)
        self.assertEqual(-1, tcs.get_frame_number(-0.02))
        self.assertEqual(-2, tcs.get_frame_number(-0.05))

    def test_vfr_and_cfr_frame_numbers_agree(self):
        # the unified sampling contract: identical CFR content must produce
        # identical frame numbers through the VFR and CFR code paths
        fps = 24000.0 / 1001.0
        text = '# timecode format v2\n' + '\n'.join(str(1000 * x / fps) for x in range(0, 3000))
        vfr = Timecodes.parse(text)
        cfr = Timecodes.cfr(fps)
        for t in (0.0, 0.04, 1.5, 17.89, 100.001, 120.0):
            self.assertEqual(cfr.get_frame_number(t), vfr.get_frame_number(t))
