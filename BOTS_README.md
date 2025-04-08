# AVAILABLE BOTS

## Equipment farming script

A script that probably no one needs but me, `scripts/EquipmentFarmer.py` farms gear to extract blue stones while auto-salvaging whenever the equipment inventory becomes full. Then it goes back to farming. 

Requirements for it to work properly:
1. Have the "auto-farming" option of free stages set to 'infinite' with auto-renewal of stamina pots.
2. Have the desired farming team set.
3. Ensure the salvaging options on tavern-Diane are the desired ones.
4. Start the script already from within fighting an equipment farming free stage.

## Floor 4 of Bird

The bot we've all been waiting for: The automatic Floor 4 farmer, in `scripts/BirdFloor4Farmer.py`. It assumes the following team (with all the relics):
* Traitor Meli (recommended) / Freyr
* Thor
* Blue Megellda
* Shion (recommended) / Green Diane

Requirements:
1. **Important**: If you use Diane, place her on the rightmost position in the team.
2. 13M+ box CC (preferably).
3. Constellation 6 (preferably).

## Floor 4 of Deer

In `scripts/DeerFloor4Farmer.py`. It needs the following team:
* Thor (att/crit damage)
* Green Jorm (HP/crit defense)
* Freyr (HP/crit defense)
* Green Hel (att/crit damage). 1/6 is fine, 2+/6 preferable

Start the script from within the Deer floor selection screen.
**Important**: Currently the win rate of the bot on a 15.5m CC and Const 6 account is of 25%, mostly because of RNG.

## Hraesvelgr (Bird) farming script

It's named `scripts/BirdFarmer.py`, and it does what its name says: It farms floors 1-3 of the Bird uninterruptedly, even when stamina is depleted or a fight is lost.

Requirements:
1. Start by being in a screen that's in the path of going to the bird (i.e.: tavern, battle menu, or bird menu).
2. Have the team ready with the proper gear. This doesn't mean "saved" (this will be handled by the script automatically), but rather just set up before clicking the "Save" button.
3. **Important**: If using green/red Diane, place her in the rightmost position.

## Eikthyrnir (Deer) Floors 1-3 farming script

The script is named `scripts/DeerFarmer.py`. 

Required team:
* LR Lostvayne Meli
* Jormungandr
* Blue crazy Roxy
* UR Escanor

<b>Update</b>: With the new Deer Floor 4, the bot has been updated to the new team:
* Green Jorm
* Freyr
* Thor Whale-mode 
* Red Megelda / Green Hel (recommended)

Other requirements:
1. Start the script from within the Deer floor selection screen.
2. Have the team ready with proper gear.

## Whale-mode Eikthyrnir (Deer) Floors 1-3 farming script

The script is named `scripts/DeerFarmerWhale.py`. It uses a very fast but risky strategy.

Team order in this EXACT positioning (left to right): 
* Green Jorm (left) 1st slot
* Loli Merlin (center left) 2nd slot
* Freyr (center right) 3rd slot
* Albedo (right) 4th slot

Minimum Requirements:
* 16M Box CC
* 5TH Constellation Complete
* ALL units with UR Atk-Crit Damage Gear Sets Rolled at 14.5% (Atk Pieces. Def and HP can be whatever roll % but enough to survive in case it doesn't one turn a phase in Floor 3)
* Loli Merlin LR + Relic
* Freyr built decently + Relic
* Albedo + Relic
* Green Jormungandr + Relic
* Sabunak 3/6 Minimum Link under Albedo
* OG Red Sariel 6/6 Link under Loli Merlin LR
* OG Light Mael 4/6 Minimum Link under Jorm

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