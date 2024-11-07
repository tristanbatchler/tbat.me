---
title: Godot 4 Golang MMO Introduction
description: We are embarking on another journey to create the ultimate MMO with Godot 4 and Golang!
redditurl: 
---

Two years ago, I started writing a series of blog posts about creating an "MMO" with Godot 3 and Python. I use the term "MMO" loosely to just mean an online multiplayer game with a central server, plus I think it helped the project get more attention.

There were a few issues with that project, though. The biggest and perhaps most unfortunate was its timing. I started the project in November 2022, and Godot 4 was released in March 2023. This meant that the project was already outdated by the time I finished writing it, and quickly an influx of commenters pointed out errors, bugs, and other issues to do with my code which discouraged me from continuing the project.

Over the last couple years, I have been messing around here and there, trying to address some of the issues with the original project, big and small. After lots of trial and error, and waiting for certain Godot 4 features to become available, I think I have landed on a good solution that I am excited to share with you all <small>*and hopefully it will be relevant for a little while longer this time*</small>.

## Radius Rumble
The game we will be creating in this series. 
![Radius Rumble](/assets/css/images/posts/2024/11/08/screenshot.png)
It is basically a clone of agar.io written in Godot 4.4 and Golang. Don't worry, the implementation will be general and flexible enough that you will have no problems adapting it to your own game ideas.

You can check out the final project [here](https://dev.godot4mmo2024.tbat.me:42523).

## Why Golang?
One of more common types of feedback I received on the original project was that Python was not a good choice for a server-side language. The reasons for having this opinion can often be debatable, and it is important to choose a language that you are comfortable with and that you can get the job done with. However, I can't deny that a language more intended for server-side programming and optimized for performance would be a better choice.

Golang fits the bill perfectly, while also being a decently simple language to learn and use. One of the best benefits I've seen over Python has been the static typing, which has helped me catch many bugs before they even happen, and really improves the coding experience because intellisense works so much better.

If you come from a Python background like me, it may take some getting used to, and you might fight the urge to write Pythonic code in Golang, but if you just embrace Golang's style and conventions, I think you'll find it to be a breath of fresh air and not too difficult to learn.

## Other changes
The two other glaring differences in this project is:
1. We will **not** be using an ORM for the database. The original project used Django, which I admit was completely overkill for the project and added a lot of unnecessary complexity. We will be using a simple SQLite database and [sqlc](https://sqlc.dev) to compile handwritten SQL queries into Go code. If you have never used SQL before, don't worry, our queries will be very simple, and I will explain them as we go.
2. We will be using [Protocol Buffers](https://protobuf.dev) for our packet serialization. This means we won't have to write our own JSON-based packet class like with did with the original project. The benefits of Protocol Buffers are that they are faster, smaller, and more efficient than JSON, and they are also language agnostic, so you could use them with other languages if you wanted to. Speaking of which, there is a fantastic Godot addon called [Godotbuf](https://github.com/oniksan/godobuf) which we will be taking advantage of to share our packet definitions between the server and client. We will also get the added benefit of being able to craft packets using generated functions in both Golang and GDScript, improving the development experience and reducing the chance of errors.

Overall, we should be able to create a more performant, more modern, and more maintainable project this time around.

## The plan
The series will be broken up into roughly three parts:
1. **Making a chatroom** aims to get us familiar with the tools we will be using and get a basic chatroom you can register, login, and send messages in. At first glance, it will seem to be one of the most over-engineered chatrooms you have ever seen, but it is disguised as a **solid** foundation for our game.
2. **Implementing the game** will obviously be the bulk of the project, where we will implement the game logic, networking, and polishing the client.
3. **Deployment** lifts our project off our local machine and onto the internet. I will show you best practices for deploying your server and launching the game to various platforms for the world to see.

Let's not waste any time and dive right in! See you in the next post where we will set up our project and get our server and client communicating with each other.

---

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.
