/// CLI tool for computing the African Fractal Hash (uxandeh) of stdin.
///
/// All code and comments follow British English spelling conventions.

use std::io::{self, Read};
use uxandeh::uxandeh;

fn main() -> io::Result<()> {
    let mut buffer = Vec::new();
    io::stdin().read_to_end(&mut buffer)?;
    
    let digest = uxandeh(&buffer);
    
    for byte in digest {
        print!("{:02x}", byte);
    }
    println!();
    
    Ok(())
}
