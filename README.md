# Pi-Hole
Support scripts and configurations for Pi-Hole


## Updating the OS

```
sudo apt update
sudo apt -y upgrade
```

## Add Some Packages

### Required Python Packages
```
sudo apt install --upgrade python3-pip python3-venv python3-setuptools
```

### Install the `uv` Python Package Manager
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Optional Packages
These packages are not strictly required, but nice-to-have.
```
sudo apt install -y vim
```

### Run Your Script Automatically as a Systemctl Service

#### Create a Systemctl Service for the Script

Create a file named `pihole-display.service` in the directory `/etc/systemd/system/`.
```
sudo vim /etc/systemd/system/pihole-display.service
```

Copy and paste the contents below and save the file.

```ini
[Unit]
Description=Display Pi-hole stats when buttons are pressed

# This unit is supposed to indicate when network functionality is available, but it is only
# very weakly defined what that is supposed to mean, with one exception: at shutdown, a unit
# that is ordered after network-online.target will be stopped before the network
After=network-online.target pihole-FTL.service
Requires=pihole-FTL.service

# Limit (re)start loop to 5 within 2 minutes
StartLimitBurst=5
StartLimitIntervalSec=120s

[Service]
User=herrin
WorkingDirectory=/home/herrin/Projects/Pi-Hole

ExecStart=/home/herrin/.local/bin/uv run --project /home/herrin/Projects/Pi-Hole /home/herrin/Projects/Pi-Hole/pihole_display.py
Restart=on-failure
RestartSec=5s
ExecReload=/bin/kill -HUP $MAINPID

# Use graceful shutdown with a reasonable timeout
TimeoutStopSec=10s

# Make /usr, /boot, /etc and possibly some more folders read-only...
ProtectSystem=full

[Install]
WantedBy=multi-user.target
```

#### Enable the New Systemctl Service

Run the following commands to enable and start the `systemctl` service.  This will automatically run the script and let it continuously run in the background.

```
sudo systemctl enable mouselogger.service
sudo systemctl start mouselogger.service
```

## References

- [Pi Hole Tutorial for Raspberry Pi Zero W from AdaFruit](https://learn.adafruit.com/pi-hole-ad-blocker-with-pi-zero-w)
- [Pi Hole Unbound installation and configuration](https://docs.pi-hole.net/guides/dns/unbound/)
- [Git Repo for Pi-Hole scripts](https://github.com/adafruit/Adafruit_Learning_System_Guides/tree/main/Pi_Hole_Ad_Blocker)
- [Pi-Hole v6 Python-based API library](https://github.com/sbarbett/pihole6api)
- [FireBog.new block lists](https://firebog.net/)
- [Systemd service creation](https://learn.adafruit.com/running-programs-automatically-on-your-tiny-computer/systemd-writing-and-enabling-a-service)
