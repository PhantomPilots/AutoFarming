"""Card strategy for the Supreme Deity Battle (Hell), with the team: Festival Odin, LoliMerlin, Hel, Gawain.

Reference: https://youtu.be/pI9a1lRGgGA (Global client, Hell, clear in ~12 min). The fight has 6 phases:
* P1 to P4: the First to Fourth Judgments (waves of messengers), each one with a 4-turn counter. The video clears the
  first three in 2 turns each (Stigmata of Weakening on the 2nd turn of P3). The Fourth Judgment lasts its 4 turns.
* P5: the Heavenly Punishment Forces of Protection, cleared in 2 turns with the Gawain then Odin ults.
* P6: the final boss (Ludociel in the video, Sariel on other weeks), hit for 4 turns with the Stigmata of Weakening.
  Each 10% of its HP gives an extra chest.

Each turn of the video is a script of 4 slots. When the scripted card isn't in hand, we play a card of the same
hero, then another attack. The ults we keep for a later phase are never played in the fallbacks.
The Odin talent and the Stigmata are handled by the SupremeDeityFighter at the start of each turn.
"""

import time

import cv2
import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardTypes
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import determine_card_merge

CARD_LABEL_THRESHOLD = 0.7
# The cards are searched on the whole width of the hand, then given to the column the bot clicks on (the generic 8
# columns of 57px from x=61). The real cards don't line up with these columns, and their position depends on the size
# of the window: cutting the hand into columns misses the cards on the left
HAND_Y_RANGE = (790, 960)
HAND_COLUMNS_X = 61
HAND_COLUMN_WIDTH = 57
HAND_SIZE = 8
# Two matches closer than this are the same card
SAME_CARD_DISTANCE = 30

# Template name -> hero
CARD_HEROES = {
    "odin_st": "odin",
    "odin_aoe": "odin",
    "odin_ult": "odin",
    "gawain_st": "gawain",
    "gawain_aoe": "gawain",
    "gawain_ult": "gawain",
    "hel_1": "hel",
    "hel_2": "hel",
    "hel_ult": "hel",
    "merlin_st": "merlin",
    "merlin_aoe": "merlin",
    "merlin_ult": "merlin",
}
ALL_ULTS = {"odin_ult", "gawain_ult", "hel_ult", "merlin_ult"}

# The 4 cards of each turn of the video: (phase, turn) -> slots. "move" moves a card (merging it if possible), and
# "move:<hero>" moves a card of this hero
TURN_SCRIPTS = {
    # First Judgment: Odin ST then Odin AoE, then 2 moves of LoliMerlin cards
    (1, 1): ("odin_st", "odin_aoe", "move:merlin", "move:merlin"),
    (1, 2): ("merlin_aoe", "merlin_st", "move", "gawain_st"),
    # Second Judgment
    (2, 1): ("merlin_ult", "gawain_aoe", "hel_2", "odin_aoe"),
    (2, 2): ("odin_aoe", "merlin_st", "gawain_st", "hel_2"),
    # Third Judgment: one skill and 3 moves, then the Stigmata of Weakening
    (3, 1): ("merlin_st", "move", "move", "move"),
    (3, 2): ("odin_aoe", "hel_1", "move", "move"),
    # Fourth Judgment: it lasts its 4 turns, the last one only prepares the hand
    (4, 1): ("move", "gawain_aoe", "gawain_ult", "hel_2"),
    (4, 2): ("gawain_st", "odin_st", "move", "move"),
    (4, 3): ("gawain_aoe", "merlin_st", "odin_st", "move"),
    (4, 4): ("move", "hel_1", "merlin_st", "move"),
    # Heavenly Punishment Forces of Protection
    (5, 1): ("gawain_st", "gawain_st", "odin_st", "gawain_ult"),
    (5, 2): ("odin_ult", "hel_2", "merlin_ult", "move"),
    # Final boss
    (6, 1): ("hel_ult", "odin_st", "merlin_ult", "move"),
    (6, 2): ("odin_st", "gawain_aoe", "merlin_st", "merlin_aoe"),
    (6, 3): ("gawain_aoe", "merlin_ult", "gawain_ult", "gawain_st"),
    (6, 4): ("odin_aoe", "merlin_st", "hel_2", "move"),
}
# Only the skills of this hero on these turns (the other slots are moves). The Divine Edict of the first wave gives a
# bonus when the wave dies on a turn where only one hero attacked
SINGLE_HERO_TURNS = {(1, 1): "odin"}

# When a phase lasts longer than in the video: the attacks by order of damage
ATTACKS = ("odin_st", "gawain_st", "odin_aoe", "gawain_aoe", "merlin_aoe", "merlin_st", "hel_1", "hel_2")
# Ults we keep for a later phase: Odin for the Forces of Protection, Hel for the final boss
RESERVED_ULTS = {
    1: ALL_ULTS,
    2: {"odin_ult", "hel_ult"},
    3: {"odin_ult", "hel_ult"},
    4: {"odin_ult", "hel_ult"},
    5: {"hel_ult"},
    6: set(),
}


class SupremeDeityBattleStrategy(IBattleStrategy):
    """Scripted strategy, phase by phase and turn by turn, falling back to safe choices"""

    # Screenshot taken by the SupremeDeityFighter right before picking a card, to read the cards at their real position
    screenshot: np.ndarray | None = None

    def get_next_card_index(
        self, hand_of_cards: list[Card], picked_cards: list[Card], *, phase: int = 1, card_turn: int = 0, **kwargs
    ) -> int | tuple[int, int] | None:

        turn = max(1, IBattleStrategy.phase_turn)
        labels = self._hand_labels(hand_of_cards)
        print(f"Supreme Deity P{phase} T{turn} slot {card_turn + 1}, hand: {labels}")

        if not any(labels):
            # The hand is hidden (talent or Stigmata animation): read it again a bit later instead of playing blind
            print("Can't read the hand, waiting for it to show up again...")
            time.sleep(1)
            return None

        reserved_ults = RESERVED_ULTS.get(phase, set())
        single_hero = SINGLE_HERO_TURNS.get((phase, turn))

        script = TURN_SCRIPTS.get((phase, turn))
        wish = script[card_turn] if script is not None and card_turn < len(script) else None

        for candidate in self._candidates(wish, reserved_ults, single_hero):
            action = self._resolve(candidate, hand_of_cards, labels)
            if action is not None:
                print(f"Wish '{wish}' -> '{candidate}': {action}")
                return action

        return self._fallback(hand_of_cards, labels, picked_cards[:card_turn], reserved_ults, single_hero)

    @staticmethod
    def _candidates(wish: str | None, reserved_ults: set[str], single_hero: str | None) -> list[str]:
        """The scripted card, then the other cards of the same hero, then the other attacks"""
        if wish is not None and wish.startswith("move"):
            return [wish] if wish == "move" else [wish, "move"]

        candidates = []
        if wish is not None:
            hero = CARD_HEROES[wish]
            candidates.append(wish)
            candidates += [label for label in ATTACKS if CARD_HEROES[label] == hero and label != wish]
        candidates += [label for label in ATTACKS if label not in candidates]

        if single_hero is not None:
            candidates = [label for label in candidates if CARD_HEROES[label] == single_hero]
        # A scripted ult is always allowed, the reserved ones only protect the fallbacks
        return [label for label in candidates if label == wish or label not in reserved_ults] + ["move"]

    def _resolve(self, wish: str, hand_of_cards: list[Card], labels: list[str | None]) -> int | tuple[int, int] | None:
        if wish.startswith("move"):
            hero = wish.partition(":")[2] or None
            return self._move_card(hand_of_cards, labels, hero)
        return self._pick(labels, wish, hand_of_cards)

    @staticmethod
    def _pick(labels: list[str | None], wanted: str, hand_of_cards: list[Card]) -> int | None:
        """Highest ranked (then rightmost) card with the wanted label. The label is enough: the generic card type
        predictor often mistakes the cards of this team for disabled ones"""
        ids = [i for i, label in enumerate(labels) if label == wanted]
        if not ids:
            return None
        return max(ids, key=lambda i: (hand_of_cards[i].card_rank.value, i))

    @staticmethod
    def _move_card(
        hand_of_cards: list[Card], labels: list[str | None], hero: str | None = None
    ) -> tuple[int, int] | None:
        """Move a card, of the given hero if any. Moving onto an identical card merges them, which ranks it up"""

        playable = [
            i
            for i, card in enumerate(hand_of_cards)
            if labels[i] is not None or card.card_type not in (CardTypes.NONE, CardTypes.GROUND)
        ]
        if len(playable) < 2:
            return None

        # Keep the ults in place
        candidates = [i for i in playable if labels[i] not in ALL_ULTS]
        if hero is not None:
            candidates = [i for i in candidates if labels[i] is not None and CARD_HEROES[labels[i]] == hero]
        if not candidates:
            return None

        for origin in candidates:
            for target in playable:
                if (
                    target != origin
                    and labels[origin] is not None
                    and labels[target] == labels[origin]
                    and determine_card_merge(hand_of_cards[origin], hand_of_cards[target])
                ):
                    return (origin, target)

        # No merge: just swap the rightmost card with its closest neighbour
        origin = candidates[-1]
        target = min((i for i in playable if i != origin), key=lambda i: abs(i - origin))
        return (origin, target)

    def _fallback(
        self,
        hand_of_cards: list[Card],
        labels: list[str | None],
        played_cards: list[Card],
        reserved_ults: set[str],
        single_hero: str | None,
    ) -> int | tuple[int, int]:
        """Nothing from the script is available: play something safe"""

        if single_hero is None:
            # Any card we recognize, keeping the reserved ults for later
            for i in range(len(hand_of_cards) - 1, -1, -1):
                if labels[i] is None or labels[i] in reserved_ults:
                    continue
                print(f"Fallback: playing card {i} ({labels[i]})")
                return i

        # Moving a card doesn't use any skill
        if (move := self._move_card(hand_of_cards, labels)) is not None:
            print(f"Fallback: moving {move}")
            return move

        print("Fallback: no safe choice, using the generic strategy.")
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, played_cards)

    @classmethod
    def count_known_cards(cls, screenshot: np.ndarray) -> int:
        """How many cards of the team we recognize in the hand. None during the cutscenes"""
        strategy = cls()
        strategy.screenshot = screenshot
        return sum(label is not None for label in strategy._hand_labels())

    def _hand_labels(self, hand_of_cards: list[Card] | None = None) -> list[str | None]:
        """Template name of each card of the hand, e.g. 'odin_st', or None if it's not recognized"""
        if self.screenshot is None:
            return [self._column_label(card) for card in hand_of_cards or []]

        y0, y1 = HAND_Y_RANGE
        strip = self.screenshot[y0:y1]

        # Every match of every template along the hand: (score, x of its center, label)
        matches = []
        for label in CARD_HEROES:
            needle = getattr(vio, f"sd_{label}").needle_img
            if needle is None or needle.shape[0] > strip.shape[0] or needle.shape[1] > strip.shape[1]:
                continue
            best_per_x = cv2.matchTemplate(strip, needle, cv2.TM_CCOEFF_NORMED).max(axis=0)
            for x in np.flatnonzero(best_per_x >= CARD_LABEL_THRESHOLD):
                around = best_per_x[max(0, x - SAME_CARD_DISTANCE) : x + SAME_CARD_DISTANCE + 1]
                if best_per_x[x] == around.max():
                    matches.append((float(best_per_x[x]), x + needle.shape[1] / 2, label))

        # The best match of each card wins, and goes to the closest column
        labels: list[str | None] = [None] * HAND_SIZE
        taken = []
        for _, x_center, label in sorted(matches, reverse=True):
            if any(abs(x_center - other) < SAME_CARD_DISTANCE for other in taken):
                continue
            column = round((x_center - HAND_COLUMNS_X - HAND_COLUMN_WIDTH / 2) / HAND_COLUMN_WIDTH)
            if 0 <= column < HAND_SIZE and labels[column] is None:
                labels[column] = label
                taken.append(x_center)
        return labels

    @staticmethod
    def _column_label(card: Card) -> str | None:
        """Template name of a card cut from the generic columns, when we don't have the screenshot"""
        if card.card_image is None:
            return None
        best_label, best_score = None, CARD_LABEL_THRESHOLD
        for label in CARD_HEROES:
            needle = getattr(vio, f"sd_{label}").needle_img
            if needle is None or needle.shape[0] > card.card_image.shape[0] or needle.shape[1] > card.card_image.shape[1]:
                continue
            score = float(cv2.matchTemplate(card.card_image, needle, cv2.TM_CCOEFF_NORMED).max())
            if score >= best_score:
                best_label, best_score = label, score
        return best_label
