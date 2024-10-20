# 7DS Grand Cross scripts for auto-farming

This repository contains several scripts for auto-farming specific events in the 7DS Grand Cross mobile game.
For now it's built for Windows only, but it will change in the future.

**Disclaimer**: One downside of these scripts is that they cannot run in the background, i.e., you won't be able to use your PC while autofarming.
Also, use this code at your own risk.

**Disclaimer 2**: These scripts may not work on 4k monitors for reasons yet unknown.

## Samples

<img src="readme_images/snake_sample.gif" alt="Snake GIF" width="15%" style="margin-right: 10px;">
<img src="readme_images/dogs_sample.gif" alt="Dogs GIF" width="15%" style="margin-right: 10px;">
<img src="readme_images/bird_floor_4_sample.gif" alt="Dogs GIF" width="15%">



## Installation

#### Git

To keep up-to-date with any updates, you'll need to install [Git](https://gitforwindows.org/) for Windows. Simply download the executable and install it.

#### Python 

Install Python 3.10 or higher from the Microsoft Store:<br>
<img src="readme_images/python311.png" alt="IDLE app" width="200"/><br>

#### Download the code

1. After you have installed Git from above, open a folder where you want to download the code.
2. While pressing the `SHIFT` key, right-click inside the folder and then click on `Open PowerShell window here`.
3. Once the terminal is open, simply copy the following command and right-click inside the terminal to paste it:<br> 
`git clone https://github.com/PhantomPilots/AutoFarming.git`<br>
and press `ENTER`.
This downloads the code into a folder named _AutoFarming_.
1. Now we need to install some additional Python modules for the scripts to work. To do so, follow these steps:
   1. Open the _AutoFarming_ folder.
   2. Like before, while pressing the `SHIFT` key, right-click inside the folder and then click on `Open PowerShell window here`.
   3. Once the terminal opens, paste the command: `python -m pip install -r requirements.txt` and press `ENTER`.

#### Sizer

Download and install the [Sizer](https://www.brianapps.net/sizer4/) application for custom re-sizing of windows. 
Once installed, open it as administrator and:
1. Set the game in ***portrait*** mode instead of landscape mode (in-game settings).
2. Open Sizer. It's hidden at the bottom-right of your screen:<br>
<img src="readme_images/sizer_icon.png" width="100"/><br>
Right-click on it and select `Configure sizer...`.
3. In Sizer, create a custom size of `540x960` and name it 7DS (first time only).
4. Right-click on the border of the 7DS window and choose the custom size to resize the window:<br>
<img src="readme_images/sizer.png" alt="Sizer" width="200"/><br>
**This needs to be done ever time you want to run a script**.


### Code updates

Updating the code is done using Git. The process is simple:
1. Similarly to Installation point 4.2., open a PowerShell window within the AutoFarming folder.
2. Type in `git pull` and press `ENTER`.
   * If when running `git pull` you get an error/warning saying the code cannot be updated, first run `git stash` and then `git pull` again. You should now see the code updated.

### How to run the scripts

#### Python IDLE

All scripts require being run as administrator. One way to do so is the following:
1. Press the Windows key and type "IDLE". If Python is installed properly, you should see the IDLE app: <br>
<img src="readme_images/idle_python.png" alt="IDLE app" width="200"/><br>
Right-click on it and run it as an administrator.
2. Click on `File -> Open...` and load the script you want to run.
3. To run the script, press the `F5` key while the 7DS window is **fully visible** on the screen.
4. To stop the script, close the new window that appeared after the previous point (where blue text is being written down).

#### PowerShell

Using the Python IDLE is easier, but it doesn't allow for `CTRL+C` to kill some scripts (like the `BirdFarmer.py`). Using PowerShell is a better alternative:
1. Open PowerShell with administrator privileges.
2. Navigate to the folder where you host the scripts. To do so, copy the path location:<br>
<img src="readme_images/copy_location.png" alt="copy_location" width="200"/><br>

3. Paste the location in PowerShell, preceded by `cd `, and press `Enter`:<br>
<img src="readme_images/location_in_powershell.png" width="250"/><br>

4. Finally, type into PowerShell: `python BirdFarmer.py` (or whatever script you're trying to run).
5. Now, to stop any script you can simply press `CTRL+C`.

Happy farming!

## Farming scripts

For detailed information on all the bots available, go to the [bots README file](BOTS_README.md).

## Troubleshooting

* If the script doesn't work as expected (e.g., not clicking anywhere), make sure the game window is resized with the custom size created at the beginning.
* The scripts don't account for random pop-ups (such as demon invitations), so make sure you have those notifications disabled.
* If when updating the code with `git pull` you get an error/warning saying the code cannot be updated, first run `git stash` and then `git pull` again. You should now see the code updated.
* For more errors, please open a new "issue" in the "Issues" tab of this website.


## Shorter-term features
- [X] Farmer for Floor 4 of Bird.
- [ ] Farmer for floors 1-3 of Deer.
- [X] Farmer for floors 1-3 of Dogs.
- [X] Farmer for floors 1-3 of Snake.

## Longer-term features

- [ ] Allow starting the scripts from ANYWHERE.
- [ ] Make the scripts independent of the window size (i.e., scale-invariant).
- [ ] Make them work in 4k monitors.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
