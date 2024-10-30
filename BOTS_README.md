# AVAILABLE BOTS

## Equipment farming script

A script that probably no one needs but me, `scripts/EquipmentFarmer.py` farms gear to extract blue stones while auto-salvaging whenever the equipment inventory becomes full. Then it goes back to farming. 

Requirements for it to work properly:
1. Have the "auto-farming" option of free stages set to 'infinite' with auto-renewal of stamina pots.
2. Have the desired farming team set.
3. Ensure the salvaging options on tavern-Diane are the desired ones.
4. Start the script already from within an equipment farming free stage.

## Hraesvelgr (Bird) farming script

It's named `scripts/BirdFarmer.py`, and it does what its name says: It farms floors 1-3 of the Bird uninterruptedly, even when stamina is depleted or a fight is lost.

Requirements:
1. Start by being in a screen that's in the path of going to the bird (i.e.: tavern, battle menu, or bird menu).
2. Have the team ready with the proper gear. This doesn't mean "saved" (this will be handled by the script automatically), but rather just set up before clicking the "Save" button.
3. **Important**: If using green/red Diane, place her in the rightmost position.

## Eikthyrnir (Deer) farming script

The script is named `scripts/DeerFarmer.py`. 

Required team:
* LR Lostvayne Meli
* Jormungandr
* Blue crazy Roxy
* UR Escanor

Other requirements:
1. Start the script from within the Deer floor selection screen.
2. Have the team ready with proper gear.

## Skoll and Hati (Dogs) farming script

The script is in `scripts/DogsFarmer.py`.

Recommended team (in this order):
* UR Escanor
* LR Lostvayne with relic
* Freyr
* Thonar with relic and crit-res gear with crit-res rolls. Ideally True Awakened too.

Requirements:
1. Start the script from within the Dogs floor selection screen.

## Nidhogrr (Snake) farming script

Can be found in `scripts/SnakeFarmer.py`. 

Recommended team:
* Mael
* Red Margaret
* Freyja with relic
* LR Liz

Requirements:
1. Start the script from within the Snake floor selection screen.

## Final Boss farming script

It's in `scripts/FinalBossFarmer.py`, and it accepts all difficulties. To change the difficulty, simply change the desired difficulty name in the script. It may default to either "challenge" or "hell", pay attention in which one you want:

<img src="readme_images/final_boss_difficulty.png" width="400"/>

## Demon farming script

In `scripts/DemonFarmer.py`, it's a script that looks for real-time demon fights in a non-stopping loop. It's an infinite source of demon materials without wasting any resource! It accepts any demon, from Red to Bellmoth and OG.
So far, it only accepts the "Hell" difficulty.

**An important feature** is that the bot will stop farming demons **at 2am PT time** to **check in and do all the daily missions** except PVP (unless the option is enabled, see below).

You can find all the setup options inside the file:

```python
FarmingFactory.main_loop(
    farmer=DemonFarmer,
    starting_state=States.GOING_TO_DEMONS,  # Should be 'GOING_TO_DEMONS'
    demon_to_farm=vio.og_demon,  # Accepts: 'vio.og_demon', 'vio.bell_demon', 'vio.red_demon', 'vio.gray_demon', 'vio.crimson_demon'
    time_to_sleep=9.3,  # How many seconds to sleep before accepting an invitation
    do_dailies=True,  # Do we halt demon farming to do dailies?
    do_daily_pvp=False,  # If we do dailies, do we do PVP?
)
```

* To select the demon, inside `DemonFarmer.py` change the demon type in this line:<br>
```demon_to_farm=vio.bell_demon,  # Accepts: vio.og_demon, vio.bell_demon, vio.red_demon, vio.gray_demon, vio.crimson_demon```

* You may need to play with the timing in the line:<br>
```time_to_sleep=9.3,  # How many seconds to sleep before accepting an invitation```<br>
⚠ Lower than `9.2`, you'll risk wasting all your 3 daily demon invites.

* Doing the automatic dailies can be disabled by setting its option to `False`. PVP daily mission can be enabled by setting its option to `True`.

## Floor 4 of Bird

The bot we've all been waiting for: The automatic Floor 4 farmer, in `scripts/Floor4Farmer.py`. It assumes the following team (with all the relics):
* Traitor Meli
* Thor
* Blue Megellda
* Green Diane

Requirements:
1. **Important**: Place Diane on the rightmost position in the team.
2. Always start from within the floor 4 bird fight already.
3. 13M+ box CC (preferably).
4. Constellation 6 (preferably).