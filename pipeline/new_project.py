"""Create a project folder (and its working memory) for /plan, /edit or /carousel.

  python -m pipeline.new_project <pillar> <slug> [--task plan|edit|carousel] [--date YYYY-MM-DD]
Prints the project id.
"""
from __future__ import annotations

import argparse

from pipeline import memory
from pipeline.common import PILLARS, Project


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pillar", choices=PILLARS)
    ap.add_argument("slug")
    ap.add_argument("--task", default="plan", choices=["plan", "edit", "carousel"])
    ap.add_argument("--date")
    ap.add_argument("--goal", default="")
    a = ap.parse_args(argv)
    proj = Project.create(a.pillar, a.slug, a.date)
    memory.create_working(proj.id, a.pillar, a.task, goal=a.goal)
    memory.memory_load(a.pillar, proj.id)
    print(proj.id)


if __name__ == "__main__":
    main()
