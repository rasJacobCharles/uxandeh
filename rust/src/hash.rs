/// Hash module.
///
/// Implements Merkle-Damgård padding and the compression processing loop.
///
/// All code and comments follow British English spelling conventions.

use crate::compression::{compress_block, DEFAULT_IV};

pub fn pad(data: &[u8]) -> Vec<u8> {
    let original_len_bits = (data.len() as u64) * 8;
    
    let mut padded = Vec::with_capacity(data.len() + 32);
    padded.extend_from_slice(data);
    padded.push(0x80);

    let current_mod = padded.len() % 32;
    let k = if current_mod <= 24 {
        24 - current_mod
    } else {
        32 - (current_mod - 24)
    };

    padded.resize(padded.len() + k, 0x00);
    padded.extend_from_slice(&original_len_bits.to_be_bytes());
    padded
}

pub fn uxandeh(data: &[u8]) -> [u8; 32] {
    let padded = pad(data);
    let mut state = DEFAULT_IV;

    for chunk in padded.chunks_exact(32) {
        let block: &[u8; 32] = chunk.try_into().unwrap();
        state = compress_block(state, block);
    }

    let mut digest = [0u8; 32];
    digest[0..8].copy_from_slice(&state.0.to_be_bytes());
    digest[8..16].copy_from_slice(&state.1.to_be_bytes());
    digest[16..24].copy_from_slice(&state.2.to_be_bytes());
    digest[24..32].copy_from_slice(&state.3.to_be_bytes());
    digest
}
