---
layout: post
title: How to sync mail using mutt-wizard and systemd
description: Recently mutt-wizard (mw) removed the built-in option to configure
  a cron job to regularly sync mail. This article describes how to configure
  systemd as a replacement to cron for this job.
---
Recently mutt-wizard (mw) removed the built-in option to configure a cron job to regularly sync mail. This leaves users no choice but to schedule regular syncs themselves. I chose to use systemd and here is what I found works well.

systemd is a monolithic system manager which nowadays much of popular operating systems. [Controversy](https://suckless.org/sucks/systemd/) aside, see how we can use it to also manage our email sync.

## Create a systemd user service and timer

As mentioned above, systemd is a **system**-wide manager, meaning it can run at the global level across all users. But that's no good for our email syncing as we only want it to happen for our particular user on the machine when we are logged in.

Luckily, systemd offers users the ability to manage their own services with their own personal systemd instance. How do we do this? We are interested in `.config/systemd/user` -- create this directory if it doesn't exist.

In this directory, create two files:\
`~/.config/systemd/user/mwsync.service`

```editorconfig
[unit]
description=mutt-wizard synchronisation service

[service]
type=oneshot
execstart=/usr/bin/mw sync
```

`~/.config/systemd/user/mwsync.timer`

```editorconfig
[Unit]
Description=Mutt-wizard synchronisation timer

[Timer]
OnBootSec=1m
OnUnitActiveSec=1m
Unit=mwsync.service

[Install]
WantedBy=timers.target
```

This server-timer pair will run `mw sync` every minute from the time you log in. You  can adjust the frequency by adjusting the values in the timer file.

## Enable and start the timer

Nothing will happen yet because we need to enable the timer which will then run the service every minute.

```bash
systemctl --user enable mwsync.timer
systemctl --user start mwsync.timer
```

The `enable` argument ensures this unit status up automatically on login. The `start` argument actually starts it this time. Notice we are using the `--user` flag. This tells systemd we are interested in managing our own configured services.

Wait around for a minute and then check the status of your new service with

```bash
systemctl --user status mwsync
```

Here you can see whether the timer is active and waiting, and how much time until the next time it runs.

You will probably see an error like this

```
● mwsync.service - Mutt-wizard synchronisation service
     Loaded: loaded (/home/t/.config/systemd/user/mwsync.service; static)
     Active: inactive (dead) since Thu 2020-09-24 19:11:18 AEST; 20s ago
TriggeredBy: ● mwsync.timer
    Process: 12817 ExecStart=/usr/bin/mw sync (code=exited, status=0/SUCCESS)
   Main PID: 12817 (code=exited, status=0/SUCCESS)

Sep 24 19:11:18 t430s systemd[358]: Starting Mutt-wizard synchronisation service...
Sep 24 19:11:18 t430s mw[12817]: `pass` must be installed and initialized to encrypt passwords.
Sep 24 19:11:18 t430s mw[12817]: Be sure it is installed and run `pass init <yourgpgemail>`.
Sep 24 19:11:18 t430s mw[12817]: If you don't have a GPG public private key pair, run `gpg --full-gen-key` first.
Sep 24 19:11:18 t430s systemd[358]: mwsync.service: Succeeded.
Sep 24 19:11:18 t430s systemd[358]: Finished Mutt-wizard synchronization service.
```

So it doesn't recognise your password manager or your GPG keys! That's odd, considering `mw sync` probably works just fine if you run it yourself in your terminal...

## Environment variables

The user instance of systemd does not inherit any of the environment variables set by the user (e.g. from `.profile` or `.bashrc`, etc.). There are [several ways](https://wiki.archlinux.org/index.php/Systemd/User) to set environment variables for the systemd user but here's one really good choice for us:

Create a folder at `~/.config/environment.d` if one doesn't exist already. This is where we write files that define the user service environment.

The syntax is [a bit particular](https://www.freedesktop.org/software/systemd/man/environment.d.html) but here we are creating a file called `10-mwsync.conf`. The `10-` prefix means this config file gets high priority over other potential configuration files in this directory. The name isn't too important but is a good idea to have separate files for different purposes and the name is a good way to organise these.

`~/.config/environment.d/10-mwsync.conf`

```editorconfig
NOTMUCH_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/notmuch-config"
PASSWORD_STORE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/password-store"
```

This tells systemd to use the environment variables for the notmuch database and password store configuration required for mutt-wizard to sync our mail.

Now let's refresh the systemd daemon

```bash
systemctl --user daemon-reload
```

and wait a minute for the next run.

## The moment of truth

Let's check back in with

```bash
systemctl --user status mwsync
```

This time we get a success!

```
● mwsync.service - Mutt-wizard synchronisation service
     Loaded: loaded (/home/t/.config/systemd/user/mwsync.service; static)
     Active: inactive (dead) since Thu 2020-09-24 19:08:16 AEST; 1s ago
TriggeredBy: ● mwsync.timer
    Process: 12127 ExecStart=/usr/bin/mw sync (code=exited, status=0/SUCCESS)
   Main PID: 12127 (code=exited, status=0/SUCCESS)

Sep 24 19:08:02 t430s systemd[358]: Starting Mutt-wizard synchronisation service...
Sep 24 19:08:16 t430s mw[12209]: No new mail.
Sep 24 19:08:16 t430s systemd[358]: mwsync.service: Succeeded.
Sep 24 19:08:16 t430s systemd[358]: Finished Mutt-wizard synchronisation service.
```