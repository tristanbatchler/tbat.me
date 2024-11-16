---
title: §07 Adding Objectives + Polishing the Godot 4 Go MMO
description: So we have a basic functioning MMO, but it's not very fun and movement is a bit janky. Let's make things a bit easier on the eyes and keep players engaged with objectives.
redditurl: 
---

Nice to see you again! In [the last post](/2024/11/11/godot-golang-mmo-part-6), we finally got some gameplay down, and we left off in a pretty good spot. We have a basic space where players can move around and spot each other, but it is very unpolished, and I wouldn't really call it a "game" since it lacks objectives! Let's fix that today by adding some spores to collect and let the player grow. We will also be making the movement more fluid and restoring the chat functionality we kinda lost in the last post. Let's get right into it!

## Bringing back the chat
Low-hanging fruit, let's quickly restore our chatroom logic we got rid of in <a href="/2024/11/10/godot-golang-mmo-part-5#get-rid-of-chat-handling" target="_blank">§05</a>. All we need to do here is add a new case to the `HandleMessage` method in our `InGame` state handler:

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    // ...
    case *packets.Packet_Chat:
        g.handleChat(senderId, message)
    // ...
    }
}

func (g *InGame) handleChat(senderId uint64, message *packets.Packet_Chat) {
    if senderId == g.client.Id() {
        g.client.Broadcast(message)
    } else {
        g.client.SocketSendAs(message, senderId)
    }
}
```

Note the `handleChat` method is just a repeat of the code we had to remove in §05, which we originally wrote in <a href="/2024/11/09/godot-golang-mmo-part-3#add-chat-logic" target="_blank">§03</a>.

So now, when two players are in the same room, they can chat with each other!
![Chatting](/assets/css/images/posts/2024/11/14/chatting.png)

## Improving chat on the client

While we're talking about chat, we have the ability to access the player's name from the sender ID, so why don't we display the player's name in the chat? Let's do that in the script for the `InGame` state:

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _handle_chat_msg(sender_id: int, chat_msg: packets.ChatMessage) -> void:
    if sender_id in _players:
        var actor := _players[sender_id]
        _log.chat(actor.actor_name, chat_msg.get_msg())
```

![I owe Adam Sandler $20 please send help](/assets/css/images/posts/2024/11/14/chatting-names.png)

Now that looks a lot better!

## Smoothing out the movement

The movement in our game is pretty jerky, because we are just directly setting the player's positions whenever the server sends an update. We can solve this by giving every actor a velocity based on the speed and direction the server sent us at each sync. This way, even though we are getting limited information from the server, we can still reconstruct what the player's movement should look like.

Luckily, this isn't difficult because we already have `direction` and `speed` fields in our `PlayerMessage` protocol buffer, and we are already using a `velocity` variable in our Actor Godot script to update the player's position. All we need to do is set the velocity in the `_handle_player_msg` method in the `InGame` state script:

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _handle_player_msg(sender_id: int, player_msg: packets.PlayerMessage) -> void:
    # ...
    if actor_id not in _players:
        # ...
    else:
        # ...

        var direction := player_msg.get_direction()
        actor.velocity = speed * Vector2.from_angle(direction)
```

And that's it! Now, the movement of other players should look much smoother.
<video controls>
  <source src="/assets/css/images/posts/2024/11/14/smooth-movement.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

## Adding objectives

Now that our game is a tiny bit more acceptable in terms of polish, let's go ahead and add a new feature: spores. These spores will spawn randomly around the map and players can collect them to grow. For now, let's just get these things into the game and worry about the growing part later.

### Defining the spores

First, let's add a new message type to our protocol buffers:

```directory
/shared/packets.proto
```

```proto
message SporeMessage { uint64 id = 1; double x = 2; double y = 3; double radius = 4; }

message Packet {
    // ...
    oneof msg { 
        // ...
        SporeMessage spore = 10;
    }
}
```

Now, add a helper function to easily make a new `SporeMessage`:

```directory
/server/pkg/packets/util.go
```

```go
func NewSpore(id uint64, spore *objects.Spore) Msg {
    return &Packet_Spore{
        Spore: &SporeMessage{
            Id:     id,
            X:      spore.X,
            Y:      spore.Y,
            Radius: spore.Radius,
        },
    }
}
```

This will give an error because we haven't defined the `objects.Spore` struct yet, so let's do that now:

```directory
/server/internal/server/objects/gameObjects.go
```

```go
type Spore struct {
    X      float64
    Y      float64
    Radius float64
}
```

That should solve the error in our `util.go` file!

All of this is pretty standard stuff, so let's make sure we recompile our proto file to generate the new Go and GDScript code and move on to add a shared collection of spores to the hub's `SharedGameObjects` struct:

```directory
/server/internal/server/hub.go
```

```go
type SharedGameObjects struct {
    // ...
    Spores *objects.SharedCollection[*objects.Spore]
}
```

We'll need to modify the `NewHub` function to initialize the spores collection:

```directory
/server/internal/server/hub.go
```

```go
func NewHub() *Hub {
    // ...
    hub := &Hub{
        // ...
        SharedGameObjects: &SharedGameObjects{
            // ...
            Spores:  objects.NewSharedCollection[*objects.Spore](),
        },
    }
    // ...
}
```

### Spawning spores

Now, to the interesting stuff: {% include highlight.html anchor="spawning-stuff" text="let's add a new file to our <code>objects</code> package to handle spawning game objects" %}, since we will need to have the ability to place spores and players around the map, with some eventual logic to stop them from spawning on top of each other, for example. But for now, we'll just have a simple `SpawnCoords` function to give a random position on the map:

```directory
/server/internal/server/objects/spawn.go
```

```go
package objects

import (
    "math/rand/v2"
)

func SpawnCoords() (float64, float64) {
    var bound float64 = 3000
    return rand.Float64() * bound, rand.Float64() * bound
}
```

It might seem overkill to have a whole file for this, but we will be adding more spawn logic in the future, so it's good to have a dedicated place for it.

Now, let's add a method to the `Hub` to spawn a spore:

```directory
/server/internal/server/hub.go
```

```go
import (
    // ...
    "math/rand/v2"
    // ...
)

func (h *Hub) newSpore() *objects.Spore {
    sporeRadius := max(rand.NormFloat64()*3+10, 5)
    x, y := objects.SpawnCoords()
    return &objects.Spore{X: x, Y: y, Radius: sporeRadius}
}
```

Finally, let's add a constant for the maximum number of spores we want in our game, and spawn them in at the top of the `Hub`'s `Run` method, right after we create the database but before we start listening on the channels:

```directory
/server/internal/server/hub.go
```

```go
const MaxSpores int = 1000

// ...

func (h *Hub) Run() {
    // ...
    log.Println("Placing spores...")
    for i := 0; i < MaxSpores; i++ {
        h.SharedGameObjects.Spores.Add(h.newSpore())
    }
    // ...
}
```

If everything is working correctly, we should be able to run our server and play the game, same as before, but we won't see any spores until we actually send the messages to the client and render them. Let's do that now!

### Sending the spores to the client

A good place to send the spores to the client would be the `OnEnter` method of the `InGame` state, since it'll be one of the first things the client will want to know about when they enter the game:

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) OnEnter() {
    // ...
    // Send the spores to the client in the background
    go func() {
        g.client.SharedGameObjects().Spores.ForEach(func(sporeId uint64, spore *objects.Spore) {
            time.Sleep(5 * time.Millisecond)
            g.client.SocketSend(packets.NewSpore(sporeId, spore))
        })
    }()
}
```

This section of code simply *starts* sending spores to the client in the background, so the client can start rendering them as soon as possible. We also added a small delay between each spore to avoid flooding the send channel and causing packets to be dropped. The client interfacer won't block on this goroutine, so it can continue to process other messages while the spores are being sent.

This basically just allows the client to get into the game without needing to wait for all the spores to be sent, but there is a drawback that the player will see the spores pop in one by one. This should take less than a few seconds though, so may not be a dealbreaker. Another approach would be to send all the spores in batches, but that would require a bit more work. I will leave a section at the end of this post with instructions on how to do that if you're interested, but for now, let's move on.

### Rendering the spores
Now that we're sending the spores to the client, we are all good to go ahead and start processing them in Godot. But first, we'll need to add a new object to our game to represent these spores.

Create a new folder at `res://objects/spore/` and add a new scene called `spore.tscn` with an **Area2D** root node called `Spore`.
![Spore scene](/assets/css/images/posts/2024/11/14/spore-scene.png)

Now, add a **CollisionShape2D** child node to the `Spore` node and set its shape to a **CircleShape2D**. Similarly to the actor, we'll want to ensure the **Local to Scene** property is checked in the **CircleShape2D**. The rationale for this has been covered in <a href="/2024/11/11/godot-golang-mmo-part-6#local-to-scene-note" target="_blank">the last post</a>.

Now, let's add a new script to the `Spore` node called `spore.gd`:

```directory
/client/objects/spore/spore.gd
```

```gdscript
extends Area2D

const Scene := preload("res://objects/spore/spore.tscn")
const Spore := preload("res://objects/spore/spore.gd")

var spore_id: int
var x: float
var y: float
var radius: float
var color: Color

@onready var _collision_shape := $CollisionShape2D.shape as CircleShape2D

static func instantiate(spore_id: int, x: float, y: float, radius: float) -> Spore:
    var spore := Scene.instantiate() as Spore
    spore.spore_id = spore_id
    spore.x = x
    spore.y = y
    spore.radius = radius
    
    return spore

func _ready() -> void:
    position.x = x
    position.y = y
    _collision_shape.radius = radius

    color = Color.from_hsv(randf(), 1, 1, 1)

func _draw() -> void:
    draw_circle(Vector2.ZERO, radius, color)
```

This script is pretty similar to the `Actor` script, but we have a few differences. We have a `color` variable that we set to a random color when the spore is created, and we draw the spore as a circle with that color. We also have a `spore_id` variable that we set when we instantiate the spore, which we will use to identify the spore when we need to update it.

{% include highlight.html anchor="handle-spores" text="Speaking of which, let's keep a map of spores in the <code>InGame</code> state script, so we can hold onto them and update them when we receive new information about them:" %}

```directory
/client/states/ingame/ingame.gd
```

```gdscript
const Spore := preload("res://objects/spore/spore.gd")

# ...

var _spores: Dictionary[int, Spore]

# ...

func _on_ws_packet_received(packet: packets.Packet) -> void:
    # ...
    elif packet.has_spore():
        _handle_spore_msg(sender_id, packet.get_spore())

# ...

func _handle_spore_msg(sender_id: int, spore_msg: packets.SporeMessage) -> void:
    var spore_id := spore_msg.get_id()
    var x := spore_msg.get_x()
    var y := spore_msg.get_y()
    var radius := spore_msg.get_radius()

    if spore_id not in _spores:
        var spore := Spore.instantiate(spore_id, x, y, radius)
        _world.add_child(spore)
        _spores[spore_id] = spore
```

All of this should be pretty straight forward now that we've seen pretty much the same thing for actors. In this case, we don't need to worry about updating the spores since they are static objects, but we will need be able to remove them later on when the server tells us to, which is why we're keeping a reference to them in the `_spores` dictionary. Aside from that, everything should be self-explanatory, so I won't go into more detail.
<video controls>
  <source src="/assets/css/images/posts/2024/11/14/spores.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

### Eating the spores
So we have spores in the game, but they don't do anything yet. Let's make it so that when a player collides with a spore, the spore is removed from the game and the player's size increases. We'll start by adding a new message type to our protocol buffers:

```directory
/shared/packets.proto
```

```proto
message SporeConsumedMessage { uint64 spore_id = 1; }

message Packet {
    // ...
    oneof msg { 
        // ...
        SporeConsumedMessage spore_consumed = 11;
    }
}
```

<small>*You should be used to recompiling the proto file by now, so this might be the last time I mention it: don't forget to compile your Golang and GDScript code using `protoc` or Godobuf! Instructions for the Golang code compilation can be found in <a href="/2024/11/09/godot-golang-mmo-part-1#protoc-usage" target="_blank">§01</a>, and the Godobuf instructions are in <a href="/2024/11/09/godot-golang-mmo-part-1#godobuf-usage" target="_blank">the same post, a bit further down</a>.*</small>

Now, since both the actor and spore are **Area2D** nodes, we can use the `body_entered` signal to detect when they collide. It will be much more efficient to listen to the player actor's signal, rather than to every spore in the game, so let's connect this signal up to a handler in the `InGame` state script, just after we instantiate the player. 

But that section of the code is getting a bit long, so let's move it to its own method called `_add_actor`. The update logic can also be extracted into its own method called `_update_actor`, so let's do that as well:

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _handle_player_msg(sender_id: int, player_msg: packets.PlayerMessage) -> void:
    # ...
    if actor_id not in _players:
        _add_actor(actor_id, actor_name, x, y, radius, speed, is_player)
    else:
        var direction := player_msg.get_direction()
		_update_actor(actor_id, x, y, direction, speed, radius, is_player)

func _add_actor(actor_id: int, actor_name: String, x: float, y: float, radius: float, speed: float, is_player: bool) -> void:
    var actor := Actor.instantiate(actor_id, actor_name, x, y, radius, speed, is_player)
    _world.add_child(actor)
    _players[actor_id] = actor
    
    if is_player:
        actor.area_entered.connect(_on_player_area_entered)

func _update_actor(actor_id: int, x: float, y: float, direction: float, speed: float, radius: float, is_player: bool) -> void:
	var actor := _players[actor_id]
	actor.radius = radius

	if actor.position.distance_squared_to(Vector2(x, y)) > 100:
		actor.position.x = x
		actor.position.y = y
	
	if not is_player:
		actor.velocity = Vector2.from_angle(direction) * speed
```

We are also taking the opportunity to update the player's radius when they receive a new message from the server, because the information is there: we might as well use it! Also, we will only update the actor's position to the new position if there is a distance of more than 10 pixels between them. This is useful to give the player a bit of leeway when moving around, rather than feeling like they are always being dragged around by the server. We never update the player's velocity either, because the experience is never going to feel good that way.

Now, of course we need to add the `_on_player_area_entered` method to handle the collision:

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _on_player_area_entered(area: Area2D) -> void:
    if area is Spore:
        _consume_spore(area as Spore)
```

{% include highlight.html anchor="consuming-spores" text="We are splitting this off into another method called <code>_consume_spore</code>, because we will need to also handle the case where the player collides with another actor (but we won't be doing that in this post). To keep things clean, let's move on to implementing the <code>_consume_spore</code> method:" %}

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _consume_spore(spore: Spore) -> void:
    var packet := packets.Packet.new()
    var spore_consumed_msg := packet.new_spore_consumed()
    spore_consumed_msg.set_spore_id(spore.spore_id)
    WS.send(packet)
    _remove_spore(spore)
```

Here we are sending the new message type we just created to the server, and then removing the spore from the game. Let's add the `_remove_spore` method now, as it needs to do a bit of cleanup, and we will be re-using it later when we receive a message from the server to remove a spore:

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _remove_spore(spore: Spore) -> void:
    _spores.erase(spore.spore_id)
    spore.queue_free()
```

Well, that should be it! Now, when a player collides with a spore, the spore will be removed from the game and the server will be notified. The player's size will not increase yet, but we will be adding that in the next post.

Let's see if it works by adding a quick debug message to the server's `InGame` state handler `HandleMessage` method:

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    // ...
    case *packets.Packet_SporeConsumed:
        g.logger.Printf("Spore %d consumed by client %d", message.SporeConsumed.SporeId, senderId)
    }
}
```

Now restart the server and client, and you should see something like this:
<video controls>
  <source src="/assets/css/images/posts/2024/11/14/consume-spore.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

```plaintext
2024/11/15 18:04:00 Starting server on :8080
2024/11/15 18:04:00 Placing spores...
2024/11/15 18:04:00 Awaiting client registrations
2024/11/15 18:04:06 New client connected from [::1]:64729
Client 1: 2024/11/15 18:04:06 Switching from state None to Connected
Client 1 [Connected]: 2024/11/15 18:04:15 User saltytaro logged in successfully
Client 1: 2024/11/15 18:04:15 Switching from state Connected to InGame
Client 1 [InGame]: 2024/11/15 18:04:15 Adding player saltytaro to the shared collection
Client 1 [InGame]: 2024/11/15 18:04:28 Spore 329 consumed by client 1
Client 1 [InGame]: 2024/11/15 18:04:38 Spore 576 consumed by client 1
Client 1 [InGame]: 2024/11/15 18:04:39 Spore 429 consumed by client 1
Client 1 [InGame]: 2024/11/15 18:04:40 Spore 536 consumed by client 1
```

If you see the debug messages in the server's console, then you know it's working! We will be handling these messages next time, where we will perform some server-side validation checks and update the player's size when they consume a spore. But for now, let's wrap up this post.

## Conclusion

I hope you are seeing the workflow of this project by now. Whenever we want to add a new feature to the game, we need to consider:
* Do we need a new message type in our protocol buffers? If so, add it to the `packets.proto` file and recompile into source code.
* Do we need the server to send this message to the client? If so, create a helper function in the `util.go` file to make it easier to create the message.
* Do we need to store this information on the server? If so, add a new struct to the `objects` package and a new collection to the `SharedGameObjects` struct in the `hub.go` file.
* Do we need to render this information on the client? If so, create a new scene and script for the object in the `objects` folder, and add a new method to the `InGame` state script to handle the message and instantiate the object.
* Et cetera...

We will be following this workflow for most of the features we add to the game from here on, so there's still plenty of time to get used to it. For now though, I figured it's been a while since we've checked our project structure, so I'll give you a quick rundown of what we have so far:

<details markdown="1">
<summary>Click to expand</summary>

```plaintext
/
├───.vscode/
│       launch.json
│       
├───client/
│   │   game_manager.gd
│   │   main.gd
│   │   main.tscn
│   │   packets.gd
│   │   project.godot
│   │   websocket_client.gd
│   │
│   ├───addons/
│   │       protobuf/
│   │
│   ├───classes/
│   │   └───log/
│   │           log.gd
│   │           log.tscn
│   │
│   ├───objects/
│   │   ├───actor/
│   │   │       actor.gd
│   │   │       actor.tscn
│   │   │
│   │   └───spore/
│   │           spore.gd
│   │           spore.tscn
│   │
│   ├───resources/
│   │       floor.svg
│   │
│   └───states/
│       ├───connected/
│       │       connected.gd
│       │       connected.tscn
│       │
│       ├───entered/
│       │       entered.gd
│       │       entered.tscn
│       │
│       └───ingame/
│               ingame.gd
│               ingame.tscn
│
├───server/
│   │   go.mod
│   │   go.sum
│   │
│   ├───cmd/
│   │       db.sqlite
│   │       debug_executable.exe
│   │       main.go
│   │
│   ├───internal/
│   │   └───server/
│   │       │   hub.go
│   │       │
│   │       ├───clients/
│   │       │       websocket.go
│   │       │
│   │       ├───db/
│   │       │   │   db.go
│   │       │   │   models.go
│   │       │   │   queries.sql.go
│   │       │   │
│   │       │   └───config/
│   │       │           queries.sql
│   │       │           schema.sql
│   │       │           sqlc.yml
│   │       │
│   │       ├───objects/
│   │       │       gameObjects.go
│   │       │       sharedCollection.go
│   │       │       spawn.go
│   │       │
│   │       └───states/
│   │               connected.go
│   │               ingame.go
│   │
│   └───pkg/
│       └───packets/
│               packets.pb.go
│               util.go
│
└───shared/
        packets.proto
```
</details>

For anyone who wants to keep going, I've added a section below on how to send spores in batches, which will help reduce the time it takes for the client to receive all the spores. But if you're happy with the progress we've made so far, I'll see you in <strong><a href="/2024/11/15/godot-golang-mmo-part-8" class="sparkle-less">the next post</a></strong> where we will be adding the logic to grow the player when they consume a spore, or another player!

---

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.

---

## Optional: Sending spores in batches

<small>*Psst! I heard you want spores to come in shipments, not one-by-one. I got you covered.*</small>

<details markdown="1">
<summary>Click to expand</summary>

For those of you still around, let's put in a little extra effort to get the initial spores sent to the client in a much more efficient way. This will require a new type of protobuf message we've never seen before: a repeated field. This is a way to send a list of messages in a single packet, which is perfect for sending spores in batches. Let's start by adding a new message type to our protocol buffers:

```directory
/shared/packets.proto
```

```proto
message SporesBatchMessage { repeated SporeMessage spores = 1; }

message Packet {
    // ...
    oneof msg { 
        // ...
        SporesBatchMessage spores_batch = 12;
    }
}
```

Let's now add a helper function to easily make a new `SporesBatchMessage`. Since we're going to be creating more `SporeMessage`s to fill the batch, we might as well add a helper function to create these `SporeMessage`s as well, since it can also be used in the `NewSpore` function:

```directory
/server/pkg/packets/util.go
```

```go
func newSporeMessage(spore_id uint64, spore *objects.Spore) *SporeMessage {
    return &SporeMessage{
        Id:     spore_id,
        X:      spore.X,
        Y:      spore.Y,
        Radius: spore.Radius,
    }
}

func NewSpore(id uint64, spore *objects.Spore) Msg {
    return &Packet_Spore{
        Spore: newSporeMessage(id, spore),
    }
}

func NewSporesBatch(spores map[uint64]*objects.Spore) Msg {
    sporesMessages := make([]*SporeMessage, len(spores))
    for id, spore := range spores {
        sporesMessages = append(sporesMessages, newSporeMessage(id, spore))
    }
    return &Packet_SporesBatch{
        SporesBatch: &SporesBatchMessage{
            Spores: sporesMessages,
        },
    }
}
```

The `NewSporesBatch` function takes simply a map of our `Spore` objects, creates a batch of `SporeMessage`s from them, and packages them all up in our new `SporesBatchMessage`. Now, let's modify the `OnEnter` method in the `InGame` state script to send the spores in batches:

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) OnEnter() {
    // ...
    // Send the spores to the client in the background
    go func() {
        const batchSize = 20
        sporesBatch := make(map[uint64]*objects.Spore, batchSize)

        g.client.SharedGameObjects().Spores.ForEach(func(sporeId uint64, spore *objects.Spore) {
            sporesBatch[sporeId] = spore

            if len(sporesBatch) >= batchSize {
                g.client.SocketSend(packets.NewSporesBatch(sporesBatch))
                sporesBatch = make(map[uint64]*objects.Spore, batchSize)
                time.Sleep(50 * time.Millisecond)
            }
        })

        // Send any remaining spores
        if len(sporesBatch) > 0 {
            g.client.SocketSend(packets.NewSporesBatch(sporesBatch))
        }
    }()
}
```

Now we are converting the shared spores collection into a series of batches, each containing 20 spores. We package them all up, send them off, then wait a bit before sending the next batch. This is just to ensure we don't flood the client with too many large packets at once. Even though we are still sleeping, we are able to send 20 spores per 50 milliseconds this way (400 spores per second), which is a twice as fast as sending them one-by-one and sleeping for 5 milliseconds between each one. In reality, it is going to be much faster than twice as fast, because we don't need the overhead of sending a TCP packet for each spore, and we don't need to worry about filling up the send buffer either.

You are encouraged to play around with the batch size and sleep time to see what works best for you. You might even find you can improve the performance even more this way!

I'm not really loving how long the anonymous goroutine got, nor how many magic numbers we accumulated. I'd suggest just extracting the logic into a new method called `sendInitialSpores` (we can even turn the magic numbers into arguments) and simplify the `OnEnter` method to just call this new method in the background:

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) OnEnter() {
    // ...
    go g.sendInitialSpores(20, 50 * time.Millisecond)
}

func (g *InGame) sendInitialSpores(batchSize int, delayBetweenBatches time.Duration) {
    // Basically the same code as before, but with the magic numbers replaced with arguments
}
```

Now we still need to update the client to handle the new `SporesBatchMessage` type. This is just a matter of adding a new case to the `HandleMessage` method in the `InGame` state script:

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _on_ws_packet_received(packet: packets.Packet) -> void:
    # ...
    elif packet.has_spores_batch():
        _handle_spores_batch_msg(sender_id, packet.get_spores_batch())

func _handle_spores_batch_msg(sender_id: int, spores_batch_msg: packets.SporesBatchMessage) -> void:
    for spore_msg in spores_batch_msg.get_spores():
        _handle_spore_msg(sender_id, spore_msg)
```

Simple as that! Now the client will be able to receive spores in batches, and you should see them pop in much faster than before. Here is a comparison of the two methods side-by-side (old method on the left, new method on the right):
<video controls>
  <source src="/assets/css/images/posts/2024/11/14/comparison.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

If you're happy with the progress we've made so far, I'll see you in <strong><a href="/2024/11/15/godot-golang-mmo-part-8" class="sparkle-less">the next post</a></strong> where we will be adding the logic to grow the player when they consume a spore, or another player!

</details>