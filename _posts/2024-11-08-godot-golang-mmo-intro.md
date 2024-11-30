---
title: "§00 Build a Modern Godot 4 MMO with Golang"
description: "Learn how to create an online MMO using the latest tools, Godot 4 and Golang. This series introduces a practical approach to building a scalable, high-performance game while remaining accessible to developers of all skill levels."
redditurl: 
---

Two years ago, I set out to create an MMO using Godot 3 and Python. Now, with Godot 4 here and valuable feedback from that first attempt, I’m excited to introduce a new and improved approach using Golang. I use the term "MMO" loosely to mean an online multiplayer game with a central server—but the term has certainly helped garner attention!

Unfortunately, timing was a challenge for the original project. I started in late 2022, just months before Godot 4's release in March 2023. By the time the series was finished, the outdated Godot 3 code led to bugs and feedback that made the project difficult to maintain.

Over the last couple of years, I have been tinkering, trying to address some issues with the original project, big and small. After lots of trial and error, and waiting for certain Godot 4 features to become available, I've landed on a great structure that I am excited to share with you all <small>*and, hopefully it will be relevant for a little while longer this time*</small>.

## Introducing "Radius Rumble"
For this series, we’ll develop Radius Rumble, a Godot-4-and-Golang-powered clone of the popular game [agar.io](https://agar.io).
![Radius Rumble](/assets/css/images/posts/2024/11/08/screenshot.png)
Don't worry, the implementation will be general and flexible enough that you will have no problems adapting it to your own game ideas.

You can check out the final project [here](https://radius.rumble.tbat.me).

## Why Golang?
Some of the most common feedback I received on the original project was that Python is not a good choice for a server-side language. The reasons for having this opinion can often be debatable, and I still stand by the opinion it's important to choose a language that you are comfortable with and can get the job done. However, I can't deny that a language more intended for server-side programming and optimized for performance would be a better choice, even if it's not as accessible as Python.

Golang is a great fit: it’s fast, simple to learn, and offers a major advantage over Python with its static typing. Static typing has helped me catch many bugs early on and has significantly improved the coding experience, thanks to more effective IntelliSense.

If you come from a Python background like me, it may take some getting used to, and you might have to fight the urge to write Pythonic code in Golang. But if you just embrace Golang's philosophy, I think you'll find it to be surprisingly refreshing, while not being all that difficult to learn.

## Other key changes in this project
The two other glaring differences in this project is:
1. We will **not** be using an ORM for the database. The original project used Django, which I admit was completely overkill for the project and added a lot of unnecessary complexity. Instead, we'll use a simple SQLite database and [sqlc](https://sqlc.dev) to compile handwritten SQL queries into Go code. If you have never used SQL before, don't worry—our queries will be very simple, and I'll walk you through each one.
2. We will be using [Protocol Buffers](https://protobuf.dev) for our packet serialization. This means we won't have to write our own JSON-based packet class like we did with the original project. Protocol Buffers are faster and smaller than JSON, and they are widely supported across all technologies. Speaking of which, there is a fantastic Godot add-on called [Godotbuf](https://github.com/oniksan/godobuf) which we will be taking full advantage of to share our packet definitions between the server and client. This way, we get the awesome bonus of being able to craft packets using generated functions in both Golang and GDScript, improving the development experience and reducing the chance of errors.

Overall, we can create a more performant, modern, and maintainable project this time around.

## The plan
The series will be broken up into roughly three parts:
1. **Make a chatroom:** In the first few parts, we'll start small but important by building a chatroom, giving you hands-on experience with the tools we will be using. At first glance, it will seem to be the most over-engineered chatroom you have ever seen, but it will disguise itself as a **solid** foundation for our game.
2. **Implement game logic:** The next few parts will bring our MMO to life with real-time game state management techniques and opportunities to really polish the look and feel.
3. **Deploy to the cloud:** lifts our project off our local machine and into the hands of players from across the world. We will discuss security, platforms, and other nuances to consider when publishing your game.

Let's dive into this journey together! Head to <strong><a href="/2024/11/09/godot-golang-mmo-part-1" class="sparkle-less">the next post</a></strong> to get started building your server and client.

---

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.
