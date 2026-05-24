---
layout: project
title: Twilight Grove Online
description: A tiny MMO built with Godot 4.4 and Go, playable in the browser with over 150 players and a persistent world and economy.
start_date: 2024-12-01T00:00:00.000Z
finished: true
finish_date: 2025-02-28T00:00:00.000Z
external_link: https://twilightgrove.tbat.me
---

Twilight Grove Online was my obsession for the end of 2024 and the start of 2025. I had just, for the past few months, finished prototyping a toy Agar.io clone and 
writing and [extensive tutorial series on how I built it](https://www.tbat.me/projects/godot-golang-mmo-tutorial-series). I wanted a creative outlet, and I wanted 
to make something I thought would be a very comfortable fit for my new skills. It would also serve to be a sort of poster child for the tutorial series.

So, I made a tiny MUD that in about a month, and spent another month delivering small fixes and polish. It's web first, works great on mobile, but also has a desktop 
build. It only has one quest and two skills, and a few levels. But it has a persistent world and economy, and has over 150 players (only a couple have completed the 
quest, but it is a very grindy game).

Some fun facts about TGO:
- The levels (tilemap, entities) are designed in Godot and uploaded straight to the server as .tscn files, straight from the game itself when logged in as the special 
  admin user.
- All the database interactions are done with handwritten SQL queries.
- The server is authoritative, so all game logic is done in Go and the client is just a display and input layer.
- There's a profanity filter for usernames, but only a slur filter for the chat. I was able to download a list of these words from a GitHub repo and reference them in 
  the game's config file.
- The whole game server runs in a docker container with persistent storage on a PostgreSQL database.
- I got jumpscared by my friend who decided to log in as an undead and chase me around the spawn area while I was testing a new feature at 3am.

## Play the game

<center>
<iframe
  style="max-width: 1000px; width: 100%; aspect-ratio: 16 / 9; border: 0;"
  src="https://twilightgrove.tbat.me"
  title="Twilight Grove Online"
  loading="lazy"
  allow="fullscreen; gamepad; clipboard-read; clipboard-write"
  allowfullscreen
></iframe>
</center>

If your browser blocks the embed, you can play it directly at [twilightgrove.tbat.me](https://twilightgrove.tbat.me), or on [itch.io](https://saltytaro.itch.io/twilightgrove).

## Screenshots

{% include grid.html
  folder="projects/twilight-grove-online/grid"
  columns=2
  captions="Spawn area|The mines|Trading with Mud|The main quest start"
  alts="Twilight Grove town square with player UI|Twilight Grove inventory and item management UI|Twilight Grove quest and progression gameplay|Twilight Grove running cross-platform"
%}

## Resources

1. Play now: [twilightgrove.tbat.me](https://twilightgrove.tbat.me)
1. Source code: [github.com/tristanbatchler/TwilightGroveOnline](https://github.com/tristanbatchler/TwilightGroveOnline)
1. How I made it: [Godot + Golang MMO tutorial series](https://www.tbat.me/projects/godot-golang-mmo-tutorial-series)
