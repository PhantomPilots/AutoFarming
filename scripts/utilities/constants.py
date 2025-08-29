"""File that just contains constants to imported by other files.
This file should not import any other custom module"""

import pytz

# For dailies and logging back in after being logged out
PACIFIC_TIMEZONE = pytz.timezone("America/Los_Angeles")
MINUTES_TO_WAIT_BEFORE_LOGIN = 30
CHECK_IN_HOUR = 2  # Pacific Time
