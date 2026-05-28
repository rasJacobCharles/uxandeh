/// Integration tests for the Rust implementation of uxandeh.
///
/// Verifies the correctness, bijectivity, non-linearity, differential uniformity,
/// and avalanche effect.
///
/// All code and comments follow British English spelling conventions.

use uxandeh::sona::{generate_sona_sbox, SplitMix64};
use uxandeh::compression::{PRIME_P, DEFAULT_IV, modular_inverse, compress_block};
use uxandeh::hash::{pad, uxandeh};

#[test]
fn test_prng_determinism() {
    let mut rng1 = SplitMix64::new(42);
    let mut rng2 = SplitMix64::new(42);

    assert_eq!(rng1.next_u64(), rng2.next_u64());
    assert_eq!(rng1.rand_range(0, 100), rng2.rand_range(0, 100));

    let mut lst1: Vec<usize> = (0..50).collect();
    let mut lst2: Vec<usize> = (0..50).collect();
    rng1.shuffle(&mut lst1);
    rng2.shuffle(&mut lst2);
    assert_eq!(lst1, lst2);
}

fn compute_nonlinearity(sbox: &[u8; 256]) -> usize {
    let mut min_nl = 256;
    for a in 1..256u32 {
        let mut max_walsh = 0;
        for b in 0..256u32 {
            let mut walsh = 0i32;
            for x in 0..256u32 {
                let ax = (a & x).count_ones() % 2;
                let bs = (b & sbox[x as usize] as u32).count_ones() % 2;
                if ax ^ bs == 1 {
                    walsh -= 1;
                } else {
                    walsh += 1;
                }
            }
            max_walsh = max_walsh.max(walsh.abs());
        }
        let nl = 128 - max_walsh / 2;
        min_nl = min_nl.min(nl);
    }
    min_nl as usize
}

fn compute_differential_uniformity(sbox: &[u8; 256]) -> usize {
    let mut max_diff = 0;
    for delta_x in 1..256 {
        let mut diffs = [0usize; 256];
        for x in 0..256 {
            let delta_y = (sbox[x] ^ sbox[x ^ delta_x]) as usize;
            diffs[delta_y] += 1;
        }
        let local_max = *diffs.iter().max().unwrap();
        max_diff = max_diff.max(local_max);
    }
    max_diff
}

#[test]
fn test_sona_cryptographic_properties() {
    let seeds = [42, 12345, 999999];
    for seed in seeds {
        let sbox = generate_sona_sbox(seed, false);
        let pbox = generate_sona_sbox(seed, true);

        // Assert size and bijectivity
        let sbox_set: std::collections::HashSet<u8> = sbox.iter().cloned().collect();
        assert_eq!(sbox_set.len(), 256);
        let pbox_set: std::collections::HashSet<u8> = pbox.iter().cloned().collect();
        assert_eq!(pbox_set.len(), 256);
        assert_ne!(sbox, pbox);

        let nl = compute_nonlinearity(&sbox);
        let du = compute_differential_uniformity(&sbox);
        let fixed_points = sbox.iter().enumerate().filter(|&(idx, &val)| val == idx as u8).count();

        assert!(nl >= 90, "Non-linearity too low: {}", nl);
        assert!(du <= 14, "Differential uniformity too high: {}", du);
        assert!(fixed_points <= 4, "Too many fixed points: {}", fixed_points);
    }
}

#[test]
fn test_finite_field_arithmetic() {
    // Basic modular inversion test
    let mut rng = SplitMix64::new(12345);
    for _ in 0..100 {
        let val = rng.next_u64() % (PRIME_P - 1) + 1;
        let inv = modular_inverse(val);
        let product = ((val as u128 * inv as u128) % PRIME_P as u128) as u64;
        assert_eq!(product, 1);
    }

    // Verify 1 + v^2 is never 0 modulo p
    for _ in 0..100 {
        let v = rng.next_u64() % PRIME_P;
        let den = ((1 + v as u128 * v as u128) % PRIME_P as u128) as u64;
        assert_ne!(den, 0);
    }
}

#[test]
fn test_determinism() {
    let mut rng = SplitMix64::new(54321);
    let state = DEFAULT_IV;
    let mut block = [0u8; 32];
    for b in block.iter_mut() {
        *b = (rng.next_u64() % 256) as u8;
    }

    let out1 = compress_block(state, &block);
    let out2 = compress_block(state, &block);
    assert_eq!(out1, out2);

    assert!(out1.0 < PRIME_P);
    assert!(out1.1 < PRIME_P);
    assert!(out1.2 < PRIME_P);
    assert!(out1.3 < PRIME_P);
}

fn state_to_bits(state: (u64, u64, u64, u64)) -> Vec<u8> {
    let mut bits = Vec::with_capacity(256);
    for &val in &[state.0, state.1, state.2, state.3] {
        for i in (0..64).rev() {
            bits.push(((val >> i) & 1) as u8);
        }
    }
    bits
}

fn flip_bit(block: &[u8; 32], bit_idx: usize) -> [u8; 32] {
    let byte_idx = bit_idx / 8;
    let bit_in_byte = bit_idx % 8;
    let mut flipped = *block;
    flipped[byte_idx] ^= 1 << (7 - bit_in_byte);
    flipped
}

#[test]
fn test_avalanche_effect() {
    let mut rng = SplitMix64::new(67890);
    let num_samples = 50;
    let mut msg_flip_ratios = Vec::new();
    let mut state_flip_ratios = Vec::new();

    for _ in 0..num_samples {
        let state = (
            rng.next_u64() % PRIME_P,
            rng.next_u64() % PRIME_P,
            rng.next_u64() % PRIME_P,
            rng.next_u64() % PRIME_P,
        );
        let mut block = [0u8; 32];
        for b in block.iter_mut() {
            *b = (rng.next_u64() % 256) as u8;
        }

        let base_out = compress_block(state, &block);
        let base_bits = state_to_bits(base_out);

        // Flip message bit
        let msg_bit = rng.rand_range(0, 256);
        let flipped_block = flip_bit(&block, msg_bit);
        let msg_flipped_out = compress_block(state, &flipped_block);
        let msg_flipped_bits = state_to_bits(msg_flipped_out);
        let flipped_count_msg: usize = base_bits.iter().zip(msg_flipped_bits.iter()).map(|(b1, b2)| (b1 ^ b2) as usize).sum();
        msg_flip_ratios.push(flipped_count_msg as f64 / 256.0);

        // Flip state bit
        let state_bit = rng.rand_range(0, 256);
        let state_element = state_bit / 64;
        let bit_in_element = state_bit % 64;
        let mut flipped_state_arr = [state.0, state.1, state.2, state.3];
        flipped_state_arr[state_element] ^= 1 << bit_in_element;
        flipped_state_arr[state_element] %= PRIME_P;
        let flipped_state = (flipped_state_arr[0], flipped_state_arr[1], flipped_state_arr[2], flipped_state_arr[3]);

        let state_flipped_out = compress_block(flipped_state, &block);
        let state_flipped_bits = state_to_bits(state_flipped_out);
        let flipped_count_state: usize = base_bits.iter().zip(state_flipped_bits.iter()).map(|(b1, b2)| (b1 ^ b2) as usize).sum();
        state_flip_ratios.push(flipped_count_state as f64 / 256.0);
    }

    let avg_msg_flip: f64 = msg_flip_ratios.iter().sum::<f64>() / num_samples as f64;
    let avg_state_flip: f64 = state_flip_ratios.iter().sum::<f64>() / num_samples as f64;

    assert!((0.44..=0.56).contains(&avg_msg_flip), "Msg avalanche failed: {}", avg_msg_flip);
    assert!((0.44..=0.56).contains(&avg_state_flip), "State avalanche failed: {}", avg_state_flip);
}

#[test]
fn test_padding() {
    let mut rng = SplitMix64::new(999);
    for msg_len in &[0, 1, 15, 23, 24, 25, 31, 32, 100, 256] {
        let mut msg = vec![0u8; *msg_len];
        for b in msg.iter_mut() {
            *b = (rng.next_u64() % 256) as u8;
        }
        let padded = pad(&msg);
        assert_eq!(padded.len() % 32, 0);
        assert!(padded.len() > msg.len());
        
        let original_len_bits = (*msg_len as u64) * 8;
        let padded_len_bytes = &padded[padded.len() - 8..];
        assert_eq!(u64::from_be_bytes(padded_len_bytes.try_into().unwrap()), original_len_bits);
    }
}

#[test]
fn test_hash_output() {
    let h1 = uxandeh(b"hello world");
    let h2 = uxandeh(b"hello worle");
    
    assert_eq!(h1.len(), 32);
    assert_eq!(h2.len(), 32);
    assert_ne!(h1, h2);
}
