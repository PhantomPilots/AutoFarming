import numpy as np
import utilities.vision_images as vio
from utilities.card_data import Card, CardTypes, CardRanks
from utilities.deer_utilities import is_blue_card, is_green_card, is_red_card, count_cards
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.utilities import capture_window, find
import time
import pyautogui

class DeerBattleStrategy(IBattleStrategy):
    """The logic behind the AI for Deer based on custom strategy"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], floor: int, phase: int) -> int | list[int]:
        """Extract the next card index or movement based on floor and phase"""
        if floor == 1:
            return self.floor_1_strategy(hand_of_cards, picked_cards, phase)
        elif floor == 2:
            return self.floor_2_strategy(hand_of_cards, picked_cards, phase)
        elif floor == 3:
            return self._floor_3_strategy(hand_of_cards, picked_cards, phase)
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)  # Fallback

    def floor_1_strategy(self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int) -> int | list[int]:
        """Strategy for Floor 1"""
        card_turn = IBattleStrategy.card_turn
        
        if phase == 1:
            if card_turn == 0:
                return self._find_card(hand_of_cards, vio.lolimerl_aoe)
            elif card_turn in [1, 2]:
                freyr_1_idx = self._find_card(hand_of_cards, vio.freyr_1)
                if freyr_1_idx is not None:
                    target_idx = freyr_1_idx - 1 if freyr_1_idx > 0 else freyr_1_idx + 1
                    return [freyr_1_idx, target_idx]  # Move freyr_1
            elif card_turn == 3:
                return self._find_card(hand_of_cards, vio.freyr_1)
        
        elif phase == 2:
            if card_turn == 0:
                freyr_2_idx = self._find_card(hand_of_cards, vio.freyr_2)
                if freyr_2_idx is not None:
                    target_idx = freyr_2_idx - 1 if freyr_2_idx > 0 else freyr_2_idx + 1
                    return [freyr_2_idx, target_idx]  # Move freyr_2
            elif card_turn == 1:
                return self._find_card(hand_of_cards, vio.freyr_2)
            elif card_turn == 2:
                return self._find_card(hand_of_cards, vio.lolimerl_st)
            elif card_turn == 3:
                return self._find_card(hand_of_cards, vio.jorm_1)
        
        elif phase == 3:
            available_ids = [i for i, card in enumerate(hand_of_cards) 
                           if not find(vio.freyr_ult, card.card_image) and card.card_type != CardTypes.DISABLED]
            lolimerl_st_count = count_cards(hand_of_cards, lambda c: find(vio.lolimerl_st, c.card_image))
            if lolimerl_st_count > 1 or (lolimerl_st_count == 1 and card_turn < 3):
                available_ids = [i for i in available_ids if not find(vio.lolimerl_st, hand_of_cards[i].card_image)]
            return available_ids[-1] if available_ids else -1
        
        elif phase == 4:
            if card_turn == 0:
                return self._find_card(hand_of_cards, vio.freyr_ult)
            elif card_turn == 1:
                return self._find_card(hand_of_cards, vio.lolimerl_st)
            else:
                return self._random_non_albedo_taunt(hand_of_cards)
        
        return -1

    def floor_2_strategy(self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int) -> int:
        """Strategy for Floor 2"""
        card_turn = IBattleStrategy.card_turn
        
        if phase == 1:
            if card_turn == 0:
                return self._find_card(hand_of_cards, vio.freyr_1)
            elif card_turn == 1:
                return self._find_card(hand_of_cards, vio.jorm_2)
            elif card_turn == 2:
                return self._find_card(hand_of_cards, vio.lolimerl_aoe)
            elif card_turn == 3:
                return self._find_card(hand_of_cards, vio.jorm_1)
        
        elif phase == 2:
            # Enforce order: albedo_1 -> red -> green -> albedo_taunt (index 7)
            if card_turn == 0:
                albedo_1_idx = self._find_card(hand_of_cards, vio.albedo_1)
                if albedo_1_idx != -1:
                    print(f"Floor 2, Phase 2: Using albedo_1 at index {albedo_1_idx}")
                    return albedo_1_idx
                print("Floor 2, Phase 2: albedo_1 not found, using fallback")
                return -1
            elif card_turn == 1:
                red_idx = self._find_red_card(hand_of_cards)
                if red_idx != -1:
                    print(f"Floor 2, Phase 2: Using red card at index {red_idx}")
                    return red_idx
                print("Floor 2, Phase 2: No red card found, using fallback")
                return -1
            elif card_turn == 2:
                green_idx = self._find_green_card(hand_of_cards)
                if green_idx != -1:
                    print(f"Floor 2, Phase 2: Using green card at index {green_idx}")
                    return green_idx
                print("Floor 2, Phase 2: No green card found, using fallback")
                return -1
            elif card_turn == 3:
                if len(hand_of_cards) > 7 and find(vio.albedo_taunt, hand_of_cards[7].card_image) and hand_of_cards[7].card_type != CardTypes.DISABLED:
                    print("Floor 2, Phase 2: Using albedo_taunt at index 7")
                    return 7
                print("Floor 2, Phase 2: albedo_taunt not at index 7 or not playable, using fallback")
                return -1
        
        elif phase == 3:
            available_ids = [i for i, card in enumerate(hand_of_cards) 
                           if not find(vio.freyr_ult, card.card_image) and 
                              not find(vio.lolimerl_ult, card.card_image) and 
                              not find(vio.jorm_ult, card.card_image) and 
                              not find(vio.albedo_ult, card.card_image) and 
                              not find(vio.lolimerl_st, card.card_image)]
            if not available_ids:
                available_ids = [i for i, card in enumerate(hand_of_cards) if card.card_type != CardTypes.DISABLED]
            if card_turn < 3:
                blue_count = count_cards([hand_of_cards[i] for i in available_ids], is_blue_card)
                red_count = count_cards([hand_of_cards[i] for i in available_ids], is_red_card)
                green_count = count_cards([hand_of_cards[i] for i in available_ids], is_green_card)
                if blue_count <= 1:
                    available_ids = [i for i in available_ids if not is_blue_card(hand_of_cards[i])]
                if red_count <= 1:
                    available_ids = [i for i in available_ids if not is_red_card(hand_of_cards[i])]
                if green_count <= 1:
                    available_ids = [i for i in available_ids if not is_green_card(hand_of_cards[i])]
            return available_ids[-1] if available_ids else -1
        
        elif phase == 4:
            if card_turn == 0:
                return self._find_card(hand_of_cards, vio.albedo_1) if count_cards(hand_of_cards, is_blue_card) > 1 else self._find_blue_card(hand_of_cards)
            elif card_turn == 1:
                return self._find_red_card(hand_of_cards)
            elif card_turn == 2:
                return self._find_green_card(hand_of_cards)
            elif card_turn == 3:
                return self._random_non_albedo_taunt(hand_of_cards)
        
        return -1

    def _floor_3_strategy(self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int) -> int | list[int]:
        """Strategy for Floor 3"""
        card_turn = IBattleStrategy.card_turn
        
        if phase == 1:
            if card_turn == 0:
                return self._find_card(hand_of_cards, vio.freyr_1)
            elif card_turn == 1:
                return self._find_card(hand_of_cards, vio.jorm_2)
            elif card_turn == 2:
                return self._find_card(hand_of_cards, vio.lolimerl_aoe)
            elif card_turn == 3:
                return self._find_card(hand_of_cards, vio.jorm_1)
        
        elif phase == 2:
            # Respect color wheel (blue -> red -> green) without using index 6, 7, or 8, and keep 1 red and 1 green
            available_ids = [i for i in range(len(hand_of_cards)) if i not in [6, 7, 8] and hand_of_cards[i].card_type != CardTypes.DISABLED]
            red_count = sum(1 for i in range(len(hand_of_cards)) if is_red_card(hand_of_cards[i]))  # Count all red cards in hand
            green_count = sum(1 for i in range(len(hand_of_cards)) if is_green_card(hand_of_cards[i]))  # Count all green cards in hand
            
            if red_count <= 1:
                available_ids = [i for i in available_ids if not is_red_card(hand_of_cards[i])]
            if green_count <= 1:
                available_ids = [i for i in available_ids if not is_green_card(hand_of_cards[i])]
            
            blue_count = sum(1 for i in available_ids if is_blue_card(hand_of_cards[i]) and not find(vio.albedo_taunt, hand_of_cards[i].card_image))
            red_count_available = sum(1 for i in available_ids if is_red_card(hand_of_cards[i]))
            green_count_available = sum(1 for i in available_ids if is_green_card(hand_of_cards[i]))
            
            if blue_count > 0 and red_count_available > 0 and green_count_available > 0:  # Color wheel possible
                if card_turn == 0:
                    return self._find_blue_card_excluding_6_7_8_and_taunt(hand_of_cards)
                elif card_turn == 1:
                    return self._find_red_card(hand_of_cards)  # Red cards are not at 6/7/8
                elif card_turn == 2:
                    return self._find_green_card(hand_of_cards)  # Green cards are not at 6/7/8
                elif card_turn == 3:
                    return available_ids[-1] if available_ids else -1
            else:
                # Use any card excluding index 6, 7, and 8
                return available_ids[-1] if available_ids else -1
        
        elif phase == 3:
            # Use any card excluding 6, 7, 8, but keep 1 red and 1 green
            available_ids = [i for i in range(len(hand_of_cards)) if i not in [6, 7, 8] and hand_of_cards[i].card_type != CardTypes.DISABLED]
            red_count = sum(1 for i in range(len(hand_of_cards)) if is_red_card(hand_of_cards[i]))  # Count all red cards in hand
            green_count = sum(1 for i in range(len(hand_of_cards)) if is_green_card(hand_of_cards[i]))  # Count all green cards in hand
            
            if red_count <= 1:
                available_ids = [i for i in available_ids if not is_red_card(hand_of_cards[i])]
            if green_count <= 1:
                available_ids = [i for i in available_ids if not is_green_card(hand_of_cards[i])]
            
            return available_ids[-1] if available_ids else -1
        
        elif phase == 4:
            # Enforce order: albedo_1 (index 6) -> red -> green -> albedo_taunt (index 7)
            print(f"Floor 3, Phase 4: Card turn {card_turn}")  # Debug card_turn
            if card_turn == 0:
                if len(hand_of_cards) > 6 and find(vio.albedo_1, hand_of_cards[6].card_image) and hand_of_cards[6].card_type != CardTypes.DISABLED:
                    print("Floor 3, Phase 4: Using albedo_1 at index 6")
                    return 6
                print("Floor 3, Phase 4: albedo_1 not at index 6 or not playable, using fallback")
                return -1
            elif card_turn == 1:
                red_idx = self._find_red_card(hand_of_cards)
                if red_idx != -1:
                    print(f"Floor 3, Phase 4: Using red card at index {red_idx}")
                    return red_idx
                print("Floor 3, Phase 4: No red card found, using fallback")
                return -1
            elif card_turn == 2:
                green_idx = self._find_green_card(hand_of_cards)
                if green_idx != -1 and green_idx != 7:  # Exclude index 7 (reserved for albedo_taunt)
                    print(f"Floor 3, Phase 4: Using green card at index {green_idx}")
                    return green_idx
                print("Floor 3, Phase 4: No green card found (excluding index 7), using fallback")
                return -1
            elif card_turn == 3:
                if len(hand_of_cards) > 7 and find(vio.albedo_taunt, hand_of_cards[7].card_image) and hand_of_cards[7].card_type != CardTypes.DISABLED:
                    print("Floor 3, Phase 4: Using albedo_taunt at index 7")
                    return 7
                print("Floor 3, Phase 4: albedo_taunt not at index 7 or not playable, using fallback")
                return -1
        
        return -1

    def _find_card(self, hand_of_cards: list[Card], card_image) -> int:
        """Find a specific card by image"""
        if card_image is None:
            print(f"Warning: Card image template is missing!")
            return -1
        for i, card in enumerate(hand_of_cards):
            if find(card_image, card.card_image):
                return i
        return -1

    def _find_by_color(self, hand_of_cards: list[Card], color_func) -> int:
        """Find a card by color function"""
        for i, card in enumerate(hand_of_cards):
            if color_func(card):
                return i
        return -1

    def _find_red_card(self, hand_of_cards: list[Card]) -> int:
        return self._find_by_color(hand_of_cards, is_red_card)

    def _find_green_card(self, hand_of_cards: list[Card]) -> int:
        return self._find_by_color(hand_of_cards, is_green_card)

    def _find_blue_card(self, hand_of_cards: list[Card]) -> int:
        return self._find_by_color(hand_of_cards, is_blue_card)

    def _find_blue_card_excluding_6_7_8_and_taunt(self, hand_of_cards: list[Card]) -> int:
        """Find a blue card excluding index 6, 7, 8 and albedo_taunt"""
        for i in range(len(hand_of_cards)):
            if i not in [6, 7, 8] and is_blue_card(hand_of_cards[i]) and not find(vio.albedo_taunt, hand_of_cards[i].card_image):
                return i
        return -1

    def _use_albedo_if_multiple(self, hand_of_cards: list[Card], card_image) -> int:
        """Use albedo card only if multiple blue cards exist"""
        blue_count = count_cards(hand_of_cards, is_blue_card)
        if blue_count > 1:
            return self._find_card(hand_of_cards, card_image)
        return -1

    def _random_non_albedo_taunt(self, hand_of_cards: list[Card]) -> int:
        """Pick a random card that’s not albedo_taunt"""
        available_ids = [i for i, card in enumerate(hand_of_cards) if not find(vio.albedo_taunt, card.card_image)]
        return available_ids[-1] if available_ids else -1