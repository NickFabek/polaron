"""Small 2D geometry kit: vectors, cubic Béziers, closed contours.

Points are plain (x, y) float tuples for speed. Contours are closed and made
of line ('L') and cubic ('C') segments; the last segment always ends at the
contour's start point.
"""

from __future__ import annotations

import math

EPS = 1e-9


# ---------------------------------------------------------------- vectors
def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def mul(a, s):
    return (a[0] * s, a[1] * s)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def length(a):
    return math.hypot(a[0], a[1])


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def unit(a):
    d = math.hypot(a[0], a[1])
    if d < EPS:
        return (0.0, 0.0)
    return (a[0] / d, a[1] / d)


def perp(a):
    """Left normal (rotate +90°)."""
    return (-a[1], a[0])


def rot(a, ang):
    c, s = math.cos(ang), math.sin(ang)
    return (a[0] * c - a[1] * s, a[0] * s + a[1] * c)


def line_intersect(p, d, q, e):
    """Intersection of p + s*d and q + u*e (None if parallel)."""
    den = cross(d, e)
    if abs(den) < EPS:
        return None
    s = cross(sub(q, p), e) / den
    return (p[0] + d[0] * s, p[1] + d[1] * s)


def smoothstep(t):
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- cubics
def cubic_point(p0, p1, p2, p3, t):
    mt = 1 - t
    a = mt * mt * mt
    b = 3 * mt * mt * t
    c = 3 * mt * t * t
    d = t * t * t
    return (
        a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
        a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
    )


def cubic_deriv(p0, p1, p2, p3, t):
    mt = 1 - t
    a = 3 * mt * mt
    b = 6 * mt * t
    c = 3 * t * t
    return (
        a * (p1[0] - p0[0]) + b * (p2[0] - p1[0]) + c * (p3[0] - p2[0]),
        a * (p1[1] - p0[1]) + b * (p2[1] - p1[1]) + c * (p3[1] - p2[1]),
    )


def cubic_deriv2(p0, p1, p2, p3, t):
    mt = 1 - t
    return (
        6 * mt * (p2[0] - 2 * p1[0] + p0[0]) + 6 * t * (p3[0] - 2 * p2[0] + p1[0]),
        6 * mt * (p2[1] - 2 * p1[1] + p0[1]) + 6 * t * (p3[1] - 2 * p2[1] + p1[1]),
    )


def split_cubic(p0, p1, p2, p3, t):
    a = lerp(p0, p1, t)
    b = lerp(p1, p2, t)
    c = lerp(p2, p3, t)
    d = lerp(a, b, t)
    e = lerp(b, c, t)
    f = lerp(d, e, t)
    return (p0, a, d, f), (f, e, c, p3)


def cubic_tangents(p0, p1, p2, p3):
    """Unit tangents at start and end, robust to coincident handles."""
    if dist(p0, p1) > 1e-6:
        ts = unit(sub(p1, p0))
    elif dist(p0, p2) > 1e-6:
        ts = unit(sub(p2, p0))
    else:
        ts = unit(sub(p3, p0))
    if dist(p2, p3) > 1e-6:
        te = unit(sub(p3, p2))
    elif dist(p1, p3) > 1e-6:
        te = unit(sub(p3, p1))
    else:
        te = unit(sub(p3, p0))
    return ts, te


def fit_cubic(pts, t0, t1, iters=3):
    """Fit one cubic through pts[0]..pts[-1] with fixed end tangent
    directions t0 (leaving pts[0]) and t1 (arriving at pts[-1]).
    Returns (p0, c1, c2, p3)."""
    P0, P3 = pts[0], pts[-1]
    n = len(pts)
    # chord-length parametrisation
    us = [0.0]
    for i in range(1, n):
        us.append(us[-1] + dist(pts[i - 1], pts[i]))
    total = us[-1] or 1.0
    us = [u / total for u in us]
    chord = dist(P0, P3)
    a = b = chord / 3
    for it in range(iters + 1):
        C11 = C12 = C22 = X1 = X2 = 0.0
        for u, Q in zip(us, pts):
            mt = 1 - u
            b0 = mt * mt * mt
            b1 = 3 * mt * mt * u
            b2 = 3 * mt * u * u
            b3 = u * u * u
            A1 = (t0[0] * b1, t0[1] * b1)
            A2 = (-t1[0] * b2, -t1[1] * b2)
            base = (
                P0[0] * (b0 + b1) + P3[0] * (b2 + b3),
                P0[1] * (b0 + b1) + P3[1] * (b2 + b3),
            )
            r = (Q[0] - base[0], Q[1] - base[1])
            C11 += dot(A1, A1)
            C12 += dot(A1, A2)
            C22 += dot(A2, A2)
            X1 += dot(A1, r)
            X2 += dot(A2, r)
        det = C11 * C22 - C12 * C12
        if abs(det) > 1e-12:
            a = (X1 * C22 - X2 * C12) / det
            b = (C11 * X2 - C12 * X1) / det
        if a < chord * 0.02 or b < chord * 0.02 or a > chord * 2 or b > chord * 2:
            a = b = chord / 3
        c1 = (P0[0] + t0[0] * a, P0[1] + t0[1] * a)
        c2 = (P3[0] - t1[0] * b, P3[1] - t1[1] * b)
        if it == iters:
            return (P0, c1, c2, P3)
        # Newton reparametrisation
        nu = []
        for u, Q in zip(us, pts):
            B = cubic_point(P0, c1, c2, P3, u)
            d1 = cubic_deriv(P0, c1, c2, P3, u)
            d2 = cubic_deriv2(P0, c1, c2, P3, u)
            diff = sub(B, Q)
            num = dot(diff, d1)
            den = dot(d1, d1) + dot(diff, d2)
            if abs(den) > 1e-12:
                u = u - num / den
            nu.append(min(1.0, max(0.0, u)))
        nu[0], nu[-1] = 0.0, 1.0
        us = nu
    return (P0, c1, c2, P3)


# ---------------------------------------------------------------- contours
class Contour:
    """Closed contour. segs: list of ('L', p) or ('C', c1, c2, p).
    The final segment ends at `start`."""

    __slots__ = ("start", "segs")

    def __init__(self, start, segs):
        self.start = start
        self.segs = segs

    # -- construction helpers
    @staticmethod
    def polygon(points):
        pts = list(points)
        segs = [("L", p) for p in pts[1:]] + [("L", pts[0])]
        return Contour(pts[0], segs)

    def copy(self):
        return Contour(self.start, list(self.segs))

    def points(self):
        """All points in order (start + every segment point)."""
        out = [self.start]
        for s in self.segs:
            out.extend(s[1:])
        return out

    def map(self, f):
        segs = []
        for s in self.segs:
            if s[0] == "L":
                segs.append(("L", f(s[1])))
            else:
                segs.append(("C", f(s[1]), f(s[2]), f(s[3])))
        return Contour(f(self.start), segs)

    def translate(self, dx, dy):
        return self.map(lambda p: (p[0] + dx, p[1] + dy))

    def reversed(self):
        # node list P0..Pn with Pn == P0
        nodes = [self.start] + [s[-1] for s in self.segs]
        segs = []
        for i in range(len(self.segs) - 1, -1, -1):
            s = self.segs[i]
            prev = nodes[i]
            if s[0] == "L":
                segs.append(("L", prev))
            else:
                segs.append(("C", s[2], s[1], prev))
        return Contour(nodes[-1], segs)

    def flatten(self, steps=8):
        out = [self.start]
        cur = self.start
        for s in self.segs:
            if s[0] == "L":
                out.append(s[1])
            else:
                for i in range(1, steps + 1):
                    out.append(cubic_point(cur, s[1], s[2], s[3], i / steps))
            cur = s[-1]
        return out

    def area(self):
        pts = self.flatten(8)
        a = 0.0
        for i in range(len(pts) - 1):
            a += pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
        return a / 2

    def bounds(self):
        pts = self.flatten(8)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def clockwise(self):
        """Return a clockwise (TrueType outer) version."""
        return self.reversed() if self.area() > 0 else self

    def counterclockwise(self):
        return self if self.area() > 0 else self.reversed()


def bounds_of(contours):
    if not contours:
        return (0, 0, 0, 0)
    bs = [c.bounds() for c in contours]
    return (
        min(b[0] for b in bs),
        min(b[1] for b in bs),
        max(b[2] for b in bs),
        max(b[3] for b in bs),
    )


def affine(a, b, c, d, e, f):
    """Point map for matrix [a b c d] + translation (e f): x' = a x + c y + e."""
    return lambda p: (a * p[0] + c * p[1] + e, b * p[0] + d * p[1] + f)
