"""
Vector arrow and square highlight annotation models and Cairo drawing primitives.
"""

from dataclasses import dataclass
from typing import Tuple
import math
import cairo
import chess


@dataclass(frozen=True)
class ArrowDrawing:
    """Directed vector arrow between two squares."""
    from_square: chess.Square
    to_square: chess.Square
    color: str = "rgba(152, 195, 121, 0.85)"  # Default green


@dataclass(frozen=True)
class SquareHighlight:
    """Colored highlight overlay on a single square."""
    square: chess.Square
    color: str = "rgba(224, 108, 117, 0.65)"  # Default tactical red


def draw_cairo_arrow(
    ctx: cairo.Context,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    r: float,
    g: float,
    b: float,
    a: float,
    shaft_width: float = 12.0,
    head_length: float = 24.0,
    head_width: float = 26.0
):
    """
    Renders an arrow from (start_x, start_y) to (end_x, end_y) using Cairo vector paths.
    """
    dx = end_x - start_x
    dy = end_y - start_y
    dist = math.hypot(dx, dy)
    if dist < 5.0:
        return

    angle = math.atan2(dy, dx)
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)

    # Shorten the end slightly so the arrowhead does not touch piece edges
    target_end_x = start_x + cos_a * (dist - 4.0)
    target_end_y = start_y + sin_a * (dist - 4.0)

    # Base of the arrowhead
    arrow_base_dist = max(0.0, dist - head_length)
    base_x = start_x + cos_a * arrow_base_dist
    base_y = start_y + sin_a * arrow_base_dist

    ctx.save()
    ctx.set_source_rgba(r, g, b, a)

    # 1. Draw shaft
    ctx.set_line_width(shaft_width)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(start_x, start_y)
    ctx.line_to(base_x, base_y)
    ctx.stroke()

    # 2. Draw arrowhead triangle
    perp_sin = math.sin(angle + math.pi / 2.0)
    perp_cos = math.cos(angle + math.pi / 2.0)

    half_head = head_width / 2.0
    p1_x = base_x + perp_cos * half_head
    p1_y = base_y + perp_sin * half_head

    p2_x = base_x - perp_cos * half_head
    p2_y = base_y - perp_sin * half_head

    ctx.move_to(target_end_x, target_end_y)
    ctx.line_to(p1_x, p1_y)
    ctx.line_to(p2_x, p2_y)
    ctx.close_path()
    ctx.fill()

    ctx.restore()
