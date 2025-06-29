# AutoFarmers GUI

A beautiful graphical user interface for the AutoFarmers project that provides easy access to all farming scripts for 7DS Grand Cross.

## Features

- **Tabbed Interface**: Each farmer has its own tab with dedicated controls and images
- **Real-time Terminal Output**: See live output from running farmers as they work
- **Easy Configuration**: Simple forms for each farmer's settings - no need to remember command lines
- **Process Management**: Start and stop farmers with dedicated buttons
- **Farmer Images**: Visual representation of each farming type
- **Window Resizing**: Automatically resizes your game window for optimal performance
- **Free Software**: This is completely free and open source software

## How to Use

### Starting the GUI

1. **Open PowerShell as Administrator**: Right-click on the Start menu and select "Windows PowerShell (Admin)"
2. **Navigate to the scripts folder**: Copy the path to your AutoFarmers folder and add `\scripts` to the end
3. **Run the GUI**: Type `python AutoFarmers.py` and press Enter

### Using the Interface

1. **Select a Farmer**: Click on the tab for the farmer you want to use (Bird, Deer, Dogs, etc.)
2. **Configure Settings**: Fill in the required settings in the left panel:
   - **Password**: Your account password (optional, for auto-login)
   - **Clears**: Number of runs or "inf" for infinite farming
   - **Difficulty**: For applicable farmers (Demon, Final Boss)
   - **Demons to Farm**: For Demon Farmer, select which demons to battle
   - **Time to Sleep**: How long to wait between actions (in seconds)
   - **Do Dailies**: Check this box to complete daily missions automatically
3. **Start Farming**: Click the green "START" button
4. **Monitor Progress**: Watch the real-time output in the terminal window on the right
5. **Stop Farming**: Click the red "STOP" button when done

### Available Farmers

- **Demon Farmer**: Battle various demons (Indura, OG, Bell, Red, Gray, Crimson) with difficulty settings
- **Bird Farmer**: Farm Hraesvelgr floors 1-3 for bird materials
- **Bird Floor 4**: Farm Hraesvelgr floor 4 (hardest bird content)
- **Deer Farmer**: Farm Eikthyrnir floors 1-3 for deer materials
- **Deer Floor 4**: Farm Eikthyrnir floor 4
- **Deer Whale**: High-risk/high-reward Deer strategy for advanced players
- **Dogs Farmer**: Farm Skoll and Hati floors 1-3 for dog materials
- **Dogs Whale**: High-risk/high-reward Dogs strategy for advanced players
- **Snake Farmer**: Farm Nidhogrr floors 1-3 for snake materials
- **Final Boss**: Battle final bosses with different difficulty levels
- **Tower Trials**: Complete tower trial challenges

### Key Features

- **Real-time Output**: See exactly what your farmer is doing as it happens
- **Auto-scroll**: Terminal automatically scrolls to show the latest activity
- **Smart Output Management**: Keeps the last 1000 lines to prevent memory issues
- **Safe Process Control**: Proper shutdown handling to avoid crashes
- **Error Display**: Shows errors clearly in both popup messages and terminal
- **Window Management**: Automatically resizes your game window for best performance
- **Image Support**: Each farmer has its own visual representation

### Requirements

- **Python 3.10 or 3.11**: Download from Microsoft Store (recommended) or python.org
- **All AutoFarmers Dependencies**: Run `python -m pip install -r requirements.txt` in the main `AutoFarmers/` folder

### Important Notes

- **Game Window**: The GUI automatically resizes your 7DS Grand Cross window to 538x921 pixels for optimal performance
- **Independent Farmers**: Each farmer runs separately, so you can stop one without affecting others
- **Memory Efficient**: Output is limited to prevent memory issues during long farming sessions
- **Cross-Platform**: Works on Windows (primary), with potential for other platforms
- **Free Software**: This is completely free - if you paid for it, you were scammed!

### Troubleshooting

- **GUI won't start**: 
  - Make sure you're running from the `scripts/` directory
  - Ensure Python 3.10 or 3.11 is installed
  - Try running PowerShell as Administrator
- **Farmer won't start**: 
  - Check that all dependencies are installed (`pip install -r requirements.txt`)
  - Make sure your game is running and visible
  - Verify the game window can be resized
  - Sometimes the farmer takes a bit to start, be patient
- **No output**: 
  - Some farmers take time to start up
  - Check that your game is in the correct state
  - Try clicking the "CLEAR" button and starting again
- **Can't stop farmer**: 
  - The GUI will force-stop after 5 seconds if needed
  - You can also close the GUI window to stop all farmers
- **Window resize issues**: 
  - Make sure your game window is not minimized
  - Try manually resizing your game window first
  - Click the "RESIZE" button to manually trigger window resizing

### Tips for Best Results

1. **Start with Simple Farmers**: Try Bird Farmer or Deer Farmer first to get familiar with the system
2. **Use Infinite Mode**: Set "Clears" to "inf" for continuous farming
3. **Enable Dailies**: Check "Do Dailies" to maximize your daily rewards
4. **Monitor Output**: Keep an eye on the terminal to see what's happening
5. **Test Settings**: Start with default settings and adjust as needed
6. **Keep Game Visible**: Don't minimize the game window while farming

Happy farming! 🎮 