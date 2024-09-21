# AVAILABLE BOTS

## Equipment farming script

A script that probably no one needs but me, `scripts/EquipmentFarmer.py` farms gear to extract blue stones while auto-salvaging whenever the equipment inventory becomes full. Then it goes back to farming. 

Requirements for it to work properly:
1. Have the "auto-farming" option of free stages set to 'infinite' with auto-renewal of stamina pots.
2. Have the desired farming team set.
3. Ensure the salvaging options on tavern-Diane are the desired ones.
4. Start the script already from within an equipment farming free stage.

## Hraesvelgr (Bird) farming script

Now, this script is far more interesting for the majority of the community. It's named `scripts/BirdFarmer.py`, and it does what its name says: It farms floors 1-3 of the Bird uninterruptedly, even when stamina is depleted or a fight is lost.

Requirements:
1. Start by being in a screen that's in the path of going to the bird (i.e.: tavern, battle menu, or bird menu).
2. Have the team ready with the proper gear. This doesn't mean "saved" (this will be handled by the script automatically), but rather just set up before clicking the "Save" button.

## Skoll and Hati (Dogs) farming script

The script is in `scripts/DogsFarmer.py`.

Recommended team (in this order):
1. UR Escanor
2. LR Lostvayne with relic
3. Freyr
4. Thonar with relic and crit-res gear with crit-res rolls. Ideally True Awakened too.

Requirements:
1. Start the script from within the Dogs floors screen.

## Final Boss farming script

It's in `scripts/FinalBossFarmer.py`, and it accepts all difficulties. To change the difficulty, simply change the desired difficulty name in the script. It may default to either "challenge" or "hell", pay attention in which one you want:

<img src="readme_images/final_boss_difficulty.png" width="400"/>

## Demon farming script

In `scripts/DemonFarmer.py`, it's a script that looks for real-time demon fights in a non-stopping loop. It's an infinite source of demon materials without wasting any resource! It accepts any demon, from Red to Bellmoth and OG.
So far, it only accepts the "Hell" difficulty.

To select the demon, inside `DemonFarmer.py` change the demon type in this line:

```demon_to_farm=vio.bell_demon,  # Accepts: 'vio.og_demon', 'vio.bell_demon', 'vio.red_demon', 'vio.gray_demon', 'vio.crimson_demon'```

**Note** that you may need to play with the timing in the line:<br>
```time_to_sleep=9.4,  # How many seconds to sleep before accepting an invitation```<br>
If `9.4` is too high, lower it to `9.3` or `9.2` at most. Lower than that, you'll risk wasting all your 3 daily demon invites.


## Floor 4 of Bird

The bot we've all been waiting for: The automatic Floor 4 farmer, in `scripts/Floor4Farmer.py`. It assumes the following team (with all the relics):
* Traitor Meli
* Thor
* Green Diane (preferably) or Freyr
* Blue Megellda

Requirements:
1. **Important**: Place Diane on the rightmost position in the team.
2. Always start from within the floor 4 bird fight already.
3. 13M+ box CC (preferably).
4. Constellation 6 (preferably).

**Disclaimer**: The script fails most of the times due to RNG, even if the AI logic is sound (e.g., not getting enough silver cards on phase 2, or not enough amplify/Thor cards on phase 3). Additionally, you need to have a very strong account, probably **13M+ box CC**, and be on or close to **Constellation 6**.