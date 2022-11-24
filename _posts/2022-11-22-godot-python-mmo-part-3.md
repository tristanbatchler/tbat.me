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

## Fixing the login and register logic
Now that we've re-defined our short-term goals, we need more than just a User when we register, so change the registration logic so we do the following just after we save the user to the database, but just before we send the Ok packet back to the client.
```python
player_entity = models.Entity(name=username)
player_entity.save()
player_ientity = models.InstancedEntity(entity=player_entity, x=0, y=0)
player_ientity.save()
player = models.Actor(instanced_entity=player_ientity, user=user)
player.save()
```

Let's fix the login logic too. We need to retrieve more than just the user model, and we don't really care about holding on to the user model either. So let's do the following right after we confirm the supplied username and password matches, and right before we set the state to the `PLAY` state:
```python
user = models.User.objects.get(username=username)
self._actor = models.Actor.objects.get(user=user)

self.send_client(packet.OkPacket())
self.send_client(packet.ModelDataPacket(models.create_dict(self._actor)))
```

We will need to change the class member declaration in the constructor `self._user` to `self._actor: models.Actor = None`.

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

var server_position: Vector2
var actor_name: String
var velocity: Vector2 = Vector2.ZERO

var is_player: bool = false
var _player_target: Vector2

var speed: float = 70.0

func update(new_model: Dictionary):
    .update(new_model)
    
    var ientity = new_model["instanced_entity"]
    server_position = Vector2(float(ientity["x"]), float(ientity["y"]))
    actor_name = ientity["entity"]["name"]
    
    if label:
        label.text = actor_name

func _physics_process(delta):
    if not body:
        return
        
    var target: Vector2
    if is_player:
        target = _player_target
    elif server_position:
        target = server_position
        
    velocity = (target - body.position).normalized() * speed
    if (target - body.position).length() > 5:
        velocity = body.move_and_slide(velocity)
```

This script is a little more hefty as it needs to handle updates from the model and turn those into real, meaningful things about the actor, like velocity, position, name, etc.

We can see from the first line, this script extends from `model.gd`, so will have access to an `init` and `update` function. We are also overriding the `update` function, to additionally interpret some of the information in the model like the position and the actor's name.

In the physics process, we are updating the velocity according to the current position of the kinematic body and the server's reported position. For example, if the actor is at position `(1, 1)` and the server sends an updating saying it should be at `(5, 5)`, then we set the client's velocity to the vector with length 70, and direction pointing southeast. We keep the velocity here until eventually the client gets close enough to the target position, and then we set the velocity to zero.
If the actor is the client's player character (i.e. not another player), then we choose to follow the local player target position rather than obtain the target from the server. This is to ensure a smooth, responsive experience for the player with no latency. Of course, the server is still keeping track of the player's position, and later we will see how to correct if the client goes too off course or tries hacking the game.

## Player input
That being said, we do need a way to control our player and send our target position to the server, so add the following code to `Main.gd`:
```gdscript
func _input(event):
    if _player_actor and event.is_action_released("click"):
        var target = _player_actor.body.get_global_mouse_position()
        _player_actor._player_target = target
        var p: Packet = Packet.new("Target", [target.x, target.y])
        _network_client.send_packet(p)
```

This built-in `_input` function checks for input events each frame, so here we check if the player released the mouse button (or tap on mobile devices). Then we calculate the player's intended position target and sends it as a `Target` packet to the server. We haven't defined this packet yet, but we will soon. For now, just keep in mind the `Target` packet is meant to let the server know about our intended position we are moving to, so contains a target `x` and `y` coordinate as payloads.

We just need to add an input map for `"click"` to let Godot know we want to check for the left mouse button (which equates to a tap on mobile devices). In Godot at the top, click **Project** and then **Project Settings**. Click the **Input Map** tab, and type **click** in the **Action** input box. Click **Add**. Now scroll down to where it says **click** and click the plus button (**+**) beside it and select **Mouse Button**. Choose **All Devices** under **Device** (or mobile taps won't work), ensure **Left Button** is selected and click **Add**. Now you can close the Project Settings window.

## New packets!
Now that we have support for our game to display actors on the screen, we need to actually have a packet for sending models for the clients to process. We also need a way for the player to tell the server about its intended position target, so as previously mentioned, we need to add a Target packet.

Let's go to `server/packet.py` and add the new packets. Add these new action to our `Action` enum:
```python
ModelData = enum.auto()
Target = enum.auto()
```

Also add the packet definitions:
```python
class ModelDataPacket(Packet):
    def __init__(self, model_data: dict):
        super().__init__(Action.ModelData, model_data)

class TargetPacket(Packet):
    def __init__(self, t_x: float, t_y: float):
        super().__init__(Action.Target, t_x, t_y)
```

## Sending updates to the client
Now we are ready to actually send model updates to the client. 

Head on over the `protocol.py` and add some very simple new logic to the `PLAY` function:
```python
elif p.action == packet.Action.ModelData:
    self.send_client(p)

elif p.action == packet.Action.Target:
    self._player_target = p.payloads
```
When our protocol receives a ModelData packet, we simply relay it back to our client for Godot to process. If we receive a Target packet, we just store it for now and we'll come back to it later. We should also add this to the `__init__` constructor for the protocol just so we know what `_player_target` is:
```python
self._player_target: list[float] = None
```

So what happens when our client receives a ModelData packet? Currently nothing, because we are not checking for it in our main state machine. Let's fix that by opening `Main.gd` in Godot and adding this to our match statement for the `PLAY` function:
```gdscript
"ModelData":
    var model_data: Dictionary = p.payloads[0]
    _update_models(model_data)
```

The `_update_models` function will be a versatile function intended to update a model of any type passed in. Let's define this in `Main.gd` as well:
```gdscript
func _update_models(model_data: Dictionary):
    """
    Runs a function with signature 
    `_update_x(model_id: int, model_data: Dictionary)` where `x` is the name 
    of a model (e.g. `_update_actor`).
    """
    print("Received model data: " + JSON.print(model_data))
    var model_id: int = model_data["id"]
    var func_name: String = "_update_" + model_data["model_type"].to_lower()
    var f: FuncRef = funcref(self, func_name)
    f.call_func(model_id, model_data)
```

So if I called, for example, `_update_models(d)` where `d` is a dictionary containing fields `"id": 5` and `"model_type": "Actor"`, then another function called `update_actor(model_id, model_data)` gets called. Of course, we need to define these functions, but this reflective helper function will really improve the readability and structure of our code once we add many more models. This is another example of a function which may look like overkill for the purpose of our demo, but once the game is extended, it will be a lifesaver.

With that being said, let's define our `update_actor` function (also in `Main.gd`):
```gdscript
func _update_actor(model_id: int, model_data: Dictionary):
    # If this is an existing actor, just update them
    if model_id in _actors:
        _actors[model_id].update(model_data)

    # If this actor doesn't exist in the game yet, create them
    else:
        var new_actor
        
        if not _player_actor: 
            _player_actor = Actor.instance().init(model_data)
            _player_actor.is_player = true
            new_actor = _player_actor
        else:
            new_actor = Actor.instance().init(model_data)
        
        _actors[model_id] = new_actor
        add_child(new_actor)
```
So this is the function that gets called whenever we receive a ModelData packet containing an actor model's information. First, we check if we have the actor's model ID stored in our dictionary of actors (you will need to initialise this at the beginning of `Main.gd`: `var _actors: Dictionary = {}`). If we do already have this actor saved, we just call its update function.

If we don't have this actor's information stored already, first we need to determine whether it's the main player or not. We determine this by checking for a variable called `_player_actor`, which should initially be set to `null` (so add `var _player_actor = null` to the beginning of `Main.gd`). 

* If this variable **is** `null`, it means we haven't received our own player model yet, since that is the very first model we should ever receive from the server. In this case, we simply make a new `Actor` instance (you will need to import this at the top of the file: `const Actor = preload("res://Actor.tscn")`) and set the `is_player` flag accordingly.

* On the other hand, if we already have our player actor, then we know we are receiving new information about another actor so we just initialise it as such.

In either case, we add our new actor to our dictionary of known actors and add it to the game scene.

## Calculating and broadcasting positions
Now we have all the functionality we need to send targets, receive model updates, and display these in the game. The only thing we're missing is the ability for the server to update actor positions each tick and broadcast model updates back to the other clients! To do this though, we will need some maths. Create a new file in `server/` called `utils.py` which will serve as a place to throw all our random static functions in so they don't clutter our more important logic in other files:
```python
import math

def direction_to(current: list[float], target: list[float]) -> list[float]:
    "Return the vector with unit length pointing in the direction from current to target"
    if target == current:
        return [0, 0]
    
    n_x = target[0] - current[0]
    n_y = target[1] - current[1]

    length = math.dist(current, target)
    return [n_x / length, n_y / length]
```
This is a function which returns the direction pointing from one vector to another. The returned direction is also a vector with length one. This is useful for calculating the velocity of our actors in the next step.

Open `protocol.py` and add the following new function:
```python
def _update_position(self) -> bool:
    "Attempt to update the actor's position and return true only if the position was changed"
    if not self._player_target:
        return False
    pos = [self._actor.instanced_entity.x, self._actor.instanced_entity.y]

    now: float = time.time()
    delta_time: float = 1 / self.factory.tickrate
    if self._last_delta_time_checked:
        delta_time = now - self._last_delta_time_checked
    self._last_delta_time_checked = now

    # Use delta time to calculate distance to travel this time
    dist: float = 70 * delta_time
    
    # Early exit if we are already within an acceptable distance of the target
    if math.dist(pos, self._player_target) < dist:
        return False
    
    # Update our model if we're not already close enough to the target
    d_x, d_y = utils.direction_to(pos, self._player_target)
    self._actor.instanced_entity.x += d_x * dist
    self._actor.instanced_entity.y += d_y * dist

    return True
```

This is the function which updates the position of our player based on its target. Note we are using delta time here (you will need to add `self._last_delta_time_checked: float = None` in the constructor). We use delta time to ensure we are moving the correct amount each time this function is called, which is not every tick. Instead, we will call this function any time the packet queue is empty, so we don't inundate the server with too many calculations if it should be processing more important things. 

Some things to note:
    * The `70` in this file needs to match the player's speed variable in Godot's `Actor.gd` file otherwise the player and server will easily go out of sync.
    * We return `True` at the end to indicate we have actually moved the player. At other steps along the way, we return `False` if there was no movement possible/required. We can take advantage of this to decide whether or not we should re-broadcast our actor's model later.
    * This should be the **only** function using the `_last_delta_time_checked` variable. If for some reason you need other functions with delta time capabilities, you will need to create other variables.
    * We are not saving the actor's new position to the database yet. This will be the homework for this lesson we will discuss at the end 🙂


Finally, let's call this function. As discussed, we don't want to call this every tick, so let's put it at the end of the `tick` function like this:
```python
# To do when there are no packets to process
elif self._state == self.PLAY: 
    if self._update_position():
        self.broadcast(packet.ModelDataPacket(models.create_dict(self._actor)))
```

## Let's try it out!
Ok that should be it! It was a lot to get through, which seems to be a recurring theme with these lessons. I promise the next lesson will be more chill!

Run the server and connect a couple clients in Godot. You will want to register new accounts, because the old accounts won't have any actors associated with them. Login and start moving around and see if you can see the other actors updating on your screen too!

You should also try using the chat function again to ensure that's still working.

If any of this doesn't work for you, and you've checked the server output, Godot's debug log, and still can't figure it out, I would recommend downloading the [official source code for the game up to the end of this lesson](https://github.com/tristanbatchler/official-godot-python-mmo/archive/refs/tags/v0.3.zip) and comparing your own code against it. Also don't be shy to ask around by getting in touch in any of the ways mentioned at the end of this blog post. 

There are a couple things to note:
1. When you log out and log in again, you will always just start again in the top-right corner.
2. When a new player joins, you will see them pop up right away, but new players won't see you unless you move. In other words, if you are staying perfectly still when someone new joins, you will be invisible to them.
3. In addition to point 2, an invisible actor who suddenly moves will appear to come out of the top-left corner and move to their proper position.

## Homework
Your task is to fix problem #1 from above. A hint is to use [Django's model.save](https://docs.djangoproject.com/en/4.1/ref/models/instances/#saving-objects) function somewhere in this code!

In addition to this, think about *why* problems #2 and #3 might be occuring. You don't have to fix these (unless you really want to have a go!). It's good to note that, fixing #2 and #3 requires fixing #1 first. So next lesson we will go through the homework solutions and start with fixing problems #2 and #3.
## Conclusion
Thanks again for reading/watching! If you've managed to make it through this lesson, you should be seriously proud of yourself. This was a tough one, but as I mentioned earlier, the remainder of this series will be much more chilled out. We're nearly there, so stay tuned for more!

## Get in touch / connect with community
**If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video, email me (my contact information is in the footer below), or [join the Discord](https://discord.gg/6vN2re8T) to chat with me and other students!**