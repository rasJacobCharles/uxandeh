"""Hash Module.

This module implements the main hashing structure of the African Fractal Hash
(uxandeh) using Merkle-Damgård padding for 32-byte block sizes.

All code and comments in this module follow British English spelling conventions.
"""

from typing import Tuple
from .compression import DEFAULT_IV, PRIME_P, compress_block

def pad(data: bytes) -> bytes:
    """Pad the input data using Merkle-Damgård padding tailored for 32-byte blocks.

    Appends a 0x80 byte, then a variable number of 0x00 bytes, and finally
    the length of the original message in bits as a 64-bit big-endian integer.
    The total length of the padded message will be a multiple of 32 bytes.
    """
    original_len_bits = len(data) * 8
    
    # Append the 0x80 byte
    padded = bytearray(data)
    padded.append(0x80)
    
    # Calculate padding bytes needed
    # (len(data) + 1 + K) % 32 == 24
    current_mod = len(padded) % 32
    if current_mod <= 24:
        k = 24 - current_mod
    else:
        k = 32 - (current_mod - 24)
        
    padded.extend(b'\x00' * k)
    
    # Append the length in bits as an 8-byte big-endian integer
    padded.extend(original_len_bits.to_bytes(8, "big"))
    
    return bytes(padded)


def uxandeh(data: bytes) -> bytes:
    """Compute the 256-bit African Fractal Hash (uxandeh) digest of the input bytes.

    Args:
        data: The input message as bytes.

    Returns:
        A 32-byte (256-bit) hash digest.
    """
    # 1. Pad the message
    padded_msg = pad(data)
    
    # 2. Initialise the hash state
    state = DEFAULT_IV
    
    # 3. Process each 32-byte block
    for offset in range(0, len(padded_msg), 32):
        block = padded_msg[offset : offset + 32]
        state = compress_block(state, block)
        
    # 4. Finalise digest: convert state (four 64-bit integers) to 32 bytes
    digest = bytearray()
    for val in state:
        # Each value is modulo PRIME_P, so it fits in a 64-bit integer
        digest.extend(val.to_bytes(8, "big"))
        
    return bytes(digest)
