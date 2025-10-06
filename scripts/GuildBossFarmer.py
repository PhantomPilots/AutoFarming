from utilities.farming_factory import FarmingFactory
from utilities.guild_boss_farming_logic import GuildBossFarmer, States


def main():
    FarmingFactory.main_loop(
        farmer=GuildBossFarmer,
        starting_state=States.FIGHTING,
    )


if __name__ == "__main__":
    main()
