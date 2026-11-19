"""The rewards each farmer can read on its result screens: item templates and labels.

Kept free of OpenCV so the GUI can show the reward panels without loading the vision stack.
"""

import os
from dataclasses import dataclass

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")
REWARDS_DIR = os.path.join(IMAGES_DIR, "demons", "rewards")

# (key, display label). The key is also the template filename in images/demons/rewards/.
INDURA_ITEMS = (
    ("super_awakening_coin_fragment", "Super Awakening Coin Fragment"),
    ("chaos_fragment", "Chaos Fragment"),
    ("anvil", "Anvil"),
    ("brilliant_component", "Brilliant Component"),
    ("dark_eraser", '"Dark Eraser"'),
    ("indura_of_retribution", "Indura of Retribution"),
    ("death_match_reward", "Death Match Reward"),
    ("scroll", "Scroll"),
    ("potion", "Potion"),
)

# Tiles that are recognized (so they can't be mistaken for another item) but never reported.
INDURA_IGNORED_ITEMS = ("bingo_ticket",)


@dataclass(frozen=True)
class RewardSet:
    """The reward tiles a farmer can read: templates and display labels."""

    title: str  # shown in the GUI rewards panel
    rewards_dir: str  # holds '<key>.png' for every item
    items: tuple  # (key, display label)
    ignored_items: tuple = ()
    # Share of each template side dropped before matching (rarity frame, corner count, corner badge)
    icon_margin: float = 0.14

    @property
    def labels(self) -> dict:
        return dict(self.items)


INDURA_REWARDS = RewardSet(
    title="Indura Rewards",
    rewards_dir=REWARDS_DIR,
    items=INDURA_ITEMS,
    ignored_items=INDURA_IGNORED_ITEMS,
)

# Guild Boss (Belgius) drop table. Templates are cut from the in-game "Reward" list, whose tiles carry a
# badge in the top-right corner and the count in the bottom-right one: a wider margin keeps only the art.
GUILD_BOSS_REWARDS = RewardSet(
    title="Guild Boss Rewards",
    rewards_dir=os.path.join(IMAGES_DIR, "guild_boss", "rewards"),
    items=(
        ("belgius_artifact_card", "Demonic Beast Belgius (Artifact Card)"),
        ("awakening_stone", "Awakening Stone"),
        ("anvil", "Anvil"),
        ("treasure_chest", "Treasure Chest"),
        ("enhance_stone", "Enhance Stone"),
    ),
    icon_margin=0.22,
)

# Add sets/item PNGs here. On is_victory_result(screenshot), call read_and_report once per result before navigating.
REWARD_SETS: dict[str, RewardSet] = {
    "indura_farmer": INDURA_REWARDS,
    "GuildBossFarmer.py": GUILD_BOSS_REWARDS,
}
