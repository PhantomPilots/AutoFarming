"""The rewards each farmer can read on its result screens: item templates, labels and tile quantities.

Kept free of OpenCV so the GUI can show the reward panels without loading the vision stack.
"""

import os
from dataclasses import dataclass, field

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

# Quantities one tile can hold, from Indura's Bronze/Silver/Gold box drop tables (1 = no number drawn).
# Restricting the read to these values makes a blurry corner digit impossible to misread.
# Items missing here are read freely.
INDURA_TILE_COUNTS = {
    "super_awakening_coin_fragment": (4, 5),
    "chaos_fragment": (2, 4),
    "anvil": (5,),
    "brilliant_component": (1, 2),
    "dark_eraser": (1,),
    "indura_of_retribution": (1,),
}


@dataclass(frozen=True)
class RewardSet:
    """The reward tiles a farmer can read: templates, labels and the quantities a tile can show."""

    title: str  # shown in the GUI rewards panel
    rewards_dir: str  # holds '<key>.png' for every item
    log_subdir: str  # logs/<log_subdir>/ keeps the reward rows and the unreadable result screens
    items: tuple  # (key, display label)
    tile_counts: dict = field(default_factory=dict)
    ignored_items: tuple = ()
    # Share of each template side dropped before matching (rarity frame, corner count, corner badge)
    icon_margin: float = 0.14

    @property
    def labels(self) -> dict:
        return dict(self.items)


INDURA_REWARDS = RewardSet(
    title="Indura Rewards",
    rewards_dir=REWARDS_DIR,
    log_subdir="demon_rewards",
    items=INDURA_ITEMS,
    tile_counts=INDURA_TILE_COUNTS,
    ignored_items=INDURA_IGNORED_ITEMS,
)

# Guild Boss (Belgius) drop table. Templates are cut from the in-game "Reward" list, whose tiles carry a
# badge in the top-right corner and the count in the bottom-right one: a wider margin keeps only the art.
GUILD_BOSS_REWARDS = RewardSet(
    title="Guild Boss Rewards",
    rewards_dir=os.path.join(IMAGES_DIR, "guild_boss", "rewards"),
    log_subdir="guild_boss_rewards",
    items=(
        ("belgius_artifact_card", "Demonic Beast Belgius (Artifact Card)"),
        ("awakening_stone", "Awakening Stone"),
        ("anvil", "Anvil"),
        ("treasure_chest", "Treasure Chest"),
        ("enhance_stone", "Enhance Stone"),
    ),
    tile_counts={
        "belgius_artifact_card": (1,),
        "awakening_stone": (2,),
        "anvil": (10,),
        "treasure_chest": (1,),
        "enhance_stone": (80,),
    },
    icon_margin=0.22,
)
