"""IFS Compression Module.

This module implements a cryptographically secure compression function for the
African Fractal Hash (AFH). It utilises discrete Iterated Function Systems (IFS)
derived from Logone-Birni palace loops and Ba-ila settlement geometries,
operating over a finite field to prevent floating-point errors. It integrates
state-dependent Sona permutations and a Davies-Meyer feed-forward structure.

All code and comments in this module follow British English spelling conventions.
"""

from typing import Tuple
from .sona import generate_sona_sbox, generate_sona_pbox

# Finite field prime: p = 2^64 - 189.
# This prime satisfies p = 3 (mod 4), ensuring that 1 + v^2 = 0 (mod p) has no
# solutions, which guarantees the existence of the modular inverse.
PRIME_P = 18446744073709551427

# Initialisation Vector (IV) derived from fractional parts of square roots of primes
# mapped into the finite field.
DEFAULT_IV = (
    0x6a09e667f3bcc908 % PRIME_P,
    0xbb67ae8584caa73b % PRIME_P,
    0x3c6ef372fe94f82b % PRIME_P,
    0xa54ff53a5f1d36f1 % PRIME_P,
)


def modular_inverse(a: int) -> int:
    """Compute the modular multiplicative inverse of a modulo PRIME_P.

    Uses Fermat's Little Theorem since PRIME_P is prime.
    """
    return pow(a, PRIME_P - 2, PRIME_P)


def rotl64(x: int, n: int) -> int:
    """Rotate a 64-bit integer left by n bits."""
    x &= 0xFFFFFFFFFFFFFFFF
    return ((x << n) | (x >> (64 - n))) & 0xFFFFFFFFFFFFFFFF


def compress_block(state: Tuple[int, int, int, int], block: bytes) -> Tuple[int, int, int, int]:
    """Compress a 256-bit (32-byte) message block into a new 256-bit state.

    Args:
        state: A tuple of four 64-bit integers (x, y, w, h) representing the
          current state in the finite field.
        block: A 32-byte message block.

    Returns:
        A new state tuple (x, y, w, h) in the finite field.
    """
    if len(block) != 32:
        raise ValueError("Block size must be exactly 32 bytes (256 bits).")

    # 1. State-dependent Sona Permutation
    # Derive a key-dependent seed from the current state to dynamically
    # generate the Sona S-Box and P-Box.
    state_seed = (state[0] ^ state[1] ^ state[2] ^ state[3]) & 0xFFFFFFFF
    sbox = generate_sona_sbox(state_seed)
    pbox = generate_sona_pbox(state_seed)

    # Scramble the input message block using the S-Box and P-Box
    scrambled_bytes = bytearray(32)
    for i in range(32):
        s_val = sbox[block[i]]
        scrambled_bytes[i] = s_val

    # Filter P-Box to obtain a valid bijective permutation of 0..31
    pbox_32 = [v for v in pbox if v < 32]
    # Apply byte permutation using the filtered P-Box indices
    permuted_bytes = bytearray(32)
    for i in range(32):
        permuted_bytes[i] = scrambled_bytes[pbox_32[i]]

    # Convert the permuted bytes into four 64-bit integers in the finite field
    m = [
        int.from_bytes(permuted_bytes[0:8], "big") % PRIME_P,
        int.from_bytes(permuted_bytes[8:16], "big") % PRIME_P,
        int.from_bytes(permuted_bytes[16:24], "big") % PRIME_P,
        int.from_bytes(permuted_bytes[24:32], "big") % PRIME_P,
    ]

    # 2. Iterated Function System (IFS) loop
    x, y, w, h = state

    # Execute 12 rounds of the hybrid architectural IFS transformations
    for round_num in range(12):
        # Derive round-specific variables using non-linear mix of block integers
        # and round number.
        s_round = (m[0] ^ round_num) % PRIME_P
        if s_round == 0:
            s_round = 3  # Ensure non-trivial contractive scaling factor

        v_round = (m[1] ^ round_num ^ x) % PRIME_P
        dx_round = (m[2] ^ round_num) % PRIME_P
        dy_round = (m[3] ^ round_num) % PRIME_P

        # Logone-Birni Courtyard Dimension Scaling (accretion-based linear contraction)
        w = (s_round * w + dx_round) % PRIME_P
        h = (s_round * h + dy_round) % PRIME_P

        # Avoid zero dimensions to maintain fractal boundaries
        if w == 0:
            w = 1
        if h == 0:
            h = 1

        # Ba-ila Settlement Circular Mapping (rational parametrisation of nested rings)
        # Using w (width dimension) as the radius for the nested ring displacement.
        denominator = (1 + v_round * v_round) % PRIME_P
        inv_den = modular_inverse(denominator)

        # Rational circle coordinates
        dx_circle = (w * (1 - v_round * v_round) * inv_den) % PRIME_P
        dy_circle = (w * 2 * v_round * inv_den) % PRIME_P

        # Logone-Birni accretion rotation (apply 90-degree rotations in the field)
        rot_quadrant = round_num % 4
        if rot_quadrant == 0:
            dx_rot, dy_rot = dx_circle, dy_circle
        elif rot_quadrant == 1:
            dx_rot, dy_rot = (PRIME_P - dy_circle) % PRIME_P, dx_circle
        elif rot_quadrant == 2:
            dx_rot, dy_rot = (PRIME_P - dx_circle) % PRIME_P, (PRIME_P - dy_circle) % PRIME_P
        else:
            dx_rot, dy_rot = dy_circle, (PRIME_P - dx_circle) % PRIME_P

        # Translate the centre coordinate
        x = (x + dx_rot) % PRIME_P
        y = (y + dy_rot) % PRIME_P

        # High-diffusion mixing step using bitwise rotations and XORs
        # to ensure that LSB changes propagate to MSB changes rapidly.
        x_mix = x ^ y ^ w ^ h
        y_mix = y ^ rotl64(x_mix, 17)
        w_mix = w ^ rotl64(y_mix, 31)
        h_mix = h ^ rotl64(w_mix, 47)

        # Non-linear XOR-mixing step to thwart algebraic attacks
        x = (x_mix ^ m[1]) % PRIME_P
        y = (y_mix ^ m[2]) % PRIME_P
        w = (w_mix ^ m[3]) % PRIME_P
        h = (h_mix ^ m[0]) % PRIME_P

    # 3. Davies-Meyer Feed-Forward
    # Mix the final state with the initial state using XOR to ensure one-wayness.
    x_out = (x ^ state[0]) % PRIME_P
    y_out = (y ^ state[1]) % PRIME_P
    w_out = (w ^ state[2]) % PRIME_P
    h_out = (h ^ state[3]) % PRIME_P

    return x_out, y_out, w_out, h_out
