/// Sona Permutation module.
///
/// Implements Sona sand drawing Eulerian path rules to generate Substitution-boxes
/// and Bit-permutation boxes using a custom deterministic SplitMix64 PRNG.
///
/// All code and comments follow British English spelling conventions.

use std::collections::{HashMap, HashSet};

pub struct SplitMix64 {
    state: u64,
}

impl SplitMix64 {
    pub fn new(seed: u64) -> Self {
        SplitMix64 { state: seed }
    }

    pub fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E3779B97F4A7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
        z ^ (z >> 31)
    }

    pub fn rand_range(&mut self, start: usize, end: usize) -> usize {
        let length = end - start;
        assert!(length > 0, "Invalid range");
        start + (self.next_u64() as usize % length)
    }

    pub fn shuffle<T>(&mut self, slice: &mut [T]) {
        let n = slice.len();
        for i in (1..n).rev() {
            let j = self.rand_range(0, i + 1);
            slice.swap(i, j);
        }
    }
}

pub fn trace_sona_path(
    m: usize,
    n: usize,
    h_mirrors: &[Vec<bool>],
    v_mirrors: &[Vec<bool>],
    start_state: (i32, i32, i32, i32),
) -> Vec<(i32, i32, i32, i32)> {
    let mut x = start_state.0;
    let mut y = start_state.1;
    let mut dx = start_state.2;
    let mut dy = start_state.3;
    
    let mut visited = HashSet::new();
    let mut path = Vec::new();
    let mut state = start_state;

    loop {
        if visited.contains(&state) {
            break;
        }
        visited.insert(state);
        path.push(state);

        let mut x_next = x + dx;
        let mut y_next = y + dy;

        let mut dx_next = dx;
        let mut dy_next = dy;
        let mut bounced_x = false;
        let mut bounced_y = false;

        // Bouncing off boundary walls
        if x_next < 0 || x_next > 2 * m as i32 {
            dx_next = -dx;
            x_next = x + dx_next;
            bounced_x = true;
        }
        if y_next < 0 || y_next > 2 * n as i32 {
            dy_next = -dy;
            y_next = y + dy_next;
            bounced_y = true;
        }

        // Checking internal mirrors
        if !bounced_x && !bounced_y {
            // Check vertical mirror crossing (odd x_next, even y_next)
            if x_next % 2 != 0 && y_next % 2 == 0 {
                let i = (x_next - 1) / 2;
                let j = (y_next - 2) / 2;
                if i >= 0 && i < m as i32 && j >= 0 && j < (n - 1) as i32 {
                    if v_mirrors[i as usize][j as usize] {
                        dx_next = -dx;
                    }
                }
            // Check horizontal mirror crossing (even x_next, odd y_next)
            } else if x_next % 2 == 0 && y_next % 2 != 0 {
                let i = (x_next - 2) / 2;
                let j = (y_next - 1) / 2;
                if i >= 0 && i < (m - 1) as i32 && j >= 0 && j < n as i32 {
                    if h_mirrors[i as usize][j as usize] {
                        dy_next = -dy;
                    }
                }
            }
        }

        let xn = x_next;
        let yn = y_next;
        let mut dxn = dx_next;
        let mut dyn_ = dy_next;

        if xn == 0 && dxn != 1 {
            dxn = 1;
        }
        if xn == 2 * m as i32 && dxn != -1 {
            dxn = -1;
        }
        if yn == 0 && dyn_ != 1 {
            dyn_ = 1;
        }
        if yn == 2 * n as i32 && dyn_ != -1 {
            dyn_ = -1;
        }

        state = (xn, yn, dxn, dyn_);
        x = state.0;
        y = state.1;
        dx = state.2;
        dy = state.3;
    }

    path
}

pub fn trace_all_loops(
    m: usize,
    n: usize,
    h_mirrors: &[Vec<bool>],
    v_mirrors: &[Vec<bool>],
) -> (Vec<Vec<(i32, i32, i32, i32)>>, HashMap<(i32, i32, i32, i32), usize>) {
    let mut all_states = Vec::new();
    for x in 0..=(2 * m as i32) {
        for y in 0..=(2 * n as i32) {
            if (x + y) % 2 != 0 {
                for dx in &[-1, 1] {
                    for dy in &[-1, 1] {
                        if x == 0 && *dx != 1 {
                            continue;
                        }
                        if x == 2 * m as i32 && *dx != -1 {
                            continue;
                        }
                        if y == 0 && *dy != 1 {
                            continue;
                        }
                        if y == 2 * n as i32 && *dy != -1 {
                            continue;
                        }
                        all_states.push((x, y, *dx, *dy));
                    }
                }
            }
        }
    }

    all_states.sort();

    let mut loops = Vec::new();
    let mut state_to_loop_id = HashMap::new();
    let mut visited_global = HashSet::new();

    for start_state in all_states {
        if visited_global.contains(&start_state) {
            continue;
        }
        let loop_path = trace_sona_path(m, n, h_mirrors, v_mirrors, start_state);
        let loop_id = loops.len();
        loops.push(loop_path.clone());
        for state in loop_path {
            visited_global.insert(state);
            state_to_loop_id.insert(state, loop_id);
        }
    }

    (loops, state_to_loop_id)
}

pub struct UnionFind {
    parent: Vec<usize>,
}

impl UnionFind {
    pub fn new(n: usize) -> Self {
        UnionFind {
            parent: (0..n).collect(),
        }
    }

    pub fn find(&mut self, i: usize) -> usize {
        let mut root = i;
        while self.parent[root] != root {
            root = self.parent[root];
        }
        let mut curr = i;
        while self.parent[curr] != root {
            let next = self.parent[curr];
            self.parent[curr] = root;
            curr = next;
        }
        root
    }

    pub fn union(&mut self, i: usize, j: usize) -> bool {
        let root_i = self.find(i);
        let root_j = self.find(j);
        if root_i != root_j {
            self.parent[root_i] = root_j;
            true
        } else {
            false
        }
    }
}

pub fn generate_monolinear_grid(
    m: usize,
    n: usize,
    seed: u64,
) -> (Vec<Vec<bool>>, Vec<Vec<bool>>, Vec<(i32, i32, i32, i32)>) {
    let mut rng = SplitMix64::new(seed);

    let mut h_mirrors = vec![vec![false; n]; m - 1];
    let mut v_mirrors = vec![vec![false; n - 1]; m];

    // 1. Trace the base loops with no mirrors
    let (loops, state_to_loop_id) = trace_all_loops(m, n, &h_mirrors, &v_mirrors);
    let num_loops = loops.len();

    // 2. Identify the reverse loop ID for each loop to keep tracking symmetric
    let mut reverse_loop = HashMap::new();
    for (loop_id, l_path) in loops.iter().enumerate() {
        let (x, y, dx, dy) = l_path[0];
        let mut dx_rev = -dx;
        let mut dy_rev = -dy;
        if x == 0 && dx_rev != 1 {
            dx_rev = 1;
        }
        if x == 2 * m as i32 && dx_rev != -1 {
            dx_rev = -1;
        }
        if y == 0 && dy_rev != 1 {
            dy_rev = 1;
        }
        if y == 2 * n as i32 && dy_rev != -1 {
            dy_rev = -1;
        }
        let rev_state = (x, y, dx_rev, dy_rev);
        let rev_id = *state_to_loop_id.get(&rev_state).unwrap();
        reverse_loop.insert(loop_id, rev_id);
    }

    let mut uf = UnionFind::new(num_loops);
    let mut potential_mirrors = Vec::new();

    // Horizontal mirrors: size (M-1) x N (even x, odd y)
    for i in 0..(m - 1) {
        for j in 0..n {
            let x_m = 2 * i as i32 + 2;
            let y_m = 2 * j as i32 + 1;
            let s1 = (x_m, y_m, 1, 1);
            let s2 = (x_m, y_m, 1, -1);
            if let (Some(&l1), Some(&l2)) = (state_to_loop_id.get(&s1), state_to_loop_id.get(&s2)) {
                if l1 != l2 {
                    potential_mirrors.push(('H', i, j, l1, l2));
                }
            }
        }
    }

    // Vertical mirrors: size M x (N-1) (odd x, even y)
    for i in 0..m {
        for j in 0..(n - 1) {
            let x_m = 2 * i as i32 + 1;
            let y_m = 2 * j as i32 + 2;
            let s1 = (x_m, y_m, 1, 1);
            let s2 = (x_m, y_m, -1, 1);
            if let (Some(&l1), Some(&l2)) = (state_to_loop_id.get(&s1), state_to_loop_id.get(&s2)) {
                if l1 != l2 {
                    potential_mirrors.push(('V', i, j, l1, l2));
                }
            }
        }
    }

    // Shuffle mirror candidates to construct a key-dependent spanning tree
    rng.shuffle(&mut potential_mirrors);

    for (m_type, i, j, l1, l2) in potential_mirrors {
        let r1 = uf.find(l1);
        let r2 = uf.find(l2);
        if r1 != r2 {
            uf.union(l1, l2);
            let rev_l1 = *reverse_loop.get(&l1).unwrap();
            let rev_l2 = *reverse_loop.get(&l2).unwrap();
            uf.union(rev_l1, rev_l2);
            if m_type == 'H' {
                h_mirrors[i][j] = true;
            } else {
                v_mirrors[i][j] = true;
            }
        }
    }

    // Trace final merged loops
    let (new_loops, _) = trace_all_loops(m, n, &h_mirrors, &v_mirrors);
    (h_mirrors, v_mirrors, new_loops[0].clone())
}

pub fn generate_sona_sbox(seed: u64, is_pbox: bool) -> [u8; 256] {
    let grid_seed = if is_pbox { seed.wrapping_add(100003) } else { seed };
    let (_, _, path) = generate_monolinear_grid(16, 16, grid_seed);

    let mut sbox = [0u8; 256];
    for i in 0..256 {
        sbox[i] = i as u8;
    }

    let coeff_x = if is_pbox { 83 } else { 79 };
    let coeff_y = if is_pbox { 103 } else { 97 };
    let coeff_step = if is_pbox { 107 } else { 101 };

    for (step, state) in path.iter().enumerate() {
        let (x, y, dx, dy) = *state;
        let idx = (x * coeff_x + y * coeff_y + (dx + 2) * 13 + (dy + 2) * 17 + step as i32 * coeff_step) as usize % 256;
        let swap_idx = step % 256;
        sbox.swap(swap_idx, idx);
    }

    sbox
}
