# Pi-Hole
Support scripts and configurations for Pi-Hole


## Updating the OS

```
sudo apt update
sudo apt -y upgrade
```

## Add Some Packages

### Required Pyton Packages
```
sudo apt install --upgrade python3-pip python3-venv python3-setuptools
```

### Optional Packages
These packages are not strictly required, but nice-to-have.
```
sudo apt install -y vim
```

## Install and Configure Unbound

These notes have been *heavily* borrowed from the following page: [Pi Hole Unbound installation and configuration](https://docs.pi-hole.net/guides/dns/unbound/)

Install unbound using a package manager
```
sudo apt install unbound
```

### Configure `unbound`:
Create and/or edit the file `/etc/unbound/unbound.conf.d/pi-hole.conf`.
```
sudo touch /etc/unbound/unbound.conf.d/pi-hole.conf
```

Update the contents of the file with the following:
```
server:
    # If no logfile is specified, syslog is used
    # logfile: "/var/log/unbound/unbound.log"
    verbosity: 0

    interface: 127.0.0.1
    port: 5335
    do-ip4: yes
    do-udp: yes
    do-tcp: yes

    # May be set to no if you don't have IPv6 connectivity
    do-ip6: yes

    # You want to leave this to no unless you have *native* IPv6. With 6to4 and
    # Terredo tunnels your web browser should favor IPv4 for the same reasons
    prefer-ip6: no

    # Use this only when you downloaded the list of primary root servers!
    # If you use the default dns-root-data package, unbound will find it automatically
    #root-hints: "/var/lib/unbound/root.hints"

    # Trust glue only if it is within the server's authority
    harden-glue: yes

    # Require DNSSEC data for trust-anchored zones, if such data is absent, the zone becomes BOGUS
    harden-dnssec-stripped: yes

    # Don't use Capitalization randomization as it known to cause DNSSEC issues sometimes
    # see https://discourse.pi-hole.net/t/unbound-stubby-or-dnscrypt-proxy/9378 for further details
    use-caps-for-id: no

    # Reduce EDNS reassembly buffer size.
    # IP fragmentation is unreliable on the Internet today, and can cause
    # transmission failures when large DNS messages are sent via UDP. Even
    # when fragmentation does work, it may not be secure; it is theoretically
    # possible to spoof parts of a fragmented DNS message, without easy
    # detection at the receiving end. Recently, there was an excellent study
    # >>> Defragmenting DNS - Determining the optimal maximum UDP response size for DNS <<<
    # by Axel Koolhaas, and Tjeerd Slokker (https://indico.dns-oarc.net/event/36/contributions/776/)
    # in collaboration with NLnet Labs explored DNS using real world data from the
    # the RIPE Atlas probes and the researchers suggested different values for
    # IPv4 and IPv6 and in different scenarios. They advise that servers should
    # be configured to limit DNS messages sent over UDP to a size that will not
    # trigger fragmentation on typical network links. DNS servers can switch
    # from UDP to TCP when a DNS response is too big to fit in this limited
    # buffer size. This value has also been suggested in DNS Flag Day 2020.
    edns-buffer-size: 1232

    # Perform prefetching of close to expired message cache entries
    # This only applies to domains that have been frequently queried
    prefetch: yes

    # One thread should be sufficient, can be increased on beefy machines. In reality for most users running on small networks or on a single machine, it should be unnecessary to seek performance enhancement by increasing num-threads above 1.
    num-threads: 1

    # Ensure kernel buffer is large enough to not lose messages in traffic spikes
    so-rcvbuf: 1m

    # Ensure privacy of local IP ranges
    private-address: 192.168.0.0/16
    private-address: 169.254.0.0/16
    private-address: 172.16.0.0/12
    private-address: 10.0.0.0/8
    private-address: fd00::/8
    private-address: fe80::/10

    # Ensure no reverse queries to non-public IP ranges (RFC6303 4.2)
    private-address: 192.0.2.0/24
    private-address: 198.51.100.0/24
    private-address: 203.0.113.0/24
    private-address: 255.255.255.255/32
    private-address: 2001:db8::/32
```

Start the `unbound` service and check that the service is working:

```
sudo systemctl unbound restart
dig pi-hole.net @127.0.0.1 -p 5335
```

### Validate the `unbound` Installation

Test the DNSSEC validation using:
```
dig fail01.dnssec.works @127.0.0.1 -p 5335
dig dnssec.works @127.0.0.1 -p 5335
```
The first command should return a status of `SERVFAIL` and no IP address.  The second command should return a `NOERROR` status and an IP address.

### Configure Pi-Hole
Finally, configure Pi-hole to use your recursive DNS server by specifying `127.0.0.1#5335` in the `Settings > DNS > Custom DNS` servers section and ensuring that all the other upstream servers are unticked, as shown below:

!!! Add image here !!!

NOTE: Don't forget to click on the `Save & Apply` button to store the new configuration.

### Disable `resolvconf.conf` entry for `unbound` (Required for Debian Bullseye+ releases)

#### Step 1 - Disable the Service

Check if the service is enabled for your distribution:
```
systemctl is-active unbound-resolvconf.service
```

Disable the service with the following command:
```
sudo systemctl disable --now unbound-resolvconf.service
```

#### Step 2 - Diable the file resolvconf_resolver.conf
Disable the file `resolvconf_resolvers.conf` from being generated when `resolvconf` is invoked elsewhere.
```
sudo sed -Ei 's/^unbound_conf=/#unbound_conf=/' /etc/resolvconf.conf
sudo rm /etc/unbound/unbound.conf.d/resolvconf_resolvers.conf
```

Restart the `unbound` service.
```
sudo service unbound restart
```

### Add Logging to `unbound`

First, specify the log file, human-readable timestamps and the verbosity level in the server part of `/etc/unbound/unbound.conf.d/pi-hole.conf`:
```
server:
    # If no logfile is specified, syslog is used
    logfile: "/var/log/unbound/unbound.log"
    log-time-ascii: yes
    verbosity: 1
```

Second, create the log directory and file, and set the permissions:
```
sudo mkdir -p /var/log/unbound
sudo touch /var/log/unbound/unbound.log
sudo chown unbound /var/log/unbound/unbound.log
```

On modern Debian/Ubuntu-based Linux systems, you'll also have to add an AppArmor exception for this new file so `unbound` can write into it.

Create (or edit if existing) the file `/etc/apparmor.d/local/usr.sbin.unbound` and append
```
/var/log/unbound/unbound.log rw,
```
to the end (make sure this value is the same as above). Then reload AppArmor using
```
sudo apparmor_parser -r /etc/apparmor.d/usr.sbin.unbound
sudo service apparmor restart
```

And lastly, restart `unbound`:
```
sudo service unbound restart
```


## References

- [Pi Hole Tutorial for Raspberry Pi Zero W from AdaFruit](https://learn.adafruit.com/pi-hole-ad-blocker-with-pi-zero-w)
- [Pi Hole Unbound installation and configuration](https://docs.pi-hole.net/guides/dns/unbound/)
- [Git Repo for Pi-Hole scripts](https://github.com/adafruit/Adafruit_Learning_System_Guides/tree/main/Pi_Hole_Ad_Blocker)
- [Pi-Hole v6 Python-based API library](https://github.com/sbarbett/pihole6api)
- [FireBog.new block lists](https://firebog.net/)
