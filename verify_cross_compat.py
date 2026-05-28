#!/usr/bin/env python3
"""Cross-Language Verification Script.

Generates multiple random inputs of various lengths, hashes them with both the
Python and Rust implementations of uxandeh, and verifies they produce bit-for-bit
identical outputs.

All code and comments follow British English spelling conventions.
"""

import sys
import os
import subprocess
import random

# Add python directory to sys.path to load local uxandeh package
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "python"))
from uxandeh import uxandeh


def run_rust_hash(data: bytes) -> str:
    """Invoke the Rust binary via cargo run to compute the hash."""
    cargo_toml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rust", "Cargo.toml")
    cmd = ["cargo", "run", "--manifest-path", cargo_toml_path, "--quiet"]
    
    # Run the cargo command and pass the input bytes via stdin
    res = subprocess.run(cmd, input=data, capture_output=True, check=True)
    return res.stdout.decode("utf-8").strip()


def verify():
    print("====================================================")
    print("Starting uxandeh Cross-Language Verification...")
    print("====================================================")

    # Various test cases including edge case lengths
    test_lengths = [0, 1, 4, 15, 23, 24, 25, 31, 32, 33, 64, 127, 256, 1000]
    
    # Ensure reproducibility of random values
    rng = random.Random(42)

    for idx, length in enumerate(test_lengths):
        # Generate random message bytes of the target length
        msg = bytes([rng.randint(0, 255) for _ in range(length)])
        
        # Calculate hash in Python
        hash_py = uxandeh(msg).hex()
        
        # Calculate hash in Rust
        try:
            hash_rust = run_rust_hash(msg)
        except Exception as e:
            print(f"Error executing Rust binary: {e}")
            sys.exit(1)
            
        print(f"Test case {idx + 1:2d} (length = {length:4d} bytes):")
        print(f"  Python: {hash_py}")
        print(f"  Rust:   {hash_rust}")
        
        if hash_py != hash_rust:
            print(f"  [FAIL] Hash mismatch detected for input length {length}!")
            sys.exit(1)
        else:
            print("  [PASS] Hashes are identical.")
            
    print("====================================================")
    print("Success: All cross-compatibility verification tests passed!")
    print("====================================================")
    sys.exit(0)


if __name__ == "__main__":
    verify()
