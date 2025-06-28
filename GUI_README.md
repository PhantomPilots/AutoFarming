# AutoFarmers GUI

A graphical user interface for the AutoFarmers project that provides easy access to all farming scripts.

## Features

- **Tabbed Interface**: Each farmer has its own tab with dedicated controls
- **Real-time Terminal Output**: See live output from running farmers
- **Argument Configuration**: Easy-to-use forms for each farmer's parameters
- **Process Management**: Start and stop farmers with dedicated buttons
- **Image Placeholders**: Space for farmer-specific images (to be added later)

## How to Use

### Starting the GUI

```bash
cd scripts
python AutoFarmersGUI.py
```

### Using the Interface

1. **Select a Farmer**: Click on the tab for the farmer you want to use
2. **Configure Arguments**: Fill in the required arguments in the left panel:
   - **Password**: Your account password (optional, for auto-login)
   - **Clears**: Number of runs or "inf" for infinite
   - **Difficulty**: For applicable farmers (Demon, Final Boss)
3. **Start Farming**: Click the green "START" button
4. **Monitor Progress**: Watch the real-time output in the terminal window
5. **Stop Farming**: Click the red "STOP" button when done

### Available Farmers

- **Bird Farmer**: Hraesvelgr floors 1-3
- **Bird Floor 4**: Hraesvelgr floor 4 (hardest content)
- **Deer Farmer**: Eikthyrnir floors 1-3
- **Deer Floor 4**: Eikthyrnir floor 4
- **Deer Whale**: High-risk/high-reward Deer strategy
- **Dogs Farmer**: Skoll and Hati floors 1-3
- **Dogs Whale**: High-risk/high-reward Dogs strategy
- **Snake Farmer**: Nidhogrr floors 1-3
- **Demon Farmer**: Real-time demon battles
- **Final Boss**: Final boss battles
- **Daily Quests**: Complete daily missions
- **Equipment Farmer**: Farm equipment for salvaging

### Features

- **Real-time Output**: Terminal output streams live as the farmer runs
- **Auto-scroll**: Terminal automatically scrolls to show latest output
- **Output Limiting**: Keeps last 1000 lines to prevent memory issues
- **Process Control**: Proper SIGINT handling for graceful shutdown
- **Error Handling**: Displays errors in both popup and terminal
- **Window Management**: Prompts to stop running processes before closing

### Requirements

- Python 3.10 or 3.11
- All AutoFarmers dependencies (see main requirements.txt)
- tkinter (built-in with Python)

### Notes

- The GUI uses tkinter for cross-platform compatibility
- All farmers run as subprocesses, so they can be stopped independently
- The terminal output is limited to prevent memory issues with long-running farmers
- Image placeholders are included for future visual enhancements

### Troubleshooting

- **GUI won't start**: Make sure you're running from the `scripts/` directory
- **Farmer won't start**: Check that all dependencies are installed
- **No output**: Some farmers may take time to start, check the command line output
- **Can't stop farmer**: The GUI will force-kill after 5 seconds if graceful shutdown fails 