"""Sona Permutation Module.

This module implements Chokwe Sona drawing Eulerian path rules to generate
cryptographically secure, key-dependent Substitution-boxes (S-Boxes) and
permutation tables (P-Boxes) for the African Fractal Hash (AFH). All algorithms
are designed using integer-only modular arithmetic over a discrete grid, using
a custom deterministic SplitMix64 PRNG to guarantee cross-language consistency.

All code and comments in this module follow British English spelling conventions.
"""

from typing import List, Tuple, Dict

class SplitMix64:
    """A deterministic 64-bit SplitMix PRNG used to guarantee identical behavior
    between Python and Rust implementations.
    """
    def __init__(self, seed: int):
        self.state = seed & 0xFFFFFFFFFFFFFFFF

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        return (z ^ (z >> 31)) & 0xFFFFFFFFFFFFFFFF

    def rand_range(self, start: int, end: int) -> int:
        length = end - start
        if length <= 0:
            raise ValueError("Invalid range")
        return start + (self.next_u64() % length)

    def shuffle(self, lst: list):
        n = len(lst)
        for i in range(n - 1, 0, -1):
            j = self.rand_range(0, i + 1)
            lst[i], lst[j] = lst[j], lst[i]


def trace_sona_path(
    M: int,
    N: int,
    h_mirrors: List[List[bool]],
    v_mirrors: List[List[bool]],
    start_state: Tuple[int, int, int, int],
) -> List[Tuple[int, int, int, int]]:
    """Trace a single Sona loop on an M x N grid with mirror reflections."""
    x, y, dx, dy = start_state
    visited = set()
    path = []
    state = start_state

    while True:
        if state in visited:
            break
        visited.add(state)
        path.append(state)

        # Calculate next position candidates
        x_next = x + dx
        y_next = y + dy

        dx_next, dy_next = dx, dy
        bounced_x = False
        bounced_y = False

        # Bouncing off boundary walls
        if x_next < 0 or x_next > 2 * M:
            dx_next = -dx
            x_next = x + dx_next
            bounced_x = True
        if y_next < 0 or y_next > 2 * N:
            dy_next = -dy
            y_next = y + dy_next
            bounced_y = True

        # Checking internal mirrors if we did not bounce off the boundary
        if not bounced_x and not bounced_y:
            # Check vertical mirror crossing (odd x_next, even y_next)
            if x_next % 2 != 0 and y_next % 2 == 0:
                i = (x_next - 1) // 2
                j = (y_next - 2) // 2
                if 0 <= i < M and 0 <= j < N - 1:
                    if v_mirrors[i][j]:
                        dx_next = -dx  # Reflect horizontally
            # Check horizontal mirror crossing (even x_next, odd y_next)
            elif x_next % 2 == 0 and y_next % 2 != 0:
                i = (x_next - 2) // 2
                j = (y_next - 1) // 2
                if 0 <= i < M - 1 and 0 <= j < N:
                    if h_mirrors[i][j]:
                        dy_next = -dy  # Reflect vertically

        state = (x_next, y_next, dx_next, dy_next)

        # Normalise boundary states to prevent redundancy
        xn, yn, dxn, dyn = state
        if xn == 0 and dxn != 1:
            dxn = 1
        if xn == 2 * M and dxn != -1:
            dxn = -1
        if yn == 0 and dyn != 1:
            dyn = 1
        if yn == 2 * N and dyn != -1:
            dyn = -1
        state = (xn, yn, dxn, dyn)

        x, y, dx, dy = state

    return path


def trace_all_loops(
    M: int, N: int, h_mirrors: List[List[bool]], v_mirrors: List[List[bool]]
) -> Tuple[List[List[Tuple[int, int, int, int]]], Dict[Tuple[int, int, int, int], int]]:
    """Trace all loops in the Sona grid and assign loop IDs to each state."""
    all_states = set()
    for x in range(2 * M + 1):
        for y in range(2 * N + 1):
            if (x + y) % 2 != 0:
                for dx in [-1, 1]:
                    for dy in [-1, 1]:
                        # Filter out invalid boundary directions
                        if x == 0 and dx != 1:
                            continue
                        if x == 2 * M and dx != -1:
                            continue
                        if y == 0 and dy != 1:
                            continue
                        if y == 2 * N and dy != -1:
                            continue
                        all_states.add((x, y, dx, dy))

    loops = []
    state_to_loop_id = {}
    visited_global = set()

    for start_state in sorted(list(all_states)):
        if start_state in visited_global:
            continue
        loop = trace_sona_path(M, N, h_mirrors, v_mirrors, start_state)
        loop_id = len(loops)
        loops.append(loop)
        for state in loop:
            visited_global.add(state)
            state_to_loop_id[state] = loop_id

    return loops, state_to_loop_id


class UnionFind:
    """Disjoint Set Union (Union-Find) structure for cycle-merging."""
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: int, j: int) -> bool:
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j
            return True
        return False


def generate_monolinear_grid(
    M: int, N: int, seed: int
) -> Tuple[List[List[bool]], List[List[bool]], List[Tuple[int, int, int, int]]]:
    """Generate a key-dependent monolinear Sona grid using loop-merging.

    We trace default loops, build a loop connectivity graph, and place exactly
    g-1 mirrors via a spanning tree to merge all loops into a single curve.
    """
    rng = SplitMix64(seed)

    h_mirrors = [[False] * N for _ in range(M - 1)]
    v_mirrors = [[False] * (N - 1) for _ in range(M)]

    # 1. Trace the base loops with no mirrors
    loops, state_to_loop_id = trace_all_loops(M, N, h_mirrors, v_mirrors)
    num_loops = len(loops)

    # 2. Identify the reverse loop ID for each loop to keep tracking symmetric
    reverse_loop = {}
    for loop_id, loop in enumerate(loops):
        x, y, dx, dy = loop[0]
        dx_rev, dy_rev = -dx, -dy
        if x == 0 and dx_rev != 1:
            dx_rev = 1
        if x == 2 * M and dx_rev != -1:
            dx_rev = -1
        if y == 0 and dy_rev != 1:
            dy_rev = 1
        if y == 2 * N and dy_rev != -1:
            dy_rev = -1
        rev_state = (x, y, dx_rev, dy_rev)
        rev_id = state_to_loop_id[rev_state]
        reverse_loop[loop_id] = rev_id

    uf = UnionFind(num_loops)
    potential_mirrors = []

    # Horizontal mirrors: size (M-1) x N (even x, odd y)
    for i in range(M - 1):
        for j in range(N):
            x_m = 2 * i + 2
            y_m = 2 * j + 1
            s1 = (x_m, y_m, 1, 1)
            s2 = (x_m, y_m, 1, -1)
            l1 = state_to_loop_id.get(s1)
            l2 = state_to_loop_id.get(s2)
            if l1 is not None and l2 is not None and l1 != l2:
                potential_mirrors.append(('H', i, j, l1, l2))

    # Vertical mirrors: size M x (N-1) (odd x, even y)
    for i in range(M):
        for j in range(N - 1):
            x_m = 2 * i + 1
            y_m = 2 * j + 2
            s1 = (x_m, y_m, 1, 1)
            s2 = (x_m, y_m, -1, 1)
            l1 = state_to_loop_id.get(s1)
            l2 = state_to_loop_id.get(s2)
            if l1 is not None and l2 is not None and l1 != l2:
                potential_mirrors.append(('V', i, j, l1, l2))

    # Shuffle mirror candidates to construct a key-dependent spanning tree
    rng.shuffle(potential_mirrors)

    for m_type, i, j, l1, l2 in potential_mirrors:
        r1 = uf.find(l1)
        r2 = uf.find(l2)
        if r1 != r2:
            uf.union(l1, l2)
            uf.union(reverse_loop[l1], reverse_loop[l2])
            if m_type == 'H':
                h_mirrors[i][j] = True
            else:
                v_mirrors[i][j] = True

    # Trace final merged loops
    new_loops, _ = trace_all_loops(M, N, h_mirrors, v_mirrors)
    # The monolinear grid must have exactly 2 loops (1 curve in 2 directions)
    return h_mirrors, v_mirrors, new_loops[0]


def generate_sona_sbox(seed: int, is_pbox: bool = False) -> List[int]:
    """Generate a cryptographically strong 8x8 S-Box or 256-bit P-Box.

    This function uses a monolinear Sona path traversal on a 16x16 grid to do
    a deterministic shuffle of the elements [0..255] to achieve high diffusion
    and confusion.
    """
    # Generate monolinear grid of size 16x16
    grid_seed = seed + 100003 if is_pbox else seed
    h_mirrors, v_mirrors, path = generate_monolinear_grid(16, 16, grid_seed)

    # Perform a Sona-guided Fisher-Yates-like shuffle
    sbox = list(range(256))
    
    coeff_x = 83 if is_pbox else 79
    coeff_y = 103 if is_pbox else 97
    coeff_step = 107 if is_pbox else 101

    for step, state in enumerate(path):
        x, y, dx, dy = state
        idx = (x * coeff_x + y * coeff_y + (dx + 2) * 13 + (dy + 2) * 17 + step * coeff_step) % 256
        swap_idx = step % 256
        sbox[swap_idx], sbox[idx] = sbox[idx], sbox[swap_idx]

    return sbox


def generate_sona_pbox(seed: int) -> List[int]:
    """Generate a key-dependent 256-bit bit-permutation table (P-Box)."""
    return generate_sona_sbox(seed, is_pbox=True)
