from genesis.core.bootstrap import create_alpha_world
from genesis.core.world import WorldError, advance_tick, record_agent_event


def test_alpha_world_has_five_inhabitants():
    world = create_alpha_world()
    assert set(world.agents) == {"ari", "bela", "cato", "dara", "eli"}


def test_tick_advances_once_and_records_event():
    world = create_alpha_world()
    event = advance_tick(world)
    assert world.tick == 1
    assert event.tick == 1
    assert world.events[-1] == event


def test_rejects_multi_tick_jump():
    world = create_alpha_world()
    try:
        advance_tick(world, 2)
    except WorldError:
        pass
    else:
        raise AssertionError("Expected WorldError")


def test_rejects_unknown_agent_event():
    world = create_alpha_world()
    try:
        record_agent_event(world, "unknown", "test.event")
    except WorldError:
        pass
    else:
        raise AssertionError("Expected WorldError")
