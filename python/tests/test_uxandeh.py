"""Tests for the uxandeh library.

Verifies the mathematical properties, bijectivity, non-linearity, differential
uniformity, and avalanche effect of the Sona Permutation and IFS Compression functions.
Also tests the top-level hashing and padding.

All code and comments follow British English spelling conventions.
"""

import unittest
import random
from typing import Tuple

from uxandeh.sona import (
    generate_sona_sbox,
    generate_sona_pbox,
    SplitMix64,
)
from uxandeh.compression import (
    PRIME_P,
    DEFAULT_IV,
    modular_inverse,
    compress_block,
)
from uxandeh.hash import pad, uxandeh


class TestSplitMix64(unittest.TestCase):
    def test_prng_determinism(self):
        """Verify that SplitMix64 is deterministic and identical for a given seed."""
        rng1 = SplitMix64(42)
        rng2 = SplitMix64(42)
        
        self.assertEqual(rng1.next_u64(), rng2.next_u64())
        self.assertEqual(rng1.rand_range(0, 100), rng2.rand_range(0, 100))
        
        lst1 = list(range(50))
        lst2 = list(range(50))
        rng1.shuffle(lst1)
        rng2.shuffle(lst2)
        self.assertEqual(lst1, lst2)


class TestSonaPermutation(unittest.TestCase):
    def compute_nonlinearity(self, sbox) -> int:
        """Compute the non-linearity of an 8x8 S-Box."""
        min_nl = 256
        for a in range(1, 256):
            max_walsh = 0
            for b in range(256):
                walsh = 0
                for x in range(256):
                    ax = bin(a & x).count('1') % 2
                    bs = bin(b & sbox[x]).count('1') % 2
                    if ax ^ bs:
                        walsh -= 1
                    else:
                        walsh += 1
                max_walsh = max(max_walsh, abs(walsh))
            nl = 128 - max_walsh // 2
            min_nl = min(min_nl, nl)
        return min_nl

    def compute_differential_uniformity(self, sbox) -> int:
        """Compute the differential uniformity of an 8x8 S-Box."""
        max_diff = 0
        for delta_x in range(1, 256):
            diffs = [0] * 256
            for x in range(256):
                delta_y = sbox[x] ^ sbox[x ^ delta_x]
                diffs[delta_y] += 1
            max_diff = max(max_diff, max(diffs))
        return max_diff

    def test_sona_cryptographic_properties(self):
        """Verify bijectivity, non-linearity, and differential uniformity for Sona S-Boxes."""
        seeds = [42, 12345, 999999]
        for seed in seeds:
            sbox = generate_sona_sbox(seed)
            pbox = generate_sona_pbox(seed)

            # Check bijectivity
            self.assertEqual(len(sbox), 256)
            self.assertEqual(len(set(sbox)), 256)
            self.assertEqual(len(pbox), 256)
            self.assertEqual(len(set(pbox)), 256)
            self.assertNotEqual(sbox, pbox)

            # Cryptographic metrics
            nl = self.compute_nonlinearity(sbox)
            du = self.compute_differential_uniformity(sbox)
            fixed_points = sum(1 for idx, val in enumerate(sbox) if val == idx)

            self.assertGreaterEqual(nl, 90, f"Non-linearity low for seed {seed}: {nl}")
            self.assertLessEqual(du, 14, f"Differential uniformity high for seed {seed}: {du}")
            self.assertLessEqual(fixed_points, 4, f"Too many fixed points for seed {seed}: {fixed_points}")


class TestIFSCompression(unittest.TestCase):
    def test_finite_field_arithmetic(self):
        """Verify modular inverse correctness and that 1 + v^2 has no roots modulo p."""
        for _ in range(100):
            val = random.randint(1, PRIME_P - 1)
            inv = modular_inverse(val)
            self.assertEqual((val * inv) % PRIME_P, 1)

        # 1 + v^2 != 0 since p = 3 (mod 4)
        for _ in range(100):
            v = random.randint(0, PRIME_P - 1)
            den = (1 + v * v) % PRIME_P
            self.assertNotEqual(den, 0)

    def test_determinism(self):
        """Verify compression function is deterministic."""
        state = DEFAULT_IV
        block = bytes([random.randint(0, 255) for _ in range(32)])
        out1 = compress_block(state, block)
        out2 = compress_block(state, block)
        self.assertEqual(out1, out2)

        for val in out1:
            self.assertTrue(0 <= val < PRIME_P)

    def state_to_bits(self, state: Tuple[int, int, int, int]) -> list:
        bits = []
        for val in state:
            bin_str = format(val, "064b")
            bits.extend([int(b) for b in bin_str])
        return bits

    def flip_bit(self, block: bytes, bit_idx: int) -> bytes:
        byte_idx = bit_idx // 8
        bit_in_byte = bit_idx % 8
        block_arr = bytearray(block)
        block_arr[byte_idx] ^= 1 << (7 - bit_in_byte)
        return bytes(block_arr)

    def test_avalanche_effect(self):
        """Verify the avalanche effect of the compression function."""
        num_samples = 50
        msg_flip_ratios = []
        state_flip_ratios = []

        for _ in range(num_samples):
            state = (
                random.randint(0, PRIME_P - 1),
                random.randint(0, PRIME_P - 1),
                random.randint(0, PRIME_P - 1),
                random.randint(0, PRIME_P - 1),
            )
            block = bytes([random.randint(0, 255) for _ in range(32)])
            base_out = compress_block(state, block)
            base_bits = self.state_to_bits(base_out)

            # Flip msg bit
            msg_bit = random.randint(0, 255)
            flipped_block = self.flip_bit(block, msg_bit)
            msg_flipped_out = compress_block(state, flipped_block)
            msg_flipped_bits = self.state_to_bits(msg_flipped_out)
            flipped_count_msg = sum(b1 ^ b2 for b1, b2 in zip(base_bits, msg_flipped_bits))
            msg_flip_ratios.append(flipped_count_msg / 256.0)

            # Flip state bit
            state_bit = random.randint(0, 255)
            state_element = state_bit // 64
            bit_in_element = state_bit % 64
            flipped_state_arr = list(state)
            flipped_state_arr[state_element] ^= 1 << bit_in_element
            flipped_state_arr[state_element] %= PRIME_P
            flipped_state = tuple(flipped_state_arr)

            state_flipped_out = compress_block(flipped_state, block)
            state_flipped_bits = self.state_to_bits(state_flipped_out)
            flipped_count_state = sum(b1 ^ b2 for b1, b2 in zip(base_bits, state_flipped_bits))
            state_flip_ratios.append(flipped_count_state / 256.0)

        avg_msg_flip = sum(msg_flip_ratios) / len(msg_flip_ratios)
        avg_state_flip = sum(state_flip_ratios) / len(state_flip_ratios)

        # Average must be close to 50%
        self.assertTrue(0.44 <= avg_msg_flip <= 0.56, f"Msg avalanche: {avg_msg_flip}")
        self.assertTrue(0.44 <= avg_state_flip <= 0.56, f"State avalanche: {avg_state_flip}")


class TestUxandehHash(unittest.TestCase):
    def test_padding(self):
        """Verify that padding generates block sizes which are multiples of 32."""
        for msg_len in [0, 1, 15, 23, 24, 25, 31, 32, 100, 256]:
            msg = bytes([random.randint(0, 255) for _ in range(msg_len)])
            padded = pad(msg)
            self.assertEqual(len(padded) % 32, 0)
            self.assertTrue(len(padded) > len(msg))
            self.assertEqual(padded[-8:], (msg_len * 8).to_bytes(8, "big"))

    def test_hash_output(self):
        """Verify that different messages yield different hashes of 32 bytes."""
        msg1 = b"hello world"
        msg2 = b"hello worle"
        
        h1 = uxandeh(msg1)
        h2 = uxandeh(msg2)
        
        self.assertEqual(len(h1), 32)
        self.assertEqual(len(h2), 32)
        self.assertNotEqual(h1, h2)


if __name__ == "__main__":
    unittest.main()
