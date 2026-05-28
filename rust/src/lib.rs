/// uxandeh: African Fractal Hash (AFH) Library.
///
/// This library implements the African Fractal Hash (AFH) algorithm using discrete
/// Iterated Function Systems (IFS) and Sona Permutations.
///
/// All code and comments follow British English spelling conventions.

pub mod sona;
pub mod compression;
pub mod hash;

pub use hash::uxandeh;
pub use compression::{DEFAULT_IV, PRIME_P};
