---
layout: project
title: Godot 4 + Golang MMO Tutorial Series
description: Another course intended for people with some programming experience. This free course will show you how to use modern frameworks and tools to create an authoritative websockets MMO server, and take advantage of the latest Godot 4.4 features to deploy your game to the cloud. Accompanying videos which follow these posts will also be published on YouTube.
start_date: 2024-11-08T00:00:00.000Z
finished: true
finish_date: 2022-11-30T00:00:00.000Z
---
This is a completely free, thirteen-part course intended for people with some programming experience. The parts will take you from setting up Go and Godot 4.4, all the way through to deployment. We will cover how to use modern frameworks and tools to create an authoritative websockets MMO server, all while taking advantage of the latest Godot features. Accompanying videos which follow these posts will also be published on YouTube.

## Blog posts
<ul>
  {% for post in site.posts reversed %}
    {% if post.project == "godot4golang" %}
        <li class="no-bullet">
        <h3><a href="{{ post.url }}">{{ post.title }}</a></h3>
        <p class="timestamp">{{ post.date | date: "%d %b %y" }}</p>
        <small>{{ post.description }}</small>
        </li>
    {% endif %}
  {% endfor %}
</ul>

## Community
If you have any questions or feedback, I'd love to hear from you! [Join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs.

## Thanks
Finally, I just wanted to say thank you so much for taking the time to read this. This is my biggest personal project to date, and hundreds upon hundreds of hours have gone into creating this. If these posts or videos have helped you out and you would like to give something back to me feel free to buy me a coffee (or a beer) 🙂
<center><a href="https://www.buymeacoffee.com/tristanbatchler" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-green.png" loading="lazy" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a></center>