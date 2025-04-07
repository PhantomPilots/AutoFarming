import abc
from copy import deepcopy
from numbers import Integral

import numpy as np
import utilities.vision_images as vio
from termcolor import cprint
from utilities.battle_utilities import process_card_move, process_card_play
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.fighting_strategies import IBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    count_immortality_buffs,
    determine_card_merge,
    display_image,
    find,
    get_hand_cards,
)

class DogsBattleStrategy(IBattleStrategy):
    """The logic behind the AI for Dogs based on custom strategy"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], floor: int, phase: int) -> int:
        """Extract the next card index based on floor and phase"""
        if floor == 1:
            if phase == 1:
                return self._floor_1_phase_1(hand_of_cards, picked_cards)
            elif phase == 2:
                return self._floor_1_phase_2(hand_of_cards, picked_cards)
            elif phase == 3:
                return self._floor_1_phase_3(hand_of_cards, picked_cards)
        elif floor == 2:
            if phase == 1:
                return self._floor_2_phase_1(hand_of_cards, picked_cards)
            elif phase == 2:
                return self._floor_2_phase_2(hand_of_cards, picked_cards)
            elif phase == 3:
                return self._floor_2_phase_3(hand_of_cards, picked_cards)
        elif floor == 3:
            if phase == 1:
                return self._floor_3_phase_1(hand_of_cards, picked_cards)
            elif phase == 2:
                return self._floor_3_phase_2(hand_of_cards, picked_cards)
            elif phase == 3:
                return self._floor_3_phase_3(hand_of_cards, picked_cards)
        
        print(f"No strategy defined for Floor {floor}, Phase {phase}, returning -1")
        return -1

    def _floor_1_phase_1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Floor 1, Phase 1: lolimerl_st > thor_1 > thor_2 > ghel_aoe2"""
        card_turn = IBattleStrategy.card_turn
        print(f"Floor 1, Phase 1: Card turn {card_turn}")
        
        if card_turn == 0:
            idx = self._find_card(hand_of_cards, vio.lolimerl_st)
            if idx != -1:
                print(f"Floor 1, Phase 1: Using lolimerl_st at index {idx}")
                return idx
        elif card_turn == 1:
            idx = self._find_card(hand_of_cards, vio.thor_1)
            if idx != -1:
                print(f"Floor 1, Phase 1: Using thor_1 at index {idx}")
                return idx
        elif card_turn == 2:
            idx = self._find_card(hand_of_cards, vio.thor_2)
            if idx != -1:
                print(f"Floor 1, Phase 1: Using thor_2 at index {idx}")
                return idx
        elif card_turn == 3:
            idx = self._find_card(hand_of_cards, vio.ghel_aoe2)
            if idx != -1:
                print(f"Floor 1, Phase 1: Using ghel_aoe2 at index {idx}")
                return idx
        
        print("Floor 1, Phase 1: No preferred card found, returning -1")
        return -1

    def _floor_1_phase_2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Floor 1, Phase 2: milim_st > 3 other random cards, but NEVER use milim_aoe"""
        card_turn = IBattleStrategy.card_turn
        print(f"Floor 1, Phase 2: Card turn {card_turn}")
        
        # Get all non-disabled, non-milim_aoe cards
        available_ids = [i for i, card in enumerate(hand_of_cards) 
                        if card.card_type != CardTypes.DISABLED and 
                        not find(vio.milim_aoe, card.card_image)]
        
        print(f"Floor 1, Phase 2: Available non-milim_aoe cards: {len(available_ids)}")
        
        if card_turn == 0:
            # For first card, try to use milim_st if available
            milim_st_idx = self._find_card(hand_of_cards, vio.milim_st)
            if milim_st_idx != -1:
                print(f"Floor 1, Phase 2: Using milim_st at index {milim_st_idx}")
                return milim_st_idx
            
            # If milim_st not available, use any non-milim_aoe card
            if available_ids:
                idx = available_ids[0]
                print(f"Floor 1, Phase 2: No milim_st found, using alternative at index {idx}")
                return idx
            
            print("Floor 1, Phase 2: No suitable card found, returning -1")
            return -1
            
        elif card_turn in [1, 2, 3]:
            # For subsequent cards, use any non-milim_aoe card
            if available_ids:
                idx = available_ids[0]
                print(f"Floor 1, Phase 2: Using non-milim_aoe card at index {idx}")
                return idx
            
            print("Floor 1, Phase 2: No suitable card found, returning -1")
            return -1
        
        print("Floor 1, Phase 2: Card turn exceeded, returning -1")
        return -1

    def _floor_1_phase_3(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Floor 1, Phase 3: any *_ult > milim_aoe > any *_aoe > 2 other random cards"""
        card_turn = IBattleStrategy.card_turn
        print(f"Floor 1, Phase 3: Card turn {card_turn}")
        
        # Check for any *_ult first
        ult_count = sum(1 for card in hand_of_cards if card.card_type == CardTypes.ULTIMATE and card.card_type != CardTypes.DISABLED)
        picked_ults = sum(1 for card in picked_cards if card.card_type == CardTypes.ULTIMATE)
        if picked_ults < ult_count:
            for i, card in enumerate(hand_of_cards):
                if card.card_type == CardTypes.ULTIMATE and card.card_type != CardTypes.DISABLED:
                    print(f"Floor 1, Phase 3: Using ultimate card #{picked_ults + 1} at index {i}")
                    return i
        
        # Then proceed with original logic
        if card_turn - picked_ults == 0:
            idx = self._find_card(hand_of_cards, vio.milim_aoe)
            if idx != -1:
                print(f"Floor 1, Phase 3: Using milim_aoe at index {idx}")
                return idx
            print("Floor 1, Phase 3: milim_aoe not found, trying AOE")
        elif card_turn - picked_ults == 1:
            idx = self._find_aoe_card(hand_of_cards)
            if idx != -1:
                print(f"Floor 1, Phase 3: Using AOE card at index {idx}")
                return idx
            print("Floor 1, Phase 3: No AOE card found, trying random")
        elif card_turn - picked_ults in [2, 3]:
            available_ids = [i for i, card in enumerate(hand_of_cards) if card.card_type != CardTypes.DISABLED]
            if available_ids:
                idx = available_ids[0]
                print(f"Floor 1, Phase 3: Using random card at index {idx}")
                return idx
            print("Floor 1, Phase 3: No random card found")
        
        print("Floor 1, Phase 3: No suitable card found, returning -1")
        return -1

    def _floor_2_phase_1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Floor 2, Phase 1: Same as Floor 1, Phase 1"""
        return self._floor_1_phase_1(hand_of_cards, picked_cards)

    def _floor_2_phase_2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Floor 2, Phase 2: Any *_st or lolimerl_* card, avoid ghel_* and milim_aoe/ult"""
        card_turn = IBattleStrategy.card_turn
        print(f"Floor 2, Phase 2: Card turn {card_turn}")
        
        # Check for freeze_icon
        is_frozen = any(find(vio.freeze_icon, card.card_image) for card in hand_of_cards)
        print(f"Floor 2, Phase 2: Freeze detected: {is_frozen}")
        
        # Get all cards excluding milim_aoe, ghel_* and disabled cards
        available_ids = [i for i, card in enumerate(hand_of_cards) 
                         if card.card_type != CardTypes.DISABLED and
                         not find(vio.milim_aoe, card.card_image) and
                         not find(vio.ghel_aoe1, card.card_image) and 
                         not find(vio.ghel_aoe2, card.card_image) and 
                         not find(vio.ghel_ult, card.card_image) and 
                         not find(vio.milim_ult, card.card_image)]
        
        # Prioritize ST or Lolimerl cards
        st_or_loli_ids = [i for i in available_ids if self._is_st_or_lolimerl_card(hand_of_cards[i])]
        
        if card_turn in [0, 1, 2, 3]:
            if st_or_loli_ids:
                idx = st_or_loli_ids[0]
                print(f"Floor 2, Phase 2: Using ST or Lolimerl card at index {idx}")
                return idx
            elif available_ids:
                idx = available_ids[0]
                print(f"Floor 2, Phase 2: Using available card at index {idx}")
                return idx
        
        print("Floor 2, Phase 2: No suitable card found, returning -1")
        return -1

    def _floor_2_phase_3(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Floor 2, Phase 3: any *_ult > milim_aoe > lolimerl_aoe > thor_* with freeze handling"""
        card_turn = IBattleStrategy.card_turn
        print(f"Floor 2, Phase 3: Card turn {card_turn}")
        
        # Check for freeze_icon
        is_frozen = any(find(vio.freeze_icon, card.card_image) for card in hand_of_cards)
        print(f"Floor 2, Phase 3: Freeze detected: {is_frozen}")
        
        # Check for any *_ult first
        ult_count = sum(1 for card in hand_of_cards if card.card_type == CardTypes.ULTIMATE and card.card_type != CardTypes.DISABLED)
        picked_ults = sum(1 for card in picked_cards if card.card_type == CardTypes.ULTIMATE)
        if picked_ults < ult_count:
            for i, card in enumerate(hand_of_cards):
                if card.card_type == CardTypes.ULTIMATE and card.card_type != CardTypes.DISABLED:
                    print(f"Floor 2, Phase 3: Using ultimate card #{picked_ults + 1} at index {i}")
                    return i
        
        # Identify who's frozen based on unv_ cards
        has_unv_milim = any(find(vio.unv_milim_aoe, card.card_image) or find(vio.unv_milim_st, card.card_image) 
                            for card in hand_of_cards)
        has_unv_ghel = any(find(vio.unv_ghel_aoe1, card.card_image) or find(vio.unv_ghel_aoe2, card.card_image) or 
                           find(vio.unv_ghel_ult, card.card_image) for card in hand_of_cards)
        has_unv_thor = any(find(vio.unv_thor_1, card.card_image) or find(vio.unv_thor_2, card.card_image) or 
                           find(vio.unv_thor_ult, card.card_image) for card in hand_of_cards)
        
        print(f"Floor 2, Phase 3: Milim frozen: {has_unv_milim}, Ghel frozen: {has_unv_ghel}, Thor frozen: {has_unv_thor}")
        
        if is_frozen and (has_unv_milim or has_unv_ghel or has_unv_thor):
            # Try Ghel's AOE pair first
            if card_turn - picked_ults == 0:
                idx = self._find_card(hand_of_cards, vio.ghel_aoe1)
                if idx != -1 and self._find_card(hand_of_cards, vio.ghel_aoe2) != -1:  # Ensure both are available
                    print(f"Floor 2, Phase 3: Using ghel_aoe1 at index {idx} to start unfreezing")
                    return idx
                print("Floor 2, Phase 3: ghel_aoe1 not found or no ghel_aoe2, trying Lolimerl")
            elif card_turn - picked_ults == 1 and any(find(vio.ghel_aoe1, card.card_image) for card in picked_cards):
                idx = self._find_card(hand_of_cards, vio.ghel_aoe2)
                if idx != -1:
                    print(f"Floor 2, Phase 3: Using ghel_aoe2 at index {idx} to finish unfreezing")
                    return idx
                print("Floor 2, Phase 3: ghel_aoe2 not found after ghel_aoe1")
            
            # Try Lolimerl's AOE pair if Ghel's not fully available
            elif card_turn - picked_ults == 0:
                idx = self._find_card(hand_of_cards, vio.lolimerl_aoe)
                if idx != -1 and self._count_cards(hand_of_cards, lambda c: find(vio.lolimerl_aoe, c.card_image)) >= 2:
                    print(f"Floor 2, Phase 3: Using lolimerl_aoe at index {idx} to start unfreezing")
                    return idx
                print("Floor 2, Phase 3: Not enough lolimerl_aoe cards")
            elif card_turn - picked_ults == 1 and any(find(vio.lolimerl_aoe, card.card_image) for card in picked_cards):
                idx = self._find_card(hand_of_cards, vio.lolimerl_aoe)
                if idx != -1:
                    print(f"Floor 2, Phase 3: Using lolimerl_aoe at index {idx} to finish unfreezing")
                    return idx
                print("Floor 2, Phase 3: No second lolimerl_aoe found")

            # After unfreezing (turn 2+), use Milim or default
            elif card_turn - picked_ults >= 2:
                idx = self._find_card(hand_of_cards, vio.milim_aoe)
                if idx != -1:
                    print(f"Floor 2, Phase 3: Using milim_aoe at index {idx} post-unfreeze")
                    return idx
                idx = self._find_card(hand_of_cards, vio.lolimerl_aoe)
                if idx != -1:
                    print(f"Floor 2, Phase 3: Using lolimerl_aoe at index {idx} post-unfreeze")
                    return idx
                idx = self._find_thor_card(hand_of_cards)
                if idx != -1:
                    print(f"Floor 2, Phase 3: Using Thor card at index {idx} post-unfreeze")
                    return idx
        
        # Default: milim_aoe > lolimerl_aoe > thor_* (no freeze or after unfreezing)
        idx = self._find_card(hand_of_cards, vio.milim_aoe)
        if idx != -1:
            print(f"Floor 2, Phase 3: Using milim_aoe at index {idx}")
            return idx
        idx = self._find_card(hand_of_cards, vio.lolimerl_aoe)
        if idx != -1:
            print(f"Floor 2, Phase 3: Using lolimerl_aoe at index {idx}")
            return idx
        idx = self._find_thor_card(hand_of_cards)
        if idx != -1:
            print(f"Floor 2, Phase 3: Using Thor card at index {idx}")
            return idx
        
        print("Floor 2, Phase 3: No suitable card found, returning -1")
        return -1

    def _floor_3_phase_1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Floor 3, Phase 1: Same as Floor 1, Phase 1"""
        return self._floor_1_phase_1(hand_of_cards, picked_cards)

    def _floor_3_phase_2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Floor 3, Phase 2: Any 4 cards, NEVER use milim_aoe"""
        card_turn = IBattleStrategy.card_turn
        print(f"Floor 3, Phase 2: Card turn {card_turn}")
        
        # Check for freeze_icon
        is_frozen = any(find(vio.freeze_icon, card.card_image) for card in hand_of_cards)
        print(f"Floor 3, Phase 2: Freeze detected: {is_frozen}")
        
        if card_turn in [0, 1, 2, 3]:
            # Strictly avoid milim_aoe cards
            available_ids = [i for i, card in enumerate(hand_of_cards) 
                            if card.card_type != CardTypes.DISABLED and
                            not find(vio.milim_aoe, card.card_image)]
            
            if available_ids:
                idx = available_ids[0]
                print(f"Floor 3, Phase 2: Using non-milim_aoe card at index {idx}")
                return idx
        
        print("Floor 3, Phase 2: No suitable card found, returning -1")
        return -1

    def _floor_3_phase_3(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Floor 3, Phase 3: any *_ult > milim_aoe > thor_* > lolimerl_aoe with freeze handling"""
        card_turn = IBattleStrategy.card_turn
        print(f"Floor 3, Phase 3: Card turn {card_turn}")
        
        # Check for freeze_icon
        is_frozen = any(find(vio.freeze_icon, card.card_image) for card in hand_of_cards)
        print(f"Floor 3, Phase 3: Freeze detected: {is_frozen}")
        
        # Check for any *_ult first
        ult_count = sum(1 for card in hand_of_cards if card.card_type == CardTypes.ULTIMATE and card.card_type != CardTypes.DISABLED)
        picked_ults = sum(1 for card in picked_cards if card.card_type == CardTypes.ULTIMATE)
        if picked_ults < ult_count:
            for i, card in enumerate(hand_of_cards):
                if card.card_type == CardTypes.ULTIMATE and card.card_type != CardTypes.DISABLED:
                    print(f"Floor 3, Phase 3: Using ultimate card #{picked_ults + 1} at index {i}")
                    return i
        
        # Identify who's frozen based on unv_ cards
        has_unv_milim = any(find(vio.unv_milim_aoe, card.card_image) or find(vio.unv_milim_st, card.card_image) 
                            for card in hand_of_cards)
        has_unv_ghel = any(find(vio.unv_ghel_aoe1, card.card_image) or find(vio.unv_ghel_aoe2, card.card_image) or 
                           find(vio.unv_ghel_ult, card.card_image) for card in hand_of_cards)
        has_unv_thor = any(find(vio.unv_thor_1, card.card_image) or find(vio.unv_thor_2, card.card_image) or 
                           find(vio.unv_thor_ult, card.card_image) for card in hand_of_cards)
        has_unv_lolimerl = any(find(vio.unv_lolimerl_aoe, card.card_image) or find(vio.unv_lolimerl_st, card.card_image) 
                            for card in hand_of_cards)
        
        print(f"Floor 3, Phase 3: Milim frozen: {has_unv_milim}, Ghel frozen: {has_unv_ghel}, Thor frozen: {has_unv_thor}, Merlin frozen: {has_unv_lolimerl}")
        
        if is_frozen and (has_unv_milim or has_unv_ghel or has_unv_thor or has_unv_lolimerl):
            # Try Ghel's AOE pair first
            if card_turn - picked_ults == 0:
                idx = self._find_card(hand_of_cards, vio.ghel_aoe1)
                if idx != -1 and self._find_card(hand_of_cards, vio.ghel_aoe2) != -1:  # Ensure both are available
                    print(f"Floor 3, Phase 3: Using ghel_aoe1 at index {idx} to start unfreezing")
                    return idx
                print("Floor 3, Phase 3: ghel_aoe1 not found or no ghel_aoe2, trying Lolimerl")
            elif card_turn - picked_ults == 1 and any(find(vio.ghel_aoe1, card.card_image) for card in picked_cards):
                idx = self._find_card(hand_of_cards, vio.ghel_aoe2)
                if idx != -1:
                    print(f"Floor 3, Phase 3: Using ghel_aoe2 at index {idx} to finish unfreezing")
                    return idx
                print("Floor 3, Phase 3: ghel_aoe2 not found after ghel_aoe1")
            
            # Try Lolimerl's AOE pair if Ghel's not fully available
            elif card_turn - picked_ults == 0:
                idx = self._find_card(hand_of_cards, vio.lolimerl_aoe)
                if idx != -1 and self._count_cards(hand_of_cards, lambda c: find(vio.lolimerl_aoe, c.card_image)) >= 2:
                    print(f"Floor 3, Phase 3: Using lolimerl_aoe at index {idx} to start unfreezing")
                    return idx
                print("Floor 3, Phase 3: Not enough lolimerl_aoe cards")
            elif card_turn - picked_ults == 1 and any(find(vio.lolimerl_aoe, card.card_image) for card in picked_cards):
                idx = self._find_card(hand_of_cards, vio.lolimerl_aoe)
                if idx != -1:
                    print(f"Floor 3, Phase 3: Using lolimerl_aoe at index {idx} to finish unfreezing")
                    return idx
                print("Floor 3, Phase 3: No second lolimerl_aoe found")

            # After unfreezing (turn 2+), use default priority
            elif card_turn - picked_ults >= 2:
                idx = self._find_card(hand_of_cards, vio.milim_aoe)
                if idx != -1:
                    print(f"Floor 3, Phase 3: Using milim_aoe at index {idx} post-unfreeze")
                    return idx
                idx = self._find_thor_card(hand_of_cards)
                if idx != -1:
                    print(f"Floor 3, Phase 3: Using Thor card at index {idx} post-unfreeze")
                    return idx
                idx = self._find_card(hand_of_cards, vio.lolimerl_aoe)
                if idx != -1:
                    print(f"Floor 3, Phase 3: Using lolimerl_aoe at index {idx} post-unfreeze")
                    return idx
        
        # Default: milim_aoe > thor_* > lolimerl_aoe (no freeze or after unfreezing)
        idx = self._find_card(hand_of_cards, vio.milim_aoe)
        if idx != -1:
            print(f"Floor 3, Phase 3: Using milim_aoe at index {idx}")
            return idx
        idx = self._find_thor_card(hand_of_cards)
        if idx != -1:
            print(f"Floor 3, Phase 3: Using Thor card at index {idx}")
            return idx
        idx = self._find_card(hand_of_cards, vio.lolimerl_aoe)
        if idx != -1:
            print(f"Floor 3, Phase 3: Using lolimerl_aoe at index {idx}")
            return idx
        
        print("Floor 3, Phase 3: No suitable card found, returning -1")
        return -1

    # Helper Functions
    def _find_card(self, hand_of_cards: list[Card], card_image) -> int:
        """Find a specific card by image"""
        if card_image is None:
            print("Warning: Card image template is missing!")
            return -1
        for i, card in enumerate(hand_of_cards):
            if find(card_image, card.card_image) and card.card_type != CardTypes.DISABLED:
                return i
        return -1

    def _count_cards(self, hand_of_cards: list[Card], check_func) -> int:
        """Count cards matching a condition"""
        return sum(1 for card in hand_of_cards if check_func(card) and card.card_type != CardTypes.DISABLED)

    def _is_st_or_lolimerl_card(self, card: Card) -> bool:
        """Check if a card is *_st or lolimerl_*"""
        return (find(vio.lolimerl_st, card.card_image) or find(vio.lolimerl_aoe, card.card_image) or 
                find(vio.lolimerl_ult, card.card_image) or find(vio.milim_st, card.card_image) or 
                find(vio.thor_1, card.card_image))  # thor_1 is technically ST-like

    def _find_aoe_card(self, hand_of_cards: list[Card]) -> int:
        """Find any *_aoe card"""
        aoe_cards = [vio.ghel_aoe1, vio.ghel_aoe2, vio.lolimerl_aoe, vio.milim_aoe, 
                     vio.unv_ghel_aoe1, vio.unv_ghel_aoe2, vio.unv_lolimerl_aoe, vio.unv_milim_aoe]
        for card_image in aoe_cards:
            idx = self._find_card(hand_of_cards, card_image)
            if idx != -1:
                return idx
        return -1

    def _find_thor_card(self, hand_of_cards: list[Card]) -> int:
        """Find any thor_* card"""
        thor_cards = [vio.thor_1, vio.thor_2, vio.thor_ult]
        for card_image in thor_cards:
            idx = self._find_card(hand_of_cards, card_image)
            if idx != -1:
                return idx
        return -1