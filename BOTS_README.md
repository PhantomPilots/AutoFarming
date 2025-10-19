# AVAILABLE BOTS

## Demon farming script

In `scripts/DemonFarmer.py`, it's a script that looks for real-time demon fights in a non-stopping loop. It's an infinite source of demon materials without wasting any resource! It accepts any demon, from Red to Indura.
So far, it only accepts the "Hell" difficulty (except for Indura, which accepts all).

* You can find all the setup options inside the corresponding GUI tab.
* You may need to play with "time to sleep" value, which determines how many seconds to wait before accepting an invite.
⚠ Lower than `9`, you'll risk wasting all your 3 daily demon invites.

## Demon King farmer

Farms the Demon King fight. You're responsible for in-game pre-setting what coins to use.

**Requirements**:
* Team A: DK Meli (att/crit), LR Cusack (att/crit), G Gelda (HP/lifesteal), any 4th
* Team B: Skuld (att/crit), any 3 boosters

**Disclaimer**: The rules on phase 2 are not well understood yet, work in progress.

## Guild Boss farmer

It farms Guild Boss uninterruptedly. Should be used during stsamina reduction days only!

**Requirement:** Start the bot from within a fight already.

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
* Green Jorm (att/def)
* Freyr (att/crit damage)
* Green Tyr (preferable) / Green Hel. Both with (att/crit damage)

Start the script from within the Deer floor selection screen.<br>
**Note** that all units should have attack gear. The current expected win rate is of 60% with Tyr, 30% with Hel.<br>

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

## Whale-mode Skoll and Hati (Dogs) Floors 1-3 farming script

The script is named `scripts/DogsFarmerWhale.py`. It uses a very fast but more risky strategy (will likely lose with a Freeze debuff at the wrong time). 

Required team:
* Milim LR - !!!IMPORTANT Green or Blue Ludociel of Flash 6/6 link
* Loli Merlin LR - OG Red Sariel 6/6 link
* Thor UR - Sabunak 4/6+ link
* Green Hel - OG Light Mael 4/6+ link

Artifact set/s:
* Use Set №37 or №29 (Maxed). 

Minimum Unit Requirements:
* 14M-16M+ Box CC (14M+ you lose more runs, from 16M+ you're going to be fine most of the times)
* 6TH Constellation Complete (6TH is ideal but 5TH complete should also be fine)
* ALL units with UR Atk-Crit Damage Gear Sets with the Atk Pieces (Top Row) Rolled at 14.5%+. The rest can be whatever but enough to survive just in case the Dog/s survive and attack you.
* Loli Merlin LR + Relic
* Milim LR + Relic
* Thor UR built good
* Green Hel built decently 
* Sabunak 4/6 Minimum Link
* OG Red Sariel 6/6 Link
* OG Light Mael 4/6 Minimum Link

## Nidhoggr (Snake) farming script

Can be found in `scripts/SnakeFarmer.py`. 

Recommended team:
* Mael
* Red Margaret
* Freyja with relic
* LR Liz

Requirements:
1. Start the script from within the Snake floor selection screen.

## Whale-mode Nidhoggr (Snake) Floors 1-3 farming script

The script is named `scripts/SnakeFarmerWhale.py`. It uses a very fast but more risky strategy (can lose if your account/units aren't strong enough to one shot him each phase). 

Required team:
* Sung Jinwoo - Roxy of Frenzy (either one) 6/6 link
* Nasiens - UR Escanor or Skuld 3/6+ link 
* Cha Hae-In - !!!IMPORTANT She has to have the LOWEST HP of the team. Red Tarmiel 6/6 link
* Urek Mazino - Sabunak 4/6+ link

Artifact set/s:
* Use Set №37 or №29 (Maxed). 

Food (not necessary at all):
* Crit Chance if you're using Red Tarmiel link, Lifesteal or ATK if you use Mage Merlin.
* HP or DEF if you want to be SUUUUUUPER safe.

Minimum Unit Requirements:
* 16M+ Box CC (recommended high box cc as the team is basically a glass cannon)
* 6TH Constellation Complete (6TH is ideal but 5TH complete should also be fine)
* Jinwoo, Cha, Urek Atk-Crit Damage rolled 14.5%+. Nasiens HP-Def rolled 14.5%+.
* Jinwoo + Relic
* Nasiens built good
* Cha Hae-In + Relic
* Urek Mazino + Relic
* Sabunak 4/6 Minimum Link
* OG Roxy of Frenzy or the Christmas one 6/6 Link
* UR Escanor or Skuld 3/6 Minimum Link

Requirements:
1. Start the script from within the Snake floor selection screen.

## Final Boss farming script

It's in `scripts/FinalBossFarmer.py`, and it accepts all difficulties. To change the difficulty, simply change the desired difficulty name in the script. It may default to either "challenge" or "hell", pay attention in which one you want:

<img src="readme_images/final_boss_difficulty.png" width="400"/>

