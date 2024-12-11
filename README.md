# weatherdisplay
e-ink weather display / tide tracker using a raspberry pi

# instructions
1. Replace placeholders at top of file with your own values.
2. I use a virtual python environment to run this -- you're on your own for figuring out dependencies.
3. I'm using systemd unit files to handle auto-restarting this script on failures (sometimes it gets bad data from the API endpoint that causes a crash) and also have found that having it restart every night seems to keep it most stable. 

# references
I leaned heavily on this: https://www.open-electronics.org/e-ink-tide-and-weather-tracker/
