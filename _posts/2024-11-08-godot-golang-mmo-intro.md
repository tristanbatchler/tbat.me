---
title: Godot 4 Golang MMO Introduction
description: We are embarking on another journey to create the ultimate MMO with Godot 4 and Golang!
redditurl: 
---

Two years ago, I started writing a series of blog posts about creating an "MMO" with Godot 3 and Python. I use the term "MMO" loosely to just mean an online multiplayer game with a central server, plus I think it helped the project get more attention.

There were a few issues with that project, though. The biggest and perhaps most unfortunate was its timing. I started the project in November 2022, and Godot 4 was released in March 2023. This meant that the project was already outdated by the time I finished writing it, and quickly an influx of comment pointed out errors, bugs, and other issues which discouraged me from continuing the project.

Over the last couple years, I have been tinkering on and off, trying to address some of the issues with the original project, big and small. After lots of trial and error, and waiting for certain Godot 4 features to become available, I think I have landed on a good solution that I am excited to share with you all <small>*and hopefully it will be relevant for a little while longer this time*</small>.

## Introducing "Radius Rumble"
As our example project, we will be making clone of [agar.io](https://agar.io) written in Godot 4.4 and Golang.
![Radius Rumble](/assets/css/images/posts/2024/11/08/screenshot.png)
Don't worry, the implementation will be general and flexible enough that you will have no problems adapting it to your own game ideas.

You can check out the final project [here](https://dev.godot4mmo2024.tbat.me:42523).

## Why Golang?
One of more common types of feedback I received on the original project was that Python was not a good choice for a server-side language. The reasons for having this opinion can often be debatable, and I still stand by the opinion it's important to choose a language that you are comfortable with and can get the job done. However, I can't deny that a language more intended for server-side programming and optimized for performance would be a better choice, even if it's not as accessible as Python.

Golang fits the bill perfectly, while also being a decently simple language to learn and use. One of the best benefits I've seen over Python has been the static typing, which has helped me catch many bugs before they even happen, and really improves the coding experience because intellisense works so much better.

If you come from a Python background like me, it may take some getting used to, and you might have to fight the urge to write Pythonic code in Golang. But if you just embrace Golang's philosophy, I think you'll find it to be a breath of fresh air, while not being all that difficult to learn.

## Other changes
The two other glaring differences in this project is:
1. We will **not** be using an ORM for the database. The original project used Django, which I admit was completely overkill for the project and added a lot of unnecessary complexity. We will be using a simple SQLite database and [sqlc](https://sqlc.dev) to compile handwritten SQL queries into Go code. If you have never used SQL before, don't worry, our queries will be very simple, and I will explain them as we go.
2. We will be using [Protocol Buffers](https://protobuf.dev) for our packet serialization. This means we won't have to write our own JSON-based packet class like we did with the original project. The benefits of Protocol Buffers are that they are faster and smaller than JSON, and they are also widely supported in different languages. Speaking of which, there is a fantastic Godot addon called [Godotbuf](https://github.com/oniksan/godobuf) which we will be taking full advantage of to share our packet definitions between the server and client. This way, we get the awesome bonus of being able to craft packets using generated functions in both Golang and GDScript, improving the development experience and reducing the chance of errors.

Overall, we should be able to create a more performant, more modern, and more maintainable project this time around.

## The plan
The series will be broken up into roughly three parts:
1. **Making a chatroom** will get us familiar with the tools we will be using and get a basic app you can register, login, and send messages in. At first glance, it will seem to be the most over-engineered chatroom you have ever seen, but it disguises as a **solid** foundation for our game.
2. **Implementing the game** will obviously be the bulk of the project, where we will implement the game logic and polishing the client. Here we will discuss techniques for handling game state which I believe is invaluable for any online multiplayer game.
3. **Deploying to the cloud** lifts our project off our local machine and into the hands of players from across the world. We will discuss security, platforms, and other nuances to consider when publishing your game.

Let's not waste any time and dive right in! See you in [the next post](/2024/11/09/godot-golang-mmo-part-1) where we will set up our project and get our server and client communicating with each other.

---

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.
