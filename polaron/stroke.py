"""Skeleton strokes -> outline contours.

A stroke is a centre-line path made of lines, cubics and superelliptic
quarter arcs. Every node carries a width factor. The outline is the
Minkowski sum of the path with an elliptical pen (semi-axes A, B; optional
rotation), which gives vertical stems of width 2A and horizontal strokes of
thickness 2B -- that is how stroke contrast is produced.

Quarter arcs are offset analytically: each side becomes another
superelliptic quarter arc between the offset end points, so tight counters at
heavy weights never cusp. Generic cubics are offset by sampling and fitting a
single cubic, so the outline structure only depends on the skeleton, never on
the numbers -- outlines of all masters stay point-compatible.
"""

from __future__ import annotations

import math

from .geom import (
    Contour,
    add,
    cross,
    cubic_deriv,
    cubic_point,
    cubic_tangents,
    dist,
    dot,
    fit_cubic,
    line_intersect,
    mul,
    perp,
    rot,
    smoothstep,
    split_cubic,
    sub,
    unit,
)

KAPPA = 0.5522847498


class Pen:
    """Elliptical nib. sx = full width of a vertical stroke, sy = full
    thickness of a horizontal stroke."""

    __slots__ = ("A", "B", "ang")

    def __init__(self, sx, sy=None, angle=0.0):
        if sy is None:
            sy = sx
        self.A = sx / 2
        self.B = sy / 2
        self.ang = math.radians(angle)

    def support(self, n):
        """Point on the pen boundary furthest in direction n (unit)."""
        A, B = self.A, self.B
        if self.ang:
            n = rot(n, -self.ang)
        den = math.sqrt(A * A * n[0] * n[0] + B * B * n[1] * n[1])
        if den < 1e-12:
            return (0.0, 0.0)
        s = (A * A * n[0] / den, B * B * n[1] / den)
        if self.ang:
            s = rot(s, self.ang)
        return s

    @staticmethod
    def calibrated(sx, sy, angle):
        """Rotated elliptical nib whose vertical-stroke width is still sx and
        horizontal-stroke thickness still sy (humanist stress)."""
        th = math.radians(angle)
        c2, s2 = math.cos(th) ** 2, math.sin(th) ** 2
        X, Y = (sx / 2) ** 2, (sy / 2) ** 2
        den = c2 - s2
        A2 = max((X * c2 - Y * s2) / den, 1e-6)
        B2 = max((Y * c2 - X * s2) / den, Y * 0.2)
        p = Pen(1)
        p.A, p.B, p.ang = math.sqrt(A2), math.sqrt(B2), th
        return p

    def scaled(self, f):
        p = Pen(1)
        p.A, p.B, p.ang = self.A * f, self.B * f, self.ang
        return p


class Path:
    """Centre-line path builder.

    Segment kinds:
      L            straight line
      C c1 c2      cubic Bézier
      vh / hv      superelliptic quarter arc; 'vh' leaves vertically and
                   arrives horizontally, 'hv' the other way round.
    Each node has a width factor w (multiplies the pen).
    """

    def __init__(self, p, w=1.0):
        self.pts = [tuple(p)]
        self.ws = [w]
        self.segs = []
        self.closed = False

    @property
    def cur(self):
        return self.pts[-1]

    def L(self, p, w=1.0):
        self.segs.append(("L",))
        self.pts.append(tuple(p))
        self.ws.append(w)
        return self

    def C(self, c1, c2, p, w=1.0):
        self.segs.append(("C", tuple(c1), tuple(c2)))
        self.pts.append(tuple(p))
        self.ws.append(w)
        return self

    def vh(self, p, w=1.0, k=None):
        self.segs.append(("A", "vh", k))
        self.pts.append(tuple(p))
        self.ws.append(w)
        return self

    def hv(self, p, w=1.0, k=None):
        self.segs.append(("A", "hv", k))
        self.pts.append(tuple(p))
        self.ws.append(w)
        return self

    def close(self):
        """Close the path; the last point must coincide with the first."""
        if dist(self.pts[0], self.pts[-1]) > 0.01:
            self.L(self.pts[0], self.ws[0])
        else:
            self.pts[-1] = self.pts[0]
        self.closed = True
        return self


# ------------------------------------------------------------------ helpers
def _seg_tangents(p0, seg, p1):
    kind = seg[0]
    if kind == "L":
        t = unit(sub(p1, p0))
        return t, t
    if kind == "C":
        return cubic_tangents(p0, seg[1], seg[2], p1)
    mode = seg[1]
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    sx = 1.0 if dx >= 0 else -1.0
    sy = 1.0 if dy >= 0 else -1.0
    if mode == "vh":
        return (0.0, sy), (sx, 0.0)
    return (sx, 0.0), (0.0, sy)


def _arc_controls(s, e, mode, k):
    if mode == "vh":
        corner = (s[0], e[1])
    else:
        corner = (e[0], s[1])
    c1 = (s[0] + (corner[0] - s[0]) * k, s[1] + (corner[1] - s[1]) * k)
    c2 = (e[0] + (corner[0] - e[0]) * k, e[1] + (corner[1] - e[1]) * k)
    return c1, c2


def arc_cubic(s, e, mode, k):
    c1, c2 = _arc_controls(s, e, mode, k)
    return (s, c1, c2, e)


class _Side:
    """One side of an offset stroke: start point + contour-style segments."""

    __slots__ = ("start", "segs")

    def __init__(self, start):
        self.start = start
        self.segs = []

    @property
    def end(self):
        return self.segs[-1][-1] if self.segs else self.start

    def reversed(self):
        nodes = [self.start] + [s[-1] for s in self.segs]
        out = _Side(nodes[-1])
        for i in range(len(self.segs) - 1, -1, -1):
            s = self.segs[i]
            prev = nodes[i]
            if s[0] == "L":
                out.segs.append(("L", prev))
            else:
                out.segs.append(("C", s[2], s[1], prev))
        return out


def _move_end(side, idx, newp):
    """Move the end point of segment idx (and the start of idx+1)."""
    s = side.segs[idx]
    old = s[-1]
    d = sub(newp, old)
    if s[0] == "L":
        side.segs[idx] = ("L", newp)
    else:
        side.segs[idx] = ("C", s[1], add(s[2], d), newp)


def _move_start_of(side, idx, newp):
    if idx == 0:
        old = side.start
        side.start = newp
    else:
        old = side.segs[idx - 1][-1]
        _move_end(side, idx - 1, newp)
    s = side.segs[idx]
    if s[0] == "C":
        d = sub(newp, old)
        side.segs[idx] = ("C", add(s[1], d), s[2], s[3])


# ------------------------------------------------------------------ stroker
class Stroker:
    def __init__(self, pen: Pen, kin=0.0, samples=12):
        self.pen = pen
        self.kin = kin  # extra superness on the inner side of arcs
        self.samples = samples

    def off(self, c, t, w, sign):
        s = self.pen.support(perp(t))
        return (c[0] + sign * s[0] * w, c[1] + sign * s[1] * w)

    def _offset_segment(self, p0, seg, p1, w0, w1, sign, default_k):
        """Returns (start_point, [segment]) for one side."""
        ts, te = _seg_tangents(p0, seg, p1)
        kind = seg[0]
        if kind == "L":
            a = self.off(p0, ts, w0, sign)
            b = self.off(p1, te, w1, sign)
            return a, [("L", b)]
        if kind == "A":
            mode, k = seg[1], seg[2]
            if k is None:
                k = default_k
            turn = cross(ts, te)
            inner = (turn > 0) == (sign > 0)
            if inner:
                k = min(0.95, k + self.kin)
            a = self.off(p0, ts, w0, sign)
            b = self.off(p1, te, w1, sign)
            c1, c2 = _arc_controls(a, b, mode, k)
            return a, [("C", c1, c2, b)]
        # generic cubic: sample and fit
        c1, c2 = seg[1], seg[2]
        n = self.samples
        pts = []
        for i in range(n + 1):
            t = i / n
            c = cubic_point(p0, c1, c2, p1, t)
            d = cubic_deriv(p0, c1, c2, p1, t)
            if math.hypot(*d) < 1e-6:
                t2 = min(1.0, max(0.0, t + (1e-3 if t < 0.5 else -1e-3)))
                c2p = cubic_point(p0, c1, c2, p1, t2)
                d = sub(c2p, c) if t2 > t else sub(c, c2p)
            tt = unit(d)
            w = w0 + (w1 - w0) * smoothstep(t)
            pts.append(self.off(c, tt, w, sign))
        a, cc1, cc2, b = fit_cubic(pts, ts, te)
        return a, [("C", cc1, cc2, b)]

    def sides(self, path: Path, k):
        left = None
        right = None
        tans = []
        n = len(path.segs)
        for i, seg in enumerate(path.segs):
            p0, p1 = path.pts[i], path.pts[i + 1]
            w0, w1 = path.ws[i], path.ws[i + 1]
            tans.append(_seg_tangents(p0, seg, p1))
            for sign in (1, -1):
                a, segs = self._offset_segment(p0, seg, p1, w0, w1, sign, k)
                side = left if sign > 0 else right
                if side is None:
                    side = _Side(a)
                    if sign > 0:
                        left = side
                    else:
                        right = side
                else:
                    prev_end = side.end
                    if dist(prev_end, a) > 0.5:
                        # corner: miter by intersecting the end tangents
                        t_prev = tans[i - 1][1]
                        t_next = tans[i][0]
                        x = line_intersect(prev_end, t_prev, a, t_next)
                        if x is None or dist(x, prev_end) > 4 * (self.pen.A + self.pen.B):
                            x = ((prev_end[0] + a[0]) / 2, (prev_end[1] + a[1]) / 2)
                        _move_end(side, len(side.segs) - 1, x)
                        if segs[0][0] == "C":
                            d = sub(x, a)
                            segs = [("C", add(segs[0][1], d), segs[0][2], segs[0][3])]
                side.segs.extend(segs)
        return left, right, tans

    # -------------------------------------------------------------- caps
    def _cut_end(self, side, C, t, angle):
        """Trim/extend the end of a side chain to the cut line through C."""
        d = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
        m = perp(d)
        if dot(m, t) < 0:
            m = (-m[0], -m[1])

        def f(X):
            return dot(m, sub(X, C))

        last = side.segs[-1]
        P = side.segs[-2][-1] if len(side.segs) > 1 else side.start
        E = last[-1]
        fE = f(E)
        if last[0] == "L":
            fP = f(P)
            if abs(fP - fE) < 1e-9:
                return
            s = fP / (fP - fE)
            side.segs[-1] = ("L", (P[0] + (E[0] - P[0]) * s, P[1] + (E[1] - P[1]) * s))
            return
        c1, c2 = last[1], last[2]
        if fE < 0:
            te = unit(sub(E, c2)) if dist(E, c2) > 1e-6 else t
            den = dot(m, te)
            if abs(den) < 1e-6:
                te, den = t, dot(m, t)
            X = add(E, mul(te, -fE / den))
            side.segs.append(("L", X))
            return
        # overshoot: bisection for the crossing
        lo, hi = 0.0, 1.0
        if f(P) >= 0:
            lo = 0.0
            hi = 0.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if f(cubic_point(P, c1, c2, E, mid)) < 0:
                lo = mid
            else:
                hi = mid
        tx = (lo + hi) / 2
        X = cubic_point(P, c1, c2, E, tx)
        t1 = tx * 0.96
        left_part, _ = split_cubic(P, c1, c2, E, max(t1, 1e-3))
        side.segs[-1] = ("C", left_part[1], left_part[2], left_part[3])
        side.segs.append(("L", X))

    def _cap(self, kind, C, t, w, from_pt, to_pt, at_end):
        """Segments from from_pt to to_pt around node C (tangent t
        points out of the stroke at this end)."""
        if kind == "round":
            u = self.pen.support(t)
            u = (u[0] * w, u[1] * w)
            # from_pt -> tip (C+u) -> to_pt, as two affine quarter circles
            P0 = from_pt
            T = add(C, u)
            P2 = to_pt
            sa = sub(P0, C)
            sb = sub(P2, C)
            return [
                ("C", add(P0, mul(u, KAPPA)), add(T, mul(sa, KAPPA)), T),
                ("C", add(T, mul(sb, KAPPA)), add(P2, mul(u, KAPPA)), P2),
            ]
        return [("L", to_pt)]

    def stroke(self, path: Path, k=0.66, start="butt", end="butt"):
        left, right, tans = self.sides(path, k)
        if path.closed:
            # join the closing node
            for side in (left, right):
                if dist(side.end, side.start) > 0.5:
                    t_prev = tans[-1][1]
                    t_next = tans[0][0]
                    x = line_intersect(side.end, t_prev, side.start, t_next)
                    if x is None:
                        x = ((side.end[0] + side.start[0]) / 2, (side.end[1] + side.start[1]) / 2)
                    _move_end(side, len(side.segs) - 1, x)
                    _move_start_of(side, 0, x)
                else:
                    _move_end(side, len(side.segs) - 1, side.start)
            a = Contour(left.start, left.segs)
            b = Contour(right.start, right.segs)
            if abs(a.area()) >= abs(b.area()):
                return [a.clockwise(), b.counterclockwise()]
            return [b.clockwise(), a.counterclockwise()]

        t_end = tans[-1][1]
        t_start = tans[0][0]
        C_end = path.pts[-1]
        C_start = path.pts[0]
        # cut caps adjust the side chains first
        if isinstance(end, (int, float)) and not isinstance(end, bool):
            self._cut_end(left, C_end, t_end, end)
            self._cut_end(right, C_end, t_end, end)
            end = "butt"
        if isinstance(start, (int, float)) and not isinstance(start, bool):
            lr = left.reversed()
            rr = right.reversed()
            back = (-t_start[0], -t_start[1])
            self._cut_end(lr, C_start, back, start)
            self._cut_end(rr, C_start, back, start)
            left = lr.reversed()
            right = rr.reversed()
            start = "butt"
        segs = list(left.segs)
        segs += self._cap(end, C_end, t_end, path.ws[-1], left.end, right.end, True)
        rr = right.reversed()
        segs += rr.segs
        back = (-t_start[0], -t_start[1])
        segs += self._cap(start, C_start, back, path.ws[0], right.start, left.start, False)
        c = Contour(left.start, segs)
        return [c.clockwise()]
