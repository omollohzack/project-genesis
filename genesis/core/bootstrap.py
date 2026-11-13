"""Construct a reproducible in-memory Alpha world."""

from genesis.core.models import World
from genesis.core.seed import ALPHA_INHABITANTS


def create_alpha_world() -> World:
    world = World(world_id="genesis-alpha", name="Genesis Alpha")
    for template in ALPHA_INHABITANTS:
        # Copy mutable fields so separate worlds do not share agent state.
        from copy import deepcopy
        world.agents[template.agent_id] = deepcopy(template)
    return world
