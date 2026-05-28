# uxandeh

`uxandeh` is a deterministic, fractal-based cryptographic hashing algorithm built on recursive geometric expansion.

> **Uxande** *(Zulu/Xhosa: Pattern, Expansion)* + **H** *(Hash)*

An innovative, non-linear cryptographic hashing algorithm that utilises the deterministic chaos of fractal geometry (specifically Logone-Birni palace spiral layouts and Ba-ila settlement circular geometries) alongside Chokwe Sona drawing Eulerian path rules to generate secure, high-entropy 256-bit digests.

This repository contains completely compatible **Python** and **Rust** implementations of the algorithm.

---

## Key Features

1. **Discrete Iterated Function Systems (IFS)**:
   * **Logone-Birni Palace Loops**: Dimension scaling based on recursive courtyard expansion.
   * **Ba-ila Settlement Patterns**: Nested ring geometries mapped via rational circle parametrisation over the finite field $\mathbb{F}_p$ ($p = 2^{64} - 189$) to avoid floating-point errors.
2. **Sona Permutations (S-Box / P-Box)**:
   * Translates Chokwe Sona drawing Eulerian path rules on a $16 \times 16$ grid into highly non-linear Substitution-Boxes (Non-linearity $\ge 90$, Differential Uniformity $\le 14$) to achieve robust confusion and diffusion.
3. **One-Wayness (Pre-image Resistance)**:
   * Integrates a Davies-Meyer feed-forward structure to XOR the initial state with the final IFS output state, preventing mathematical "reverse-zooming" or algebraic cryptanalysis.
4. **Cross-Language Consistency**:
   * Utilises a custom, deterministic **SplitMix64** generator for all shuffles, guaranteeing bit-for-bit identical digests between the Python and Rust implementations.

---

## Directory Structure

```text
uxandeh/
├── python/                  # Python Implementation Package
│   ├── uxandeh/             # Core package modules
│   │   ├── sona.py          # SplitMix64 & Sona S-box/P-box logic
│   │   ├── compression.py   # IFS round function
│   │   ├── hash.py          # Padding & main compression loop
│   │   └── __init__.py      # Package export interface
│   └── tests/               # Python test suite
│
├── rust/                    # Rust Implementation Crate
│   ├── Cargo.toml           # Cargo manifest (Zero external dependencies)
│   └── src/
│       ├── lib.rs           # Crate public interface
│       ├── sona.rs          # Sona permutations & SplitMix64 port
│       ├── compression.rs   # IFS compression function port
│       ├── hash.rs          # Padding & hashing loop port
│       └── main.rs          # CLI target (hashes stdin to stdout hex)
│
├── verify_cross_compat.py   # Verifies Python/Rust equivalence
├── nist_tests.py            # Custom NIST SP-800-22 statistical test runner
├── README.md
└── LICENSE
```

---

## Getting Started

### Python Usage

```python
import sys
sys.path.append("./python")
from uxandeh import uxandeh

# Compute 256-bit hash (returns 32 bytes)
digest = uxandeh(b"hello world")
print(digest.hex())
# Output: b06850ce5bbd88c29aaafb96c00121e4c79583627a61d1597df377b65890e9b8...
```

Run Python tests:
```bash
python3 -m unittest python/tests/test_uxandeh.py
```

### Rust Usage

Add the library to your cargo project workspace or run the CLI:

```bash
cd rust
cargo build --release
```

To hash a file or input stream via the CLI:
```bash
echo -n "hello world" | cargo run --quiet
# Output: b06850ce5bbd88c29aaafb96c00121e4c79583627a61d1597df377b65890e9b8
```

Run Rust tests:
```bash
cd rust
cargo test
```

---

## Statistical Verification

### 1. Cross-Language Equivalence
A verification script runs test inputs of different lengths (including key boundary conditions) against both implementations to ensure they produce identical hex digests.
```bash
python3 verify_cross_compat.py
```

### 2. Randomness Testing (NIST SP-800-22)
To verify chaos and statistical properties, we generated **2,560,000 bits** by hashing successive integer counters (`"0"`, `"1"`, `"2"`, ...) and evaluated the bitstream using standard NIST statistical tests.
```bash
python3 nist_tests.py
```

All tests passed with exceptionally high p-values ($> 0.80$, well above the threshold $\ge 0.01$):

| NIST SP-800-22 Statistical Test | Measured p-value | Status |
| :--- | :--- | :--- |
| **Frequency (Monobit) Test** | **0.840503** | **PASSED** |
| **Frequency Test within a Block (M=128)** | **0.857485** | **PASSED** |
| **Runs Test** | **0.886665** | **PASSED** |
| **Cumulative Sums (Forward) Test** | **0.814200** | **PASSED** |
| **Cumulative Sums (Backward) Test** | **0.958342** | **PASSED** |

---

## License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.
