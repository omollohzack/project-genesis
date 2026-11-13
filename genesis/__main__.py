"""Command-line entry point for the Genesis demo."""

from genesis.core.bootstrap import create_alpha_world


def main() -> None:
    world = create_alpha_world()
    print(f"Project Genesis Alpha — world: {world.name}")
    print(f"Tick: {world.tick}")
    print("Inhabitants:")
    for agent in world.agents.values():
        print(f"  - {agent.name} ({agent.role}) [{agent.agent_id}]")


if __name__ == "__main__":
    main()
