---
title: Godot Python MMO Part 3
description: Let's turn our chatroom into a proper game by introducing actors who can move about!
redditurl: 
---

Welcome back to yet another lesson! In the [previous lesson](/2022/11/21/godot-python-mmo-part-2.html), we finished setting up authentication for our chatroom, thus completing our short-term goal.

In this lesson, we will really kick it up a notch by attaching the notion of position and movement to our players, making this feel more like a game.

[If you prefer, you can view this lesson on YouTube](https://www.youtube.com/playlist?list=PLA1tuaTAYPbHz8PvTWpFYGag0L6AdYgLH).

I highly recommend you go through the [first](/2022/11/20/godot-python-mmo-part-1.html) and [second](/2022/11/21/godot-python-mmo-part-2.html) parts, if you haven't already. If do you want to start here without viewing the previous lessons, however, you can visit [the **Releases** section of the official GitHub repository](https://github.com/tristanbatchler/official-godot-python-mmo/releases), and download the **End of lesson 2** code by expanding **Assets** and downloading [Source code (zip)](https://github.com/tristanbatchler/official-godot-python-mmo/archive/refs/tags/v0.2.zip).

## A sneak peak
Here's a quick look at what we'll be finishing up by the end of this lesson:
![A demo of what's to come...](/assets/css/images/posts/2022/11/22/godot-python-mmo-part-3/demo.gif)

## Database design
We're going to want to store information about not only the user, but also their associated **actor**. 

An actor has a user, but it also has a position and a name, etc.

Here's the most agreeable structure for further down the track when you might want to add items to your game as well as actors, or abstract entities:

* Actor
    * User
        * `Username`
        * `Password`
    * InstancedEntity
        * `x`
        * `y`
        * Entity
            * `Name`

The way to read this is every actor has a user and an instanced entity. Every instanced entity has an entity.

If we wanted to extend this later on, we could create something like a loot chest, which needs a position and a name but doesn't need a user.
* Container
    * InstancedEntity
        * `x`
        * `y`
        * Entity
            * `Name`

Loot chests require loot, of course. But this loot might not exist properly in the world so doesn't need a position:
* Item
    * `Value`
    * Container
        * ...
    * Entity
        *`Name`

So that's just a few examples of how you might want to extend the database, but for now we will just be adding support for actors. This means adding some new models.

## Adding some new models
Let's add models for our actor in `server/models.py`, as we discussed, we start with an actor which has a user and an instanced entity:
```python
class Actor(models.Model):
    user = models.OneToOneField(User, on_delete=models.RESTRICT)
    instanced_entity = models.OneToOneField(InstancedEntity, on_delete=models.RESTRICT)
```

Then we need to define instanced entities which have a position and an entity:
```python
class InstancedEntity(models.Model):
    x = models.FloatField()
    y = models.FloatField()
    entity = models.ForeignKey(Entity, on_delete=models.DO_NOTHING)
```

And finally entities:
```python
class Entity(models.Model):
    name = models.CharField(max_length=100)
```

## Our first database migration
Let's run our first database migration! It's very easy with our `manage.py` script.

Simply run the following commands:
```powershell
python manage.py makemigrations
python manage.py migrate
```

You should get the following output signifying the database has been updated to include some new tables:
```
(venv) python manage.py makemigrations
Migrations for 'server':
  migrations\0002_entity_instancedentity_actor.py
    - Create model Entity
    - Create model InstancedEntity
    - Create model Actor

(venv) python manage.py migrate
Operations to perform:
  Apply all migrations: server
Running migrations:
  Applying server.0002_entity_instancedentity_actor... OK
```

## How do we send all this data?
As our models grow in complexity, you might wonder how is best to send all this data to the client.

The answer, I've found, is to pack a model and all its nested foreign relationships up into a big dictionary and send it over the network as a "Model Packet" (later on, we will discuss inefficiencies of this approach and a very neat trick for dealing with that).

In order to convert a model into dictionary, we need a function. Let's define one now at the top of `models.py`:
```python
from django.forms import model_to_dict

def create_dict(model: models.Model) -> dict:
    """
    Recursively creates a dictionary based on the supplied model and all its foreign relationships.
    """
    d: dict = model_to_dict(model)
    model_type: type = type(model)
    d["model_type"] = model_type.__name__

    if model_type == Actor:
        d["instanced_entity"] = create_dict(model.instanced_entity)
        # Purposefully don't include user information here.
    
    return d
```

You can see we are leveraging one of Django's included `model_to_dict` functions, but that unfortunately won't recursively dive into each foreign relationship and nest its data into our dictionary for us.

For that, we need to have an `if` statement for each "composite" model in our game (e.g. `Actor` is a "composite" model because it is made up of an `InstancedEntity` and a `User`). On the other hand, `User` and `Entity` are examples of "atomic" models which don't depend on anything else.

So basically this function works by first saving the atomic models to the overall dictionary, and then it goes through each composite type and recursively adds those to the main dictionary.

Note we don't touch `User` information here because we don't want to send usernames or passwords over the network (except initially from the client to the server).

An example of an actor dictionary would be
```json
{
    "model_type": "actor",
    "instanced_entity": {
        "model_type": "instanced_entity",
        "x": 5.5,
        "y": 10.0,
        "entity": {
            "model_type": "entity",
            "name": "John the destroyer"
        }
    }
}
```

## A new actor scene in Godot
We should be getting more comfortable in Godot by now, so I won't provide as explicit instructions on how to do basic things from now on. If you do get stuck, though, remember you can always skip to the relevant section of the [YouTube video]().

In Godot, create a new scene called **Actor.tscn**. To this scene, add a Node2D root, rename it to **Actor**, and add the following other nodes until your scene tree looks like this:
* Actor
    * KinematicBody2D
        * Label
        * Sprite

You may get a warning about not having a collision shape yet, but don't worry about that for now. We will bring collisions into the game later down the track.

Select your **Sprite** node and choose a texture from the right-hand side inspector panel. I chose the default **icon.png** that came with the project to start, but later I will show you have to make beautiful animated sprites.

Attach a new script to your root node, unsurprisingly called `Actor.gd`. Clear out the default code but we will not be writing new code here just yet.

We want our actors to inherit from a more fundamental **Model** class, so we need to create that first.

Create a new script called `model.gd` (not attached to anything), and paste the following code inside:
```gdscript
extends Node

var data: Dictionary = {}

func init(initial_data: Dictionary):
	update(initial_data)
	return self

func update(new_model: Dictionary):
	data = new_model
```
This is just setting up the functionality for receiving new models and updating them in Godot. Eventually, the `update` function will be changed a bit when we make it a bit more efficient, but for now it's quite simple.

Now we can code our `Actor.gd` script:
```gdscript
extends "res://model.gd"

onready var body: KinematicBody2D = get_node("KinematicBody2D")
onready var label: Label = get_node("KinematicBody2D/Label")
onready var sprite: Sprite = get_node("KinematicBody2D/Sprite")

const OOB = Vector2(-1, -1)

var server_position: Vector2 = OOB
var actor_name: String = ""
var velocity: Vector2 = Vector2.ZERO

func update(new_model: Dictionary):
	.update(new_model)
	
	var ientity = new_model["instanced_entity"]
	server_position = Vector2(float(ientity["x"]), float(ientity["y"]))
	actor_name = ientity["entity"]["name"]
	
	if label:
		label.text = actor_name
		
	if body and not server_position == OOB:
		body.position = server_position

func _physics_process(delta):
	if server_position != OOB:
		velocity = body.position.direction_to(server_position) * 70
		
		if body.position.distance_squared_to(server_position) <= 25:
			velocity = Vector2.ZERO
	
	body.position += velocity * delta
```

This script is a little more hefty as it needs to handle updates from the model and turn those into real, meaningful things about the actor, like velocity, position, name, etc.

We can see from the first line, this script extends from `model.gd`, so will have access to an `init` and `update` function. We are also overriding the `update` function, to additionally interpret some of the information in the model like the position and the actor's name.

In the physics process, we are updating the velocity according to the current position of the kinematic body and the server's reported position. For example, if the actor is at position `(1, 1)` and the server sends an updating saying it should be at `(5, 5)`, then we set the client's velocity to the vector with length 70, and direction pointing southeast. We keep the velocity here until eventually the client gets close enough to the target position, and then we set the velocity to zero.

It's also good to note that, in the beginning, we don't know the initial position of the target, so we don't want to set the velocity to "travel" there, we just want to set the position outright. This is why we initially have the server position as `OOB` (out-of-bounds) until the first update can occur and then we can set the initial body position.

## Adding a new model packet
Now that we have support for our game to display actors on the screen, we need to actually have a packet for sending models for the clients to process.

Let's go to `server/packet.py` and add a new packet. Add a new action to our `Action` enum:
```python
ModelData = enum.auto()
```

Also add the packet definition:
```python
class ModelData(Packet):
    def __init__(self, model_data: dict):
        super().__init__(Action.ModelData, model_data)
```

## Sending updates to the client
Now we are ready to actually send the model updates to the client. 

Head on over the `protocol.py` and add some new logic to the `PLAY` function, identical to the logic for the chat packet:
```python
elif p.action == packet.Action.ModelData:
    if sender == self:
        self.broadcast(p, exclude_self=True)
    else:
        self.send_client(p)
```

## Putting it all together

## Deltas

## Conclusion


## Get in touch / connect with community
**If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video, email me (my contact information is in the footer below), or [join the Discord](https://discord.gg/6vN2re8T) to chat with me and other students!**