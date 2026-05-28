/// IFS Compression module.
///
/// Implements the hybrid Iterated Function System (IFS) round function using
/// discrete arithmetic over the finite field F_p.
///
/// All code and comments follow British English spelling conventions.

use crate::sona::generate_sona_sbox;

pub const PRIME_P: u64 = 18446744073709551427;

pub const DEFAULT_IV: (u64, u64, u64, u64) = (
    0x6a09e667f3bcc908 % PRIME_P,
    0xbb67ae8584caa73b % PRIME_P,
    0x3c6ef372fe94f82b % PRIME_P,
    0xa54ff53a5f1d36f1 % PRIME_P,
);

#[inline]
pub fn mul_mod(a: u64, b: u64) -> u64 {
    ((a as u128 * b as u128) % PRIME_P as u128) as u64
}

#[inline]
pub fn add_mod(a: u64, b: u64) -> u64 {
    ((a as u128 + b as u128) % PRIME_P as u128) as u64
}

#[inline]
pub fn sub_mod(a: u64, b: u64) -> u64 {
    if a >= b {
        a - b
    } else {
        PRIME_P - (b - a)
    }
}

pub fn pow_mod(mut base: u64, mut exp: u64) -> u64 {
    let mut res = 1;
    base %= PRIME_P;
    while exp > 0 {
        if exp % 2 == 1 {
            res = mul_mod(res, base);
        }
        base = mul_mod(base, base);
        exp /= 2;
    }
    res
}

#[inline]
pub fn modular_inverse(a: u64) -> u64 {
    pow_mod(a, PRIME_P - 2)
}

#[inline]
fn rotl64(x: u64, n: u32) -> u64 {
    (x << n) | (x >> (64 - n))
}

pub fn compress_block(state: (u64, u64, u64, u64), block: &[u8; 32]) -> (u64, u64, u64, u64) {
    // 1. State-dependent Sona Permutation
    let state_seed = (state.0 ^ state.1 ^ state.2 ^ state.3) & 0xFFFFFFFF;
    let sbox = generate_sona_sbox(state_seed, false);
    let pbox = generate_sona_sbox(state_seed, true);

    // Scramble the message block
    let mut scrambled_bytes = [0u8; 32];
    for i in 0..32 {
        scrambled_bytes[i] = sbox[block[i] as usize];
    }

    // Filter P-Box to obtain bijective permutation of 0..31
    let mut pbox_32 = Vec::with_capacity(32);
    for &v in pbox.iter() {
        if v < 32 {
            pbox_32.push(v as usize);
        }
    }

    let mut permuted_bytes = [0u8; 32];
    for i in 0..32 {
        permuted_bytes[i] = scrambled_bytes[pbox_32[i]];
    }

    // Convert to four 64-bit field elements
    let m = [
        u64::from_be_bytes(permuted_bytes[0..8].try_into().unwrap()) % PRIME_P,
        u64::from_be_bytes(permuted_bytes[8..16].try_into().unwrap()) % PRIME_P,
        u64::from_be_bytes(permuted_bytes[16..24].try_into().unwrap()) % PRIME_P,
        u64::from_be_bytes(permuted_bytes[24..32].try_into().unwrap()) % PRIME_P,
    ];

    // 2. Iterated Function System (IFS) loop
    let mut x = state.0;
    let mut y = state.1;
    let mut w = state.2;
    let mut h = state.3;

    for round_num in 0..12u64 {
        let mut s_round = (m[0] ^ round_num) % PRIME_P;
        if s_round == 0 {
            s_round = 3;
        }

        let v_round = (m[1] ^ round_num ^ x) % PRIME_P;
        let dx_round = (m[2] ^ round_num) % PRIME_P;
        let dy_round = (m[3] ^ round_num) % PRIME_P;

        // Logone-Birni Courtyard Dimension Scaling
        w = add_mod(mul_mod(s_round, w), dx_round);
        h = add_mod(mul_mod(s_round, h), dy_round);

        if w == 0 {
            w = 1;
        }
        if h == 0 {
            h = 1;
        }

        // Ba-ila Settlement Circular Mapping
        let denominator = add_mod(1, mul_mod(v_round, v_round));
        let inv_den = modular_inverse(denominator);

        let dx_circle = mul_mod(mul_mod(w, sub_mod(1, mul_mod(v_round, v_round))), inv_den);
        let dy_circle = mul_mod(mul_mod(w, mul_mod(2, v_round)), inv_den);

        // Rotation quadrant checks
        let rot_quadrant = round_num % 4;
        let (dx_rot, dy_rot) = match rot_quadrant {
            0 => (dx_circle, dy_circle),
            1 => ((PRIME_P - dy_circle) % PRIME_P, dx_circle),
            2 => ((PRIME_P - dx_circle) % PRIME_P, (PRIME_P - dy_circle) % PRIME_P),
            _ => (dy_circle, (PRIME_P - dx_circle) % PRIME_P),
        };

        // Translate centre coordinate
        x = add_mod(x, dx_rot);
        y = add_mod(y, dy_rot);

        // High-diffusion mixing
        let x_mix = x ^ y ^ w ^ h;
        let y_mix = y ^ rotl64(x_mix, 17);
        let w_mix = w ^ rotl64(y_mix, 31);
        let h_mix = h ^ rotl64(w_mix, 47);

        // Non-linear XOR mixing
        x = (x_mix ^ m[1]) % PRIME_P;
        y = (y_mix ^ m[2]) % PRIME_P;
        w = (w_mix ^ m[3]) % PRIME_P;
        h = (h_mix ^ m[0]) % PRIME_P;
    }

    // 3. Davies-Meyer Feed-Forward
    let x_out = (x ^ state.0) % PRIME_P;
    let y_out = (y ^ state.1) % PRIME_P;
    let w_out = (w ^ state.2) % PRIME_P;
    let h_out = (h ^ state.3) % PRIME_P;

    (x_out, y_out, w_out, h_out)
}
