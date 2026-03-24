"""
Computational String Art Algorithm (Improved)
==============================================
Based on: Birsak et al., "String Art: Towards Computational Fabrication
of String Images", Eurographics 2018

Key improvements over basic greedy approach:
  1. Physically-based multiplicative opacity model (Beer-Lambert law)
     – each string multiplies transmittance by (1 − α), preventing
       over-darkening and modelling real thread stacking.
  2. L2 energy minimisation for string selection – each candidate is
     scored by how much it reduces the total weighted squared error.
  3. Importance-weighted error map – Sobel edge magnitude gives higher
     priority to structural details and contours.
  4. Sparse regularised objective – explicit penalties for each added
      string, introducing new pins, and repeatedly reusing a pin pair.
  5. Two-step beam lookahead search – improves global decision quality
      over pure one-step greedy choice.
  6. Smart starting-pin selection – picks the pin with greatest
     immediate error-reduction potential.
  7. Refinement pass – replays the sequence re-evaluating every string
     choice in the updated context, swapping in better alternatives.
  8. Sequence compression pass – replaces local two-edge patterns with
      one edge when objective loss is small, reducing thread count.
  9. Robust stopping criteria based on trend analysis.

Optimisation inspirations and references:
  - Birsak et al. (2018), computational string art energy minimisation.
  - Limited-horizon/beam search for combinatorial sequence planning.
  - Sparse model selection with explicit complexity penalties (L0/L1 idea).
  - Local search / shortcut compression for route simplification.

Inputs:
    - Grayscale image (the target to reproduce)
    - Number of pins (evenly placed on a circle)
    - Maximum number of strings
    - String opacity (how opaque each thread is, 0–1)

Outputs:
    - Rendered string art image
    - Ordered sequence of pin indices (for physical fabrication)
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import matplotlib.pyplot as plt
import sys
import os
import multiprocessing
from concurrent.futures import ThreadPoolExecutor


# ---------------------------------------------------------------------------
# Line rasterization (anti-aliased) – standalone so we avoid hard dependency
# on scikit-image.  Falls back to skimage.draw.line_aa if available.
# ---------------------------------------------------------------------------

def _line_aa_builtin(y0, x0, y1, x1):
    """Xiaolin-Wu style anti-aliased line rasterisation.

    Returns
    -------
    rr, cc : ndarray of int
        Row and column indices of pixels along the line.
    val : ndarray of float
        Intensity weight for each pixel (0.0 – 1.0).
    """
    try:
        from skimage.draw import line_aa  # type: ignore[reportMissingModuleSource]
        return line_aa(y0, x0, y1, x1)
    except ImportError:
        pass

    # Pure-numpy fallback (Xiaolin Wu)
    steep = abs(y1 - y0) > abs(x1 - x0)
    if steep:
        x0, y0 = y0, x0
        x1, y1 = y1, x1
    if x0 > x1:
        x0, x1 = x1, x0
        y0, y1 = y1, y0

    dx = x1 - x0
    dy = y1 - y0
    gradient = dy / dx if dx != 0 else 1.0

    rows, cols, vals = [], [], []

    # First endpoint
    xend = round(x0)
    yend = y0 + gradient * (xend - x0)
    xpxl1 = int(xend)
    ypxl1 = int(np.floor(yend))
    rows += [ypxl1, ypxl1 + 1]
    cols += [xpxl1, xpxl1]
    frac = yend - np.floor(yend)
    vals += [1 - frac, frac]

    intery = yend + gradient

    # Second endpoint
    xend = round(x1)
    yend = y1 + gradient * (xend - x1)
    xpxl2 = int(xend)
    ypxl2 = int(np.floor(yend))
    rows += [ypxl2, ypxl2 + 1]
    cols += [xpxl2, xpxl2]
    frac = yend - np.floor(yend)
    vals += [1 - frac, frac]

    # Main loop
    for x in range(xpxl1 + 1, xpxl2):
        y_floor = int(np.floor(intery))
        frac = intery - y_floor
        rows += [y_floor, y_floor + 1]
        cols += [x, x]
        vals += [1 - frac, frac]
        intery += gradient

    rr = np.array(rows, dtype=np.intp)
    cc = np.array(cols, dtype=np.intp)
    val = np.array(vals, dtype=np.float64)

    if steep:
        rr, cc = cc, rr

    return rr, cc, val


# ---------------------------------------------------------------------------
# Worker function for parallel line precomputation (module-level for
# multiprocessing pickle compatibility)
# ---------------------------------------------------------------------------

def _compute_line_worker(args):
    """Compute one anti-aliased line for a pin pair (multiprocessing worker)."""
    i, j, r0, c0, r1, c1, img_size = args
    rr, cc, val = _line_aa_builtin(r0, c0, r1, c1)
    good = (rr >= 0) & (rr < img_size) & (cc >= 0) & (cc < img_size)
    return (i, j), (rr[good], cc[good], val[good])


# ---------------------------------------------------------------------------
# Core String Art class
# ---------------------------------------------------------------------------

class StringArt:
    """Energy-minimising computational string art generator.

    Uses a physically-based multiplicative opacity model and picks every
    string by maximising the reduction in weighted L2 error between the
    target image and the current rendering (Birsak et al. 2018).

    Parameters
    ----------
    image_path : str
        Path to the input image (any format PIL can read).
    num_pins : int
        Number of pins placed evenly around a circular frame.
    max_strings : int
        Maximum number of strings (iterations).
    string_opacity : float
        How opaque a single thread is (0.0 – 1.0).  For typical sewing
        thread on a white board use 0.08 – 0.20.
    min_pin_distance : int
        Minimum number of pins apart two connected pins must be
        (avoids very short, unnoticeable strings).
    img_size : int
        The image is resized to img_size × img_size for processing.
    importance_edge_weight : float
        Extra importance given to edge / detail pixels (0 = uniform).
    refinement_rounds : int
        Number of post-construction refinement passes that re-evaluate
        every string choice in its updated context.
    """

    def __init__(
        self,
        image_path: str,
        num_pins: int = 288,
        max_strings: int = 10000,
        string_opacity: float = 0.08,
        min_pin_distance: int = 20,
        img_size: int = 700,
        importance_edge_weight: float = 1.5,
        refinement_rounds: int = 1,
        string_cost: float = 3000.0,
        new_pin_cost: float = 2500.0,
        pair_reuse_cost: float = 1200.0,
        lookahead_width: int = 24,
        lookahead_weight: float = 0.35,
        compression_rounds: int = 2,
        compression_tolerance: float = 1500.0,
        mcmc_steps: int = 50000,
        mcmc_temp_init: float = 5.0,
        mcmc_temp_end: float = 0.05,
        num_workers: int = 0,
    ):
        self.num_pins = num_pins
        self.max_strings = max_strings
        self.string_opacity = float(np.clip(string_opacity, 0.005, 0.5))
        self.min_pin_distance = min_pin_distance
        self.img_size = img_size
        self.importance_edge_weight = importance_edge_weight
        self.refinement_rounds = refinement_rounds
        self.string_cost = max(0.0, float(string_cost))
        self.new_pin_cost = max(0.0, float(new_pin_cost))
        self.pair_reuse_cost = max(0.0, float(pair_reuse_cost))
        self.lookahead_width = max(1, int(lookahead_width))
        self.lookahead_weight = float(np.clip(lookahead_weight, 0.0, 1.0))
        self.compression_rounds = max(0, int(compression_rounds))
        self.compression_tolerance = float(compression_tolerance)
        self.mcmc_steps = max(0, int(mcmc_steps))
        self.mcmc_temp_init = max(0.0001, float(mcmc_temp_init))
        self.mcmc_temp_end = max(0.000001, float(mcmc_temp_end))
        self._num_workers = num_workers if num_workers > 0 else (os.cpu_count() or 4)

        # Geometry -----------------------------------------------------------
        self.mask = self._circular_mask()

        # Load & pre-process (normal orientation: 0 = black, 255 = white) ---
        self.target = self._load_image(image_path)
        self.target = self.target * self.mask + 255.0 * (1.0 - self.mask)

        # Importance map (edge-aware) ----------------------------------------
        self.importance = self._compute_importance_map()

        # Pin geometry -------------------------------------------------------
        self.pin_coords = self._compute_pin_positions()

        # Pre-compute every valid line's pixel coordinates -------------------
        self.line_cache: dict[tuple[int, int], tuple] = {}
        self._precompute_lines()

        # Pre-compute per-pin valid neighbours for fast iteration ------------
        self.pin_neighbours: list[list[int]] = self._precompute_neighbours()

        # Results (filled after .run()) --------------------------------------
        self.string_sequence: list[int] = []
        self.result_image: np.ndarray | None = None
        self.transmittance: np.ndarray | None = None

    # ---- Image loading & preprocessing ------------------------------------

    def _load_image(self, path: str) -> np.ndarray:
        """Load → grayscale → resize → contrast enhance.

        Returns image in [0, 255] where 0 = black, 255 = white.
        """
        img = Image.open(path).convert("L")
        img = img.resize((self.img_size, self.img_size), Image.LANCZOS)

        arr = np.array(img, dtype=np.float64)

        # Percentile-based contrast stretching (within the circular mask)
        mask_pixels = arr[self.mask > 0.5]
        lo, hi = np.percentile(mask_pixels, 2), np.percentile(mask_pixels, 98)
        if hi - lo > 1:
            arr = np.clip((arr - lo) / (hi - lo), 0.0, 1.0) * 255.0

        return arr

    # ---- Importance / edge map --------------------------------------------

    def _compute_importance_map(self) -> np.ndarray:
        """Edge-aware importance weighting via Sobel magnitude.

        Pixels near edges get higher weight so the algorithm prioritises
        reproducing structural details over flat shading.
        """
        if self.importance_edge_weight <= 0:
            return self.mask.copy()

        img_u8 = np.clip(self.target, 0, 255).astype(np.uint8)
        pil_img = Image.fromarray(img_u8, mode="L")

        try:
            sx = pil_img.filter(ImageFilter.Kernel(
                (3, 3), [-1, 0, 1, -2, 0, 2, -1, 0, 1], scale=1, offset=128
            ))
            sy = pil_img.filter(ImageFilter.Kernel(
                (3, 3), [-1, -2, -1, 0, 0, 0, 1, 2, 1], scale=1, offset=128
            ))
            ex = np.array(sx, dtype=np.float64) - 128.0
            ey = np.array(sy, dtype=np.float64) - 128.0
            edge_mag = np.sqrt(ex ** 2 + ey ** 2)
        except Exception:
            edges = pil_img.filter(ImageFilter.FIND_EDGES)
            edge_mag = np.array(edges, dtype=np.float64)

        emax = edge_mag.max()
        if emax > 0:
            edge_mag /= emax

        importance = 1.0 + self.importance_edge_weight * edge_mag
        importance *= self.mask
        return importance

    # ---- Geometry helpers -------------------------------------------------

    def _circular_mask(self) -> np.ndarray:
        centre = self.img_size / 2.0
        radius = centre - 1
        Y, X = np.ogrid[: self.img_size, : self.img_size]
        return ((X - centre) ** 2 + (Y - centre) ** 2 <= radius ** 2).astype(
            np.float64
        )

    def _compute_pin_positions(self) -> list[tuple[int, int]]:
        """Return (row, col) for each pin, evenly spaced on a circle."""
        centre = self.img_size / 2.0
        radius = centre - 1
        angles = np.linspace(0, 2 * np.pi, self.num_pins, endpoint=False)
        pins = []
        for a in angles:
            c = int(np.clip(centre + radius * np.cos(a), 0, self.img_size - 1))
            r = int(np.clip(centre + radius * np.sin(a), 0, self.img_size - 1))
            pins.append((r, c))
        return pins

    # ---- Line pre-computation ---------------------------------------------

    def _precompute_lines(self):
        """Cache anti-aliased pixel coords for every valid pin pair (parallel)."""
        print(f"Pre-computing line pixel coordinates ({self._num_workers} workers) …")
        tasks = []
        for i in range(self.num_pins):
            for j in range(i + 1, self.num_pins):
                arc = min(abs(i - j), self.num_pins - abs(i - j))
                if arc < self.min_pin_distance:
                    continue
                r0, c0 = self.pin_coords[i]
                r1, c1 = self.pin_coords[j]
                tasks.append((i, j, r0, c0, r1, c1, self.img_size))

        with multiprocessing.Pool(processes=self._num_workers) as pool:
            results = pool.map(_compute_line_worker, tasks, chunksize=256)

        for key, line_data in results:
            self.line_cache[key] = line_data

        print(f"  → {len(self.line_cache):,} valid lines cached.")

    def _precompute_neighbours(self) -> list[list[int]]:
        """For every pin, list valid destination pins (respecting min distance)."""
        neighbours: list[list[int]] = [[] for _ in range(self.num_pins)]
        for i in range(self.num_pins):
            for j in range(self.num_pins):
                if i == j:
                    continue
                arc = min(abs(i - j), self.num_pins - abs(i - j))
                if arc >= self.min_pin_distance:
                    key = (min(i, j), max(i, j))
                    if key in self.line_cache:
                        neighbours[i].append(j)
        return neighbours

    # ---- Energy & scoring -------------------------------------------------

    def _mse(self, transmittance: np.ndarray) -> float:
        """Mean squared error (unweighted, within circular mask)."""
        rendered = 255.0 * transmittance
        diff = (rendered - self.target) * self.mask
        n_pixels = np.sum(self.mask)
        return float(np.sum(diff ** 2) / (n_pixels + 1e-10))

    def _weighted_energy(self, transmittance: np.ndarray) -> float:
        """Importance-weighted sum of squared errors."""
        rendered = 255.0 * transmittance
        diff = rendered - self.target
        return float(np.sum(self.importance * diff ** 2))

    def _line_error_reduction(
        self, transmittance: np.ndarray, pin_a: int, pin_b: int
    ) -> float:
        """Compute the reduction in weighted L2 error from adding a string.

        Closed-form derivation (multiplicative opacity model):
            R_i  = 255 · T_i         (current rendered value at pixel i)
            R'_i = R_i · (1 − α·v_i) (value after adding the string)
            ΔE = Σ W_i · s_i · (2·d_i − s_i)
        where
            d_i = R_i − target_i   (positive when pixel is too bright)
            s_i = R_i · α · v_i    (amount of darkening applied)

        Returns positive value when the string reduces the error.
        """
        key = (min(pin_a, pin_b), max(pin_a, pin_b))
        if key not in self.line_cache:
            return -np.inf
        rr, cc, val = self.line_cache[key]
        if len(rr) == 0:
            return 0.0

        R = 255.0 * transmittance[rr, cc]  # current rendered
        T = self.target[rr, cc]             # target
        W = self.importance[rr, cc]         # importance weights
        a = self.string_opacity * val       # effective per-pixel opacity

        s = R * a                           # darkening amount
        d = R - T                           # residual (>0 means too bright)

        # ΔE = Σ W·s·(2d − s)  — positive ↔ error decreases
        return float(np.sum(W * s * (2.0 * d - s)))

    def _regularized_gain(
        self,
        raw_gain: float,
        src_pin: int,
        dst_pin: int,
        pair_usage: dict[tuple[int, int], int],
        used_pins: set[int],
    ) -> float:
        """Convert raw energy gain to sparse-regularized utility.

        This follows sparse optimisation ideas used in L0/L1-style model
        selection: we reward image fidelity gain but subtract explicit costs
        for adding strings, introducing new pins, and over-reusing one pair.
        """
        if not np.isfinite(raw_gain):
            return -np.inf

        pair = (min(src_pin, dst_pin), max(src_pin, dst_pin))
        reuse_penalty = self.pair_reuse_cost * pair_usage.get(pair, 0)
        novelty_penalty = self.new_pin_cost if dst_pin not in used_pins else 0.0
        total_penalty = self.string_cost + reuse_penalty + novelty_penalty
        return raw_gain - total_penalty

    # ---- Starting-pin selection -------------------------------------------

    def _find_best_start(self, transmittance: np.ndarray) -> int:
        """Pick the starting pin whose best outgoing line offers the most
        error reduction (parallelised across CPU cores)."""
        def _eval_pin(pin):
            best = -np.inf
            for cand in self.pin_neighbours[pin]:
                sc = self._line_error_reduction(transmittance, pin, cand)
                if sc > best:
                    best = sc
            return pin, best

        with ThreadPoolExecutor(max_workers=self._num_workers) as pool:
            results = list(pool.map(_eval_pin, range(self.num_pins)))

        return max(results, key=lambda x: x[1])[0]

    def _apply_string(self, transmittance: np.ndarray, pin_a: int, pin_b: int):
        """Apply one string to transmittance using multiplicative opacity."""
        key = (min(pin_a, pin_b), max(pin_a, pin_b))
        if key in self.line_cache:
            rr, cc, val = self.line_cache[key]
            transmittance[rr, cc] *= (1.0 - self.string_opacity * val)

    def _remove_string(self, transmittance: np.ndarray, pin_a: int, pin_b: int):
        """Remove one string from transmittance (inverse of apply, valid since op < 1)."""
        key = (min(pin_a, pin_b), max(pin_a, pin_b))
        if key in self.line_cache:
            rr, cc, val = self.line_cache[key]
            transmittance[rr, cc] /= (1.0 - self.string_opacity * val)

    def _eval_candidates(
        self,
        transmittance,
        current_pin,
        candidates,
        pair_usage,
        used_pins,
    ):
        """Evaluate a chunk of candidate pins (thread worker).

        Returns the best move by sparse-regularized utility.
        """
        best_reg = -np.inf
        best_raw = -np.inf
        best_pin = -1
        for cand in candidates:
            raw = self._line_error_reduction(transmittance, current_pin, cand)
            reg = self._regularized_gain(
                raw, current_pin, cand, pair_usage, used_pins
            )
            if reg > best_reg:
                best_reg = reg
                best_raw = raw
                best_pin = cand
        return best_pin, best_raw, best_reg

    def _best_move_with_lookahead(
        self,
        transmittance: np.ndarray,
        current_pin: int,
        pair_usage: dict[tuple[int, int], int],
        used_pins: set[int],
    ) -> tuple[int, float, float, float]:
        """Choose next move using 2-step lookahead over top candidates.

        Research motivation:
        - Beam search / limited-horizon planning for combinatorial routing.
        - Sparse regularisation (penalised objective) to reduce solution size.
        """
        candidates = self.pin_neighbours[current_pin]
        if not candidates:
            return -1, -np.inf, -np.inf, -np.inf

        # Step 1: immediate sparse-regularized ranking.
        scored = []
        for cand in candidates:
            raw = self._line_error_reduction(transmittance, current_pin, cand)
            reg = self._regularized_gain(raw, current_pin, cand, pair_usage, used_pins)
            scored.append((cand, raw, reg))

        if not scored:
            return -1, -np.inf, -np.inf, -np.inf

        scored.sort(key=lambda x: x[2], reverse=True)
        best_pin, best_raw, best_reg = scored[0]

        # Step 2: optional 2-step lookahead on top-K candidates (beam).
        top = scored[: min(self.lookahead_width, len(scored))]
        best_combined = -np.inf
        sel_pin, sel_raw, sel_reg = best_pin, best_raw, best_reg

        for cand, raw, reg in top:
            if cand == -1:
                continue

            trans2 = transmittance.copy()
            self._apply_string(trans2, current_pin, cand)

            pair2 = dict(pair_usage)
            key2 = (min(current_pin, cand), max(current_pin, cand))
            pair2[key2] = pair2.get(key2, 0) + 1
            used2 = set(used_pins)
            used2.add(cand)

            next_best_reg = -np.inf
            for nxt in self.pin_neighbours[cand]:
                nxt_raw = self._line_error_reduction(trans2, cand, nxt)
                nxt_reg = self._regularized_gain(nxt_raw, cand, nxt, pair2, used2)
                if nxt_reg > next_best_reg:
                    next_best_reg = nxt_reg

            if not np.isfinite(next_best_reg):
                next_best_reg = 0.0

            combined = reg + self.lookahead_weight * max(0.0, next_best_reg)
            if combined > best_combined:
                best_combined = combined
                sel_pin, sel_raw, sel_reg = cand, raw, reg

        return sel_pin, sel_raw, sel_reg, best_combined

    def _compress_sequence(self, seq: list[int], verbose: bool = False) -> list[int]:
        """Compress sequence by replacing (a->b->c) with (a->c) when beneficial.

        This pass explicitly targets lower thread count and fewer active pins
        while keeping objective quality near the current solution.
        """
        if len(seq) < 3:
            return seq

        trans = np.ones((self.img_size, self.img_size), dtype=np.float64)
        pair_usage: dict[tuple[int, int], int] = {}
        used_pins: set[int] = {seq[0]}

        new_seq = [seq[0]]
        i = 0
        compressed = 0

        while i < len(seq) - 1:
            if i + 2 >= len(seq):
                a, b = seq[i], seq[i + 1]
                self._apply_string(trans, a, b)
                key = (min(a, b), max(a, b))
                pair_usage[key] = pair_usage.get(key, 0) + 1
                used_pins.add(b)
                new_seq.append(b)
                i += 1
                continue

            a, b, c = seq[i], seq[i + 1], seq[i + 2]
            key_ac = (min(a, c), max(a, c))
            can_shortcut = key_ac in self.line_cache

            util_one = -np.inf
            if can_shortcut:
                raw_ac = self._line_error_reduction(trans, a, c)
                util_one = self._regularized_gain(raw_ac, a, c, pair_usage, used_pins)

            raw_ab = self._line_error_reduction(trans, a, b)
            util_ab = self._regularized_gain(raw_ab, a, b, pair_usage, used_pins)
            trans_tmp = trans.copy()
            self._apply_string(trans_tmp, a, b)
            pair_tmp = dict(pair_usage)
            key_ab = (min(a, b), max(a, b))
            pair_tmp[key_ab] = pair_tmp.get(key_ab, 0) + 1
            used_tmp = set(used_pins)
            used_tmp.add(b)
            raw_bc = self._line_error_reduction(trans_tmp, b, c)
            util_bc = self._regularized_gain(raw_bc, b, c, pair_tmp, used_tmp)
            util_two = util_ab + util_bc

            if can_shortcut and util_one >= (util_two - self.compression_tolerance):
                self._apply_string(trans, a, c)
                pair_usage[key_ac] = pair_usage.get(key_ac, 0) + 1
                used_pins.add(c)
                new_seq.append(c)
                compressed += 1
                i += 2
            else:
                self._apply_string(trans, a, b)
                pair_usage[key_ab] = pair_usage.get(key_ab, 0) + 1
                used_pins.add(b)
                new_seq.append(b)
                i += 1

        if verbose:
            print(
                f"    Compression pass: {compressed} shortcuts, "
                f"strings {len(seq) - 1} -> {len(new_seq) - 1}"
            )

        return new_seq

    def _simulated_annealing(self, seq: list[int], verbose: bool = True) -> list[int]:
        """Global optimization via Markov Chain Monte Carlo (Simulated Annealing)."""
        if self.mcmc_steps <= 0 or len(seq) < 4:
            return seq

        import random
        import math

        trans = np.ones((self.img_size, self.img_size), dtype=np.float64)
        for i in range(len(seq) - 1):
            self._apply_string(trans, seq[i], seq[i + 1])

        def eval_cost(current_seq, current_trans):
            E = self._weighted_energy(current_trans)
            pairs = {}
            for i in range(len(current_seq) - 1):
                a, b = current_seq[i], current_seq[i + 1]
                k = (min(a, b), max(a, b))
                pairs[k] = pairs.get(k, 0) + 1
            
            cost = E
            cost += len(current_seq) * self.string_cost
            cost += len(set(current_seq)) * self.new_pin_cost
            for count in pairs.values():
                cost += count * (count) * 0.5 * self.pair_reuse_cost
            return cost

        current_cost = eval_cost(seq, trans)
        best_seq = list(seq)
        best_cost = current_cost
        
        t_init = self.mcmc_temp_init
        t_end = self.mcmc_temp_end
        steps = self.mcmc_steps

        accepted = 0
        improved = 0

        if verbose:
            print(f"  ── Phase 4: Simulated Annealing (MCMC, {steps:,} steps) ──")
            print(f"    Initial cost: {current_cost:,.1f}")

        for step in range(steps):
            frac = step / float(steps)
            T = t_init * ((t_end / t_init) ** frac)

            # Node displacement (replace) or skip (delete) or insert
            mut = random.choices(['replace', 'delete', 'insert'], weights=[0.5, 0.25, 0.25])[0]
            n = len(seq)
            
            if mut == 'replace' and n > 2:
                idx = random.randint(1, n - 2)
                old_p = seq[idx]
                p_prev, p_next = seq[idx - 1], seq[idx + 1]
                
                n1 = set(self.pin_neighbours[p_prev])
                n2 = set(self.pin_neighbours[p_next])
                valid = list(n1.intersection(n2) - {old_p, p_prev, p_next})
                if not valid: continue
                new_p = random.choice(valid)

                self._remove_string(trans, p_prev, old_p)
                self._remove_string(trans, old_p, p_next)
                self._apply_string(trans, p_prev, new_p)
                self._apply_string(trans, new_p, p_next)
                seq[idx] = new_p

                new_cost = eval_cost(seq, trans)
                delta = new_cost - current_cost

                if delta < 0 or random.random() < math.exp(-delta / T):
                    current_cost = new_cost
                    accepted += 1
                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_seq = list(seq)
                        improved += 1
                else:
                    seq[idx] = old_p
                    self._remove_string(trans, p_prev, new_p)
                    self._remove_string(trans, new_p, p_next)
                    self._apply_string(trans, p_prev, old_p)
                    self._apply_string(trans, old_p, p_next)

            elif mut == 'delete' and n > 3:
                idx = random.randint(1, n - 2)
                old_p = seq[idx]
                p_prev, p_next = seq[idx - 1], seq[idx + 1]
                
                if p_next not in self.pin_neighbours[p_prev]:
                    continue

                self._remove_string(trans, p_prev, old_p)
                self._remove_string(trans, old_p, p_next)
                self._apply_string(trans, p_prev, p_next)
                seq.pop(idx)

                new_cost = eval_cost(seq, trans)
                delta = new_cost - current_cost

                if delta < 0 or random.random() < math.exp(-delta / T):
                    current_cost = new_cost
                    accepted += 1
                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_seq = list(seq)
                        improved += 1
                else:
                    seq.insert(idx, old_p)
                    self._remove_string(trans, p_prev, p_next)
                    self._apply_string(trans, p_prev, old_p)
                    self._apply_string(trans, old_p, p_next)

            elif mut == 'insert' and n > 1:
                idx = random.randint(0, n - 2)
                p_prev, p_next = seq[idx], seq[idx + 1]
                
                n1 = set(self.pin_neighbours[p_prev])
                n2 = set(self.pin_neighbours[p_next])
                valid = list(n1.intersection(n2) - {p_prev, p_next})
                if not valid: continue
                new_p = random.choice(valid)

                self._remove_string(trans, p_prev, p_next)
                self._apply_string(trans, p_prev, new_p)
                self._apply_string(trans, new_p, p_next)
                seq.insert(idx + 1, new_p)

                new_cost = eval_cost(seq, trans)
                delta = new_cost - current_cost

                if delta < 0 or random.random() < math.exp(-delta / T):
                    current_cost = new_cost
                    accepted += 1
                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_seq = list(seq)
                        improved += 1
                else:
                    seq.pop(idx + 1)
                    self._remove_string(trans, p_prev, new_p)
                    self._remove_string(trans, new_p, p_next)
                    self._apply_string(trans, p_prev, p_next)

            # Prevent float drift over millions of small mult/div
            if step > 0 and step % 4000 == 0:
                trans.fill(1.0)
                for i in range(len(seq) - 1):
                    self._apply_string(trans, seq[i], seq[i + 1])
                current_cost = eval_cost(seq, trans)

            if verbose and (step + 1) % (steps // 10) == 0:
                print(f"    Step {step + 1:>7}/{steps} │ Cost: {current_cost:11,.1f} │ Best: {best_cost:11,.1f} │ Acc: {accepted:,}")
                accepted = 0

        if verbose:
            print(f"  MCMC done. Improved global best {improved} times.")
            print(f"  Strings {len(seq) - 1} -> {len(best_seq) - 1}")
            print()

        return best_seq

    # ---- Main algorithm ---------------------------------------------------

    def run(self, verbose: bool = True):
        """Execute the energy-minimising string art algorithm.

        Phase 1 – Greedy construction:
            Iteratively add the string that maximises weighted L2 error
            reduction, using a multiplicative opacity model.

        Phase 2 – Refinement:
            Replay the sequence from scratch, re-evaluating every string
            choice in its updated context and swapping in better
            alternatives where possible.

        Returns
        -------
        string_sequence : list[int]
            Ordered pin indices.
        result_image : np.ndarray
            Final rendered image (0-255, normal orientation).
        """
        # Transmittance starts at 1.0 everywhere (fully white canvas)
        transmittance = np.ones(
            (self.img_size, self.img_size), dtype=np.float64
        )
        pair_usage: dict[tuple[int, int], int] = {}
        used_pins: set[int] = set()

        self._thread_pool = ThreadPoolExecutor(max_workers=self._num_workers)

        if verbose:
            print()
            print("=" * 60)
            print("  STRING ART – Energy Minimisation (Birsak et al. 2018)")
            print("=" * 60)
            print(f"  Pins              : {self.num_pins}")
            print(f"  Max strings       : {self.max_strings}")
            print(f"  String opacity    : {self.string_opacity:.3f}")
            print(f"  Min pin distance  : {self.min_pin_distance}")
            print(f"  Image size        : {self.img_size}×{self.img_size}")
            print(f"  Edge importance   : {self.importance_edge_weight:.1f}")
            print(f"  Refinement rounds : {self.refinement_rounds}")
            print(f"  String cost       : {self.string_cost:.1f}")
            print(f"  New-pin cost      : {self.new_pin_cost:.1f}")
            print(f"  Pair-reuse cost   : {self.pair_reuse_cost:.1f}")
            print(f"  Lookahead (K,w)   : {self.lookahead_width}, {self.lookahead_weight:.2f}")
            print(f"  Compression rounds: {self.compression_rounds}")
            print(f"  CPU workers       : {self._num_workers}")
            init_mse = self._mse(transmittance)
            print(f"  Initial MSE       : {init_mse:.1f}")
            print()

        # ================================================================
        # Phase 1: Greedy construction
        # ================================================================
        if verbose:
            print("  ── Phase 1: Greedy Construction ──")

        current_pin = self._find_best_start(transmittance)
        self.string_sequence = [current_pin]
        used_pins.add(current_pin)

        if verbose:
            print(f"  Best starting pin : {current_pin}")

        score_history: list[float] = []
        stall_count = 0

        for it in range(self.max_strings):
            # Command: choose next line using sparse objective + 2-step lookahead.
            best_pin, best_raw, best_reg, best_combined = self._best_move_with_lookahead(
                transmittance, current_pin, pair_usage, used_pins
            )

            # ── Stopping: no error-reducing string found ──
            if best_reg <= 0 or best_pin == -1:
                if verbose:
                    print(
                        f"  STOP at string {it}: "
                        f"regularized gain <= 0"
                    )
                break

            # ── Apply string (multiplicative opacity) ──
            key = (min(current_pin, best_pin), max(current_pin, best_pin))
            self._apply_string(transmittance, current_pin, best_pin)

            pair_usage[key] = pair_usage.get(key, 0) + 1
            self.string_sequence.append(best_pin)
            used_pins.add(best_pin)
            current_pin = best_pin

            # ── Adaptive stopping based on score trend ──
            score_history.append(best_reg)
            window = 800
            if len(score_history) > window:
                recent_avg = np.mean(score_history[-window:])
                early_avg = np.mean(score_history[:window])
                if recent_avg < 0.005 * early_avg:
                    stall_count += 1
                    if stall_count > 80:
                        if verbose:
                            print(
                                f"  STOP at string {it}: "
                                f"negligible improvement"
                            )
                        break
                else:
                    stall_count = 0

            # Progress reporting
            if verbose and (it + 1) % 1000 == 0:
                cur_mse = self._mse(transmittance)
                print(
                    f"    {it + 1:>5}/{self.max_strings}  │  "
                    f"MSE {cur_mse:7.1f}  │  "
                    f"rawΔ {best_raw:10.1f}  │  "
                    f"regΔ {best_reg:10.1f}  │  "
                    f"beam {best_combined:10.1f}  │  "
                    f"pairs {len(pair_usage):,} │ used pins {len(used_pins)}"
                )

        n_greedy = len(self.string_sequence) - 1
        if verbose:
            greedy_mse = self._mse(transmittance)
            print(
                f"  Greedy done: {n_greedy} strings, MSE = {greedy_mse:.1f}"
            )
            print()

        # ================================================================
        # Phase 2: Refinement  (re-evaluate each string in updated context)
        # ================================================================
        for ref_round in range(self.refinement_rounds):
            if verbose:
                print(
                    f"  ── Phase 2: Refinement "
                    f"(round {ref_round + 1}/{self.refinement_rounds}) ──"
                )

            trans_new = np.ones(
                (self.img_size, self.img_size), dtype=np.float64
            )
            new_seq = [self.string_sequence[0]]
            pair_usage_new: dict[tuple[int, int], int] = {}
            used_pins_new: set[int] = {self.string_sequence[0]}
            improved = 0
            skipped = 0

            n_total = len(self.string_sequence) - 1
            for i in range(n_total):
                src_pin = new_seq[-1]

                # Score the original destination
                orig_dest = self.string_sequence[i + 1]
                orig_raw = self._line_error_reduction(
                    trans_new, src_pin, orig_dest
                )
                orig_reg = self._regularized_gain(
                    orig_raw, src_pin, orig_dest, pair_usage_new, used_pins_new
                )

                # Score the best alternative from this position (parallel)
                candidates = self.pin_neighbours[src_pin]
                n_w = min(self._num_workers, max(1, len(candidates) // 8))
                if n_w <= 1 or len(candidates) < 16:
                    cand_pin, cand_raw, cand_reg = self._eval_candidates(
                        trans_new,
                        src_pin,
                        candidates,
                        pair_usage_new,
                        used_pins_new,
                    )
                else:
                    chunk_sz = max(1, len(candidates) // n_w)
                    chunks = [candidates[i:i + chunk_sz]
                              for i in range(0, len(candidates), chunk_sz)]
                    futures = [self._thread_pool.submit(
                        self._eval_candidates, trans_new, src_pin,
                        chunk, pair_usage_new, used_pins_new) for chunk in chunks]
                    results = [f.result() for f in futures]
                    cand_pin, cand_raw, cand_reg = max(results, key=lambda x: x[2])

                if cand_reg > orig_reg:
                    best_score = cand_reg
                    best_pin = cand_pin
                else:
                    best_score = orig_reg
                    best_pin = orig_dest

                # Skip string entirely if even the best is unhelpful
                if best_score <= 0:
                    # Still move to the original destination (thread continuity)
                    new_seq.append(orig_dest)
                    skipped += 1
                    continue

                if best_pin != orig_dest:
                    improved += 1

                # Apply the chosen string
                key = (min(src_pin, best_pin), max(src_pin, best_pin))
                self._apply_string(trans_new, src_pin, best_pin)
                pair_usage_new[key] = pair_usage_new.get(key, 0) + 1
                used_pins_new.add(best_pin)
                new_seq.append(best_pin)

            self.string_sequence = new_seq
            transmittance = trans_new

            if verbose:
                ref_mse = self._mse(transmittance)
                print(
                    f"    Swapped {improved} strings, "
                    f"skipped {skipped}, used pins {len(used_pins_new)}, MSE = {ref_mse:.1f}"
                )
                print()

        # ================================================================
        # Phase 3: Sequence compression (explicitly reduce string count)
        # ================================================================
        if self.compression_rounds > 0:
            if verbose:
                print("  ── Phase 3: Sequence Compression ──")
            for c_round in range(self.compression_rounds):
                old_n = len(self.string_sequence) - 1
                self.string_sequence = self._compress_sequence(
                    self.string_sequence, verbose=verbose
                )
                new_n = len(self.string_sequence) - 1

                # Command: replay compressed sequence to rebuild transmittance exactly.
                trans_replay = np.ones(
                    (self.img_size, self.img_size), dtype=np.float64
                )
                for i in range(new_n):
                    pa, pb = self.string_sequence[i], self.string_sequence[i + 1]
                    self._apply_string(trans_replay, pa, pb)
                transmittance = trans_replay

                if verbose:
                    cmp_mse = self._mse(transmittance)
                    print(
                        f"    Round {c_round + 1}/{self.compression_rounds}: "
                        f"strings {old_n} -> {new_n}, MSE = {cmp_mse:.1f}"
                    )
            if verbose:
                print()

        # ================================================================
        # Phase 4: Simulated Annealing (Global MCMC topological swaps)
        # ================================================================
        if self.mcmc_steps > 0:
            self.string_sequence = self._simulated_annealing(
                self.string_sequence, verbose=verbose
            )
            # Rebuild transmittance exactly with chosen best_seq
            trans_final = np.ones(
                (self.img_size, self.img_size), dtype=np.float64
            )
            for i in range(len(self.string_sequence) - 1):
                pa, pb = self.string_sequence[i], self.string_sequence[i + 1]
                self._apply_string(trans_final, pa, pb)
            transmittance = trans_final

        # ================================================================
        # Final result
        # ================================================================
        self.result_image = np.clip(255.0 * transmittance, 0, 255)
        self.transmittance = transmittance

        n_strings = len(self.string_sequence) - 1
        if verbose:
            final_mse = self._mse(transmittance)
            psnr = 10.0 * np.log10(255.0 ** 2 / (final_mse + 1e-10))
            print(f"  ═══════════════════════════════════════")
            print(f"  Final : {n_strings} strings")
            print(f"  MSE   : {final_mse:.1f}")
            print(f"  PSNR  : {psnr:.1f} dB")
            print(f"  ═══════════════════════════════════════")
            print()

        self._thread_pool.shutdown(wait=False)

        return self.string_sequence, self.result_image

    # ---- Visualisation ----------------------------------------------------

    def render_pil(self, line_thickness: int = 1) -> np.ndarray:
        """Re-render the result with PIL (crisp vector-style lines)."""
        img = Image.new("L", (self.img_size, self.img_size), 255)
        draw = ImageDraw.Draw(img)
        for i in range(len(self.string_sequence) - 1):
            pa, pb = self.string_sequence[i], self.string_sequence[i + 1]
            r0, c0 = self.pin_coords[pa]
            r1, c1 = self.pin_coords[pb]
            draw.line([(c0, r0), (c1, r1)], fill=0, width=line_thickness)
        return np.array(img)

    def show_results(self, save_path: str | None = None):
        """Side-by-side comparison: target → algorithm output → PIL render."""
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        axes[0].imshow(self.target, cmap="gray", vmin=0, vmax=255)
        axes[0].set_title("Target image")
        axes[0].axis("off")

        if self.result_image is not None:
            n = len(self.string_sequence) - 1
            mse = self._mse(self.transmittance) if self.transmittance is not None else 0
            axes[1].imshow(self.result_image, cmap="gray", vmin=0, vmax=255)
            axes[1].set_title(f"String art ({n} strings, MSE={mse:.1f})")
            axes[1].axis("off")

        rendered = self.render_pil()
        axes[2].imshow(rendered, cmap="gray", vmin=0, vmax=255)
        axes[2].set_title("PIL vector render")
        axes[2].axis("off")

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"  Figure saved → {save_path}")
        plt.show()

    # ---- Export -----------------------------------------------------------

    def save_sequence(self, filepath: str):
        """Write the pin sequence to a plain-text file."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Computational String Art – Pin Sequence\n")
            f.write(f"# Pins:    {self.num_pins}\n")
            f.write(f"# Strings: {len(self.string_sequence) - 1}\n")
            f.write(f"# Opacity: {self.string_opacity}\n")
            f.write(f"# Format:  one pin index per line (0-indexed)\n\n")
            for pin in self.string_sequence:
                f.write(f"{pin}\n")
        print(f"  Pin sequence saved → {filepath}")

    def save_coordinates(self, filepath: str, frame_diameter_mm: float = 600.0):
        """Write the string sequence as physical (x, y) coordinates in mm.

        The circle is centred at (0, 0) with the given diameter.
        Each line in the file represents one string connection:
            string_number, from_pin, x_from, y_from, to_pin, x_to, y_to

        A header section lists all pin positions first.
        """
        radius_mm = frame_diameter_mm / 2.0
        centre = self.img_size / 2.0
        img_radius = centre - 1

        # Convert pixel pin coords → mm coords (origin at centre)
        pin_mm = []
        for r, c in self.pin_coords:
            x_mm = (c - centre) / img_radius * radius_mm
            y_mm = -(r - centre) / img_radius * radius_mm  # y-up
            pin_mm.append((x_mm, y_mm))

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# String Art – Pin Coordinates (mm)\n")
            f.write(f"# Frame diameter : {frame_diameter_mm:.1f} mm\n")
            f.write(f"# Pins           : {self.num_pins}\n")
            f.write(f"# Strings        : {len(self.string_sequence) - 1}\n")
            f.write(f"# Origin         : centre of circle (0, 0)\n")
            f.write(f"# Y-axis         : positive = up\n")
            f.write(f"#\n")
            f.write(f"# ── PIN POSITIONS ──\n")
            f.write(f"# pin_index, x_mm, y_mm\n")
            for idx, (x, y) in enumerate(pin_mm):
                f.write(f"{idx}, {x:.2f}, {y:.2f}\n")
            f.write(f"\n")
            f.write(f"# ── STRING SEQUENCE (coordinates) ──\n")
            f.write(f"# string_no, from_pin, x_from, y_from, to_pin, x_to, y_to\n")
            for i in range(len(self.string_sequence) - 1):
                pa = self.string_sequence[i]
                pb = self.string_sequence[i + 1]
                x0, y0 = pin_mm[pa]
                x1, y1 = pin_mm[pb]
                f.write(f"{i + 1}, {pa}, {x0:.2f}, {y0:.2f}, {pb}, {x1:.2f}, {y1:.2f}\n")

        print(f"  Coordinates saved → {filepath}")
        print(f"    Frame: {frame_diameter_mm:.0f} mm diameter, {self.num_pins} pins")

    def save_pin_template(self, filepath: str, canvas_px: int = 2000):
        """Generate a high-res pin-coordinate template image for fabrication.

        Draws:
          - A circle showing the frame boundary.
          - Numbered dots at each pin position.
          - Pin index labels (every Nth pin to avoid clutter).

        Parameters
        ----------
        filepath : str
            Output image path (.png recommended).
        canvas_px : int
            Resolution of the output template in pixels.
        """
        scale = canvas_px / self.img_size
        img = Image.new("RGB", (canvas_px, canvas_px), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Draw frame circle
        centre = canvas_px / 2.0
        radius = centre - 2
        bbox = [centre - radius, centre - radius,
                centre + radius, centre + radius]
        draw.ellipse(bbox, outline=(180, 180, 180), width=2)

        # Determine label interval (show every Nth label to avoid overlap)
        label_every = max(1, self.num_pins // 36)

        # Draw pins
        pin_radius = max(4, int(canvas_px / 250))
        for idx, (r, c) in enumerate(self.pin_coords):
            cx = c * scale
            cy = r * scale
            draw.ellipse(
                [cx - pin_radius, cy - pin_radius,
                 cx + pin_radius, cy + pin_radius],
                fill=(220, 50, 50), outline=(0, 0, 0), width=1
            )
            # Label every Nth pin
            if idx % label_every == 0:
                draw.text(
                    (cx + pin_radius + 3, cy - pin_radius - 2),
                    str(idx),
                    fill=(0, 0, 0),
                )

        # Draw string connections lightly (optional visual reference)
        for i in range(len(self.string_sequence) - 1):
            pa, pb = self.string_sequence[i], self.string_sequence[i + 1]
            r0, c0 = self.pin_coords[pa]
            r1, c1 = self.pin_coords[pb]
            draw.line(
                [(c0 * scale, r0 * scale), (c1 * scale, r1 * scale)],
                fill=(0, 0, 0, 30), width=1,
            )

        img.save(filepath, quality=95)
        print(f"  Pin template saved → {filepath}")
        print(f"    Canvas: {canvas_px}×{canvas_px} px")
        print(f"    Pins: {self.num_pins} (labelled every {label_every})")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main():
    # ---- Default parameters (tweak as needed) ----------------------------
    NUM_PINS = 288
    MAX_STRINGS = 10000
    STRING_OPACITY = 0.08
    MIN_PIN_DIST = 20
    IMG_SIZE = 700
    EDGE_WEIGHT = 1.5
    REFINEMENT = 1
    STRING_COST = 3000.0
    NEW_PIN_COST = 2500.0
    PAIR_REUSE_COST = 1200.0
    LOOKAHEAD_WIDTH = 24
    LOOKAHEAD_WEIGHT = 0.35
    COMPRESSION_ROUNDS = 2
    COMPRESSION_TOLERANCE = 1500.0
    MCMC_STEPS = 50000
    MCMC_TEMP_INIT = 5.0
    MCMC_TEMP_END = 0.05
    NUM_WORKERS = os.cpu_count() or 4

    # ---- Resolve image path ----------------------------------------------
    image_path: str | None = None

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    if len(sys.argv) > 2:
        NUM_PINS = int(sys.argv[2])
    if len(sys.argv) > 3:
        MAX_STRINGS = int(sys.argv[3])
    if len(sys.argv) > 4:
        STRING_OPACITY = float(sys.argv[4])
    if len(sys.argv) > 5:
        STRING_COST = float(sys.argv[5])
    if len(sys.argv) > 6:
        NEW_PIN_COST = float(sys.argv[6])
    if len(sys.argv) > 7:
        PAIR_REUSE_COST = float(sys.argv[7])
    if len(sys.argv) > 8:
        LOOKAHEAD_WIDTH = int(sys.argv[8])
    if len(sys.argv) > 9:
        LOOKAHEAD_WEIGHT = float(sys.argv[9])
    if len(sys.argv) > 10:
        COMPRESSION_ROUNDS = int(sys.argv[10])
    if len(sys.argv) > 11:
        COMPRESSION_TOLERANCE = float(sys.argv[11])
    if len(sys.argv) > 12:
        MCMC_STEPS = int(sys.argv[12])
    if len(sys.argv) > 13:
        MCMC_TEMP_INIT = float(sys.argv[13])
    if len(sys.argv) > 14:
        MCMC_TEMP_END = float(sys.argv[14])

    if image_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, "KakaoTalk_20260306_104704271__1_-removebg-preview.png")

    # ---- Banner ----------------------------------------------------------
    print()
    print("=" * 60)
    print("  COMPUTATIONAL STRING ART")
    print("  Energy Minimisation – Birsak et al. 2018")
    print("=" * 60)
    print(f"  Image          : {image_path}")
    print(f"  Pins           : {NUM_PINS}")
    print(f"  Max strings    : {MAX_STRINGS}")
    print(f"  String opacity : {STRING_OPACITY}")
    print(f"  Min pin dist   : {MIN_PIN_DIST}")
    print(f"  Edge importance: {EDGE_WEIGHT}")
    print(f"  Refinement     : {REFINEMENT} round(s)")
    print(f"  String cost    : {STRING_COST}")
    print(f"  New-pin cost   : {NEW_PIN_COST}")
    print(f"  Reuse cost     : {PAIR_REUSE_COST}")
    print(f"  Lookahead      : K={LOOKAHEAD_WIDTH}, w={LOOKAHEAD_WEIGHT}")
    print(f"  Compression    : {COMPRESSION_ROUNDS} round(s), tol={COMPRESSION_TOLERANCE}")
    print(f"  MCMC Opt       : {MCMC_STEPS} steps, T=[{MCMC_TEMP_INIT} -> {MCMC_TEMP_END}]")
    print(f"  Image size     : {IMG_SIZE}×{IMG_SIZE}")
    print(f"  CPU workers    : {NUM_WORKERS}")
    print()

    # ---- Run algorithm ---------------------------------------------------
    sa = StringArt(
        image_path=image_path,
        num_pins=NUM_PINS,
        max_strings=MAX_STRINGS,
        string_opacity=STRING_OPACITY,
        min_pin_distance=MIN_PIN_DIST,
        img_size=IMG_SIZE,
        importance_edge_weight=EDGE_WEIGHT,
        refinement_rounds=REFINEMENT,
        string_cost=STRING_COST,
        new_pin_cost=NEW_PIN_COST,
        pair_reuse_cost=PAIR_REUSE_COST,
        lookahead_width=LOOKAHEAD_WIDTH,
        lookahead_weight=LOOKAHEAD_WEIGHT,
        compression_rounds=COMPRESSION_ROUNDS,
        compression_tolerance=COMPRESSION_TOLERANCE,
        mcmc_steps=MCMC_STEPS,
        mcmc_temp_init=MCMC_TEMP_INIT,
        mcmc_temp_end=MCMC_TEMP_END,
        num_workers=NUM_WORKERS,
    )
    sa.run(verbose=True)

    # ---- Save outputs ----------------------------------------------------
    script_dir = os.path.dirname(os.path.abspath(__file__))
    result_path = os.path.join(script_dir, "string_art_result.png")
    seq_path = os.path.join(script_dir, "pin_sequence.txt")

    sa.show_results(save_path=result_path)
    sa.save_sequence(seq_path)

    coord_path = os.path.join(script_dir, "pin_coordinates.txt")
    sa.save_coordinates(coord_path, frame_diameter_mm=600.0)

    template_path = os.path.join(script_dir, "pin_template.png")
    sa.save_pin_template(template_path, canvas_px=2000)

    print(f"  Result image   : {result_path}")
    print(f"  Pin sequence   : {seq_path}")
    print(f"  Coordinates    : {coord_path}")
    print(f"  Pin template   : {template_path}")


if __name__ == "__main__":
    main()
