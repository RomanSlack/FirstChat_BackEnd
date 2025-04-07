#!/bin/bash
# Launch Chrome with remote debugging enabled

# Default profile path
PROFILE="/home/roman-slack/.config/google-chrome/Profile 4"

# Allow profile override
if [ "$1" != "" ]; then
    PROFILE="$1"
fi

DEBUGGING_PORT=9222

echo "Launching Chrome with remote debugging enabled"
echo "Profile: $PROFILE"
echo "Remote debugging port: $DEBUGGING_PORT"
echo ""
echo "1. Chrome will open with your profile"
echo "2. Navigate to Tinder and log in if necessary"
echo "3. Enable mobile emulation (F12 -> Toggle device toolbar -> iPhone 14 Pro Max)"
echo "4. Leave Chrome running and go back to the terminal"
echo "5. Run the scraper in another terminal with: ./run_scraper"
echo ""
echo "Press Enter to continue..."
read

# Launch Chrome with remote debugging
google-chrome --user-data-dir="$PROFILE" --remote-debugging-port=$DEBUGGING_PORT --no-first-run --no-default-browser-check &

echo "Chrome launched! Open Tinder and set up mobile emulation, then run the scraper."