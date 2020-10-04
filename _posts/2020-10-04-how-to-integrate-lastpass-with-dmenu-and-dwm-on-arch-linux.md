---
layout: post
title: How to integrate LastPass with dmenu and dwm on Arch Linux
description: Storing all of your passwords in LastPass is a great idea, but can
  be a bit of a pain when you need to authenticate in various places all the
  time. Here I will demonstrate how your LastPass vault can be accessed with
  dmenu with a dwm bindkey easily on Arch Linux.
---
Storing all of your passwords in LastPass is a great idea, but can be a bit of a pain when you need to authenticate in various places all the time. Here I will demonstrate how your LastPass vault can be accessed with dmenu with a dwm bindkey easily on Arch Linux.

## Prerequisites

1. Arch Linux (other distributions should work but instructions may differ)
2. [dwm](https://dwm.suckless.org), the suckless tiling window manager
3. [dmenu](https://tools.suckless.org/dmenu), a dynamic menu for dwm

## Install the LastPass command line interface
LastPass has a command line interface (CLI) for Linux which allows you to access your vault from the terminal. This will be our basis for accessing things from the backend but we won't need to use any commands to retrieve our passwords after everything is integrated with dmenu and dwm.

Luckily, Arch has a package for this in the standard repository.
```shell
sudo pacman -S lastpass-cli
```

Once that is installed, proceed with the next section.

## Install [cspeterson's dmenu integration](https://github.com/cspeterson/lastpass-dmenu)
If you have a sourced bin folder somewhere on your machine, you will want to download this shell script there and make it executable.

If you're unsure, `/usr/local/bin` is often a safe bet:

```shell
wget -O /path/to/your/bin/folder/lastpass-dmenu https://raw.githubusercontent.com/cspeterson/lastpass-dmenu/master/lastpass-dmenu
chmod +x /path/to/your/bin/folder/lastpass-dmenu 
```

Now close your terminal and open it up again and type `lastpass-dmenu`. You should see the help info for the tool which means it has been successfully installed!

## Authenticate the CLI with LastPass servers
Before we can access our vault, we need to log in with the CLI we installed before. To do this, enter
```shell
lpass login my-username@my.domain
```
and enter your master password when prompted. The tool will remember this for the future so you shouldn't have to keep logging in. If you are concerned about the security of this tool, [it's on GitHub so check out the source code!](https://github.com/lastpass/lastpass-cli)

## Test out the dmenu dropdown
We should probably test it's all working at this point. You can do this by opening a terminal and typing
```shell
lastpass-dmenu copy
```
and you should see a dmenu context drop down where you can begin typing the name of a site. When you select an option, it will copy the password to your clipboard for you to paste anywhere.

## Create a dwm binding for the dmenu dropdown
Now that it's working, we probably want to bind the dropdown to a hotkey with dwm. For my purpose, I've chosen `Mod + Shift + L`.

In your favourite code editor, open up your `dwm/config.h` file. If you do not know where it is, a common place to check is `/usr/local/src` but if you really can't find it, you can re-clone the source wherever you like.

We will want to add a line in the `keys` array so that it should look like this:
```c
static Key keys[] = {
    // ...
    // All the pre-defined key bindings
    // ...
    { MODKEY|ShiftMask, XK_l, spawn, SHCMD("lastpass-dmenu copy") }
}
```

The `|ShiftMask` part means we need to be holding shift, and the `XK_l` part means in combination with the L key. You can change this to whatever you like as long as it's not already in use. You can scan the config file to check if it is in use.

After saving the file, and while you are inside your `src/dwm` directory, run `sudo make` and `sudo make install` to rebuild dwm.

Now you will probably need to log out of your X session and come back in again to use the new dwm.

Now try hitting your key binding and you should see the LastPass dropdown dmenu context pop up! Give yourself a pat on the back, you're done.

Now it is much easier to search for and copy a password you need on the fly. No need to worry any more about that pesky browser extension when you're not even in your browser. It's as simple as hitting a key binding, typing the name of your stored credential, and pasting it in wherever you need it!