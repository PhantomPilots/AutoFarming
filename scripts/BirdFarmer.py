import utilities.vision_images as vio
from utilities.bird_farming_logic import BirdFarmer, States
from utilities.farming_factory import FarmingFactory
from utilities.fighting_strategies import DummyBattleStrategy, SmarterBattleStrategy
from utilities.utilities import (
    capture_hand_image,
    capture_window,
    crop_image,
    determine_card_merge,
    determine_relative_coordinates,
    display_image,
    get_hand_cards,
    screenshot_testing,
)


def development():
    """Some development function calls"""

    # determine_relative_coordinates(capture_window()[0])

    cards = get_hand_cards()
    for i, card in enumerate(cards, start=0):
        print(card.card_type.name, card.card_rank.name)

        # print(card.card_image.shape)

        # border = 8
        # new_image = crop_image(
        #     card.card_image,
        #     (border, border + 4),
        #     (card.card_image.shape[1] - border, card.card_image.shape[0] - border - 12),
        # )
        # display_image(new_image)

        if i > 0 and i < len(cards) - 1 and determine_card_merge(cards[i - 1], cards[i + 1]):
            print("Card generates a merge!")
            display_image(card.card_image)

    # determine_relative_coordinates(capture_hand_image)
    # screenshot_testing(vision_image=vio.floor_3_cleard_2, threshold=0.9)

    return


def main():

    FarmingFactory.main_loop(
        farmer=BirdFarmer,
        battle_strategy=SmarterBattleStrategy,  # The AI that will pick the cards
        starting_state=States.GOING_TO_BIRD,  # Should be 'GOING_TO_BIRD'
    )


if __name__ == "__main__":

    ### The line below is for development/debugging purposes, don't uncomment
    # development()

    main()
