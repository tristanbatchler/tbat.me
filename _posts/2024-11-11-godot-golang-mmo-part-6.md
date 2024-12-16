---
title: "§06 Add Core Gameplay to Your Godot 4 MMO"
description: "Bring your world to life! Learn how to handle player creation, movement, and the game loop with a Golang-powered server."
redditurl: 
project: godot4golang
---

Welcome back to the Godot 4 + Golang MMO series. In [the last post](/2024/11/10/godot-golang-mmo-part-5), we finally finished laying down the groundwork with the database connections. Now, it's time to breathe life into our game by adding core gameplay mechanics.

Here’s a quick preview of what we’ll achieve in this post:
<video controls>
  <source src="/assets/images/posts/2024/11/11/output.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

We'll start by adding a new state to our server called `InGame`, and expand our packet system to handle player actions. Let’s dive in and start shaping the player experience!

As always, if do you want to start here without viewing the previous lesson, feel free to download the source code for release [v0.05](https://github.com/tristanbatchler/Godot4Go_MMO/releases/tag/v0.05) in the [official GitHub repository](https://github.com/tristanbatchler/Godot4Go_MMO).

## Players

Before we do any of that, we will need to create a new struct to represent our players. It will need to hold a player's name, position, speed, direction, and radius. Keeping track of these players can be done using the `SharedCollection` data structure we created in [part 3](/2024/11/09/godot-golang-mmo-part-3#making-a-custom-data-structure).

Create a new file called `gameObjects.go` in the `/server/internal/server/objects` directory, alongside `sharedCollection.go`. Add the following code to the file:

```directory
/server/internal/server/objects/gameObjects.go
```
```go
package objects

type Player struct {
    Name      string
    X         float64
    Y         float64
    Radius    float64
    Direction float64
    Speed     float64
}
```

We will now need to add a new wrapper to store collections of game objects in our hub. This is what can be accessed easily by different states. Add the following code to the `hub.go` file:

```directory
/server/internal/server/hub.go
```
```go
type SharedGameObjects struct {
    // The ID of the player is the ID of the client
    Players *objects.SharedCollection[*objects.Player]
}
```

More collections will be added to this struct as we add more game objects to our server. For now, we only need to keep track of players. Let's add a reference to this struct in the `Hub` struct:

```directory
/server/internal/server/hub.go
```
```go
type Hub struct {
    // ...
    SharedGameObjects *SharedGameObjects
    // ...
}

func NewHub() *Hub {
    // ...
    SharedGameObjects: &SharedGameObjects{
        Players: objects.NewSharedCollection[*objects.Player](),
    },
    // ...
}
```

We need the `ClientInterfacer` to be able to access the `SharedGameObjects` struct. Add the following new method to the `ClientInterfacer` interface:

```directory
/server/internal/server/hub.go
```
```go
type ClientInterfacer interface {
    // ...
    SharedGameObjects() *SharedGameObjects
    // ...
}
```

Now we need to implement this method in the `WebSocketClient` struct:

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) SharedGameObjects() *server.SharedGameObjects {
    return c.hub.SharedGameObjects
}
```

Now, we can create a new player when the user logs in successfully, and use it to pass information into the next state. Let's add a new state to our server before we do this.

## InGame state

Create a new file called `ingame.go` in the `/server/internal/server/states` directory. It needs to implement our `ClientStateHandler` interface, so add the following code to the file:

```directory
/server/internal/server/states/ingame.go
```
```go
package states

import (
    "fmt"
    "log"
    "server/internal/server"
    "server/internal/server/objects"
    "server/pkg/packets"
)

type InGame struct {
    client server.ClientInterfacer
    player *objects.Player
    logger *log.Logger
}

func (g *InGame) Name() string {
    return "InGame"
}

func (g *InGame) SetClient(client server.ClientInterfacer) {
    g.client = client
    loggingPrefix := fmt.Sprintf("Client %d [%s]: ", client.Id(), g.Name())
    g.logger = log.New(log.Writer(), loggingPrefix, log.LstdFlags)
}

func (g *InGame) OnEnter() {
    g.logger.Printf("Adding player %s to the shared collection", g.player.Name)
    go g.client.SharedGameObjects().Players.Add(g.player, g.client.Id())
}

func (g *InGame) HandleMessage(senderId uint64, message packets.Msg) {
}

func (g *InGame) OnExit() {
    g.client.SharedGameObjects().Players.Remove(g.client.Id())
}
```

See how we are adding the player to the `SharedGameObjects` collection when the state is entered, and we are ensuring that the player is added with the client's ID as the key. I am not sure if this will be useful, but it makes more sense to me to have the player ID be the same as the client ID.

Remember this is a shared collection owned by the hub, so any state from any client can access it. We might be stuck waiting for access to change the collection, so we run the `Add` method in a goroutine, since we don't really care *when* it gets added, just that it does. For more sensitive operations, it would be more appropriate to wait for the operation to complete.

It is also important to remove the player from the collection when the state is exited. This is to ensure that the collection is kept clean and up-to-date.

We can transition to this state when the client logs in successfully in the `Connected` state. Let's add that logic now, to the end of the `handleLoginRequest` method:

```directory
/server/internal/server/states/connected.go
```
```go
import (
    // ...
    "server/internal/server/objects"
    // ...
)

func (c *Connected) handleLoginRequest(senderId uint64, message *packets.Packet_LoginRequest) {
    // ...  
    c.client.SetState(&InGame{
        player: &objects.Player{
            Name: username,
        },
    })
}
```

See how we are able to set the `Player` object with an initial name while we are changing states. This will be a common technique to pass initial information to the next state.

As a sanity check at this point, you should run the server and connect to it. If you see something like the following in the server logs, you are on the right track.

```
2024/11/11 07:41:46 Starting server on :8080
2024/11/11 07:41:46 Awaiting client registrations
2024/11/11 07:51:21 New client connected from [::1]:61824
Client 1: 2024/11/11 07:51:21 Switching from state None to Connected
Client 1 [Connected]: 2024/11/11 07:51:25 User tristan logged in successfully
Client 1: 2024/11/11 07:51:25 Switching from state Connected to InGame
Client 1 [Connected]: 2024/11/11 07:51:25 Adding player saltytaro to the shared collection
```

## New packets

We will need to add some new packets to send player information to the client, and to receive player movement information from the client. Open up your `packets.proto` file and add the following new messages:

```directory
/shared/packets.proto
```
```proto
message PlayerMessage { uint64 id = 1; string name = 2; double x = 3; double y = 4; double radius = 5; double direction = 6; double speed = 7; }
message PlayerDirectionMessage { double direction = 1; }

// ... 

message Packet {
    // ...
    oneof msg {
        // ...
        PlayerMessage player = 8;
        PlayerDirectionMessage player_direction = 9;
    }
}
```

Now, don't forget to compile the proto file to generate the new Go code, and do the same for the GDScript code in Godot Godobuf. Instructions for the Golang code compilation can be found in <a href="/2024/11/09/godot-golang-mmo-part-1#protoc-usage" target="_blank">§01</a>, and the Godobuf instructions are in <a href="/2024/11/09/godot-golang-mmo-part-1#godobuf-usage" target="_blank">the same post, a bit further down</a>.

We will also add a new helper function to your `util.go` file:

```directory
/server/pkg/packets/util.go
```
```go
import "server/internal/server/objects"

func NewPlayer(id uint64, player *objects.Player) Msg {
    return &Packet_Player{
        Player: &PlayerMessage{
            Id:        id,
            Name:      player.Name,
            X:         player.X,
            Y:         player.Y,
            Radius:    player.Radius,
            Direction: player.Direction,
            Speed:     player.Speed,
        },
    }
}
```


## Sending player information to the client

As soon as the `InGame` state is reached, we should send the player information to the client. Immediately before we do this, we have the freedom to set the player's properties like initial position, speed, and radius. Let's add the following code to the `OnEnter` method of the `InGame` state:

```directory
/server/internal/server/states/ingame.go
```
```go
import (
    // ...
    "math/rand"
    // ...
)

func (g *InGame) OnEnter() {
    // ...

    // Set the initial properties of the player
    g.player.X = rand.Float64() * 1000
    g.player.Y = rand.Float64() * 1000
    g.player.Speed = 150.0
    g.player.Radius = 20.0

    // Send the player's initial state to the client
    g.client.SocketSend(packets.NewPlayer(g.client.Id(), g.player))
}
```

Since the shared game objects are holding pointers to the player objects, we are free to modify them local to the state, and not need to worry about updating the shared collection. 

We are also sending the player's initial state directly to the client, so we are now able to go ahead and render the player on the client side.

## Receiving player information on the client

Open up your Godot project and create a new folder at `res://objects/`. Inside this folder, create another folder called `actor`, and inside that folder create a new scene called `actor.tscn`. The root node of this scene should be an `Area2D`. This is what we will use to represent any player in the game.

{% include img.html src="posts/2024/11/11/actor_scene.png" alt="Actor Scene" %}

Open up the `res://objects/actor/actor.tscn` scene and add a **CollisionShape2D** node as a child of the **Actor** node. Set the shape of the **CollisionShape2D** to a new **CircleShape2D**. This will represent the player's hitbox.

>❗Important: set the **Local to Scene** property of the **CollisionShape2D**'s **Shape** property to `true`. You can click on the CircleShape2D in the inspector to open its properties, and you'll find the option under **Resources**. This will allow the hitbox's radius to change on a per-instance basis. {% include highlight.html anchor="local-to-scene-note" text="If you don't do this, changing one player's radius will change <strong>all</strong> player's radii, making for a very frustrating debugging experience <small><em>don't ask me how I know</em></small>." %}

{% include img.html src="posts/2024/11/11/local_to_scene.png" alt="Local to Scene" %}

Add another child node to the **Actor** node so that it is a sibling of the **CollisionShape2D** node. This new node should be a **Label** node. This will represent the player's name. Set the **Horizontal Alignment** and **Vertical Alignment** properties of the **Label** node to **Center** and then choose the **Center** anchor preset to position the label in the center of the player.

{% include img.html src="posts/2024/11/11/actor_scene_2.png" alt="Actor Scene" %}

Finally, add a **Camera2D** sibling. This is what we can use to follow the player around the screen and change the zoom level as we grow.

Now, let's attach a new script, `res://objects/actor/actor.gd`, to the **Actor** node. Add the following code to the script:

```directory
/client/objects/actor/actor.gd
```
```gd
extends Area2D

const packets := preload("res://packets.gd")

const Scene := preload("res://objects/actor/actor.tscn")
const Actor := preload("res://objects/actor/actor.gd")

var actor_id: int
var actor_name: String
var start_x: float
var start_y: float
var start_rad: float
var speed: float
var is_player: bool

var velocity: Vector2
var radius: float

@onready var _nameplate := $Label as Label
@onready var _camera := $Camera2D as Camera2D
@onready var _collision_shape := $CollisionShape2D.shape as CircleShape2D

static func instantiate(actor_id: int, actor_name: String, x: float, y: float, radius: float, speed: float, is_player: bool) -> Actor:
    var actor := Scene.instantiate()
    actor.actor_id = actor_id
    actor.actor_name = actor_name
    actor.start_x = x
    actor.start_y = y
    actor.start_rad = radius
    actor.speed = speed
    actor.is_player = is_player

    return actor


func _ready():
    position.x = start_x
    position.y = start_y
    velocity = Vector2.RIGHT * speed
    radius = start_rad
    
    _collision_shape.radius = radius
    _nameplate.text = actor_name

func _physics_process(delta) -> void:
    position += velocity * delta
    
    if not is_player:
        return
    # Player-specific stuff below here
        
    var mouse_pos := get_global_mouse_position()
    
    var input_vec = position.direction_to(mouse_pos).normalized()
    if abs(velocity.angle_to(input_vec)) > TAU / 15: # 12 degrees
        velocity = input_vec * speed
        var packet := packets.Packet.new()
        var player_direction_message := packet.new_player_direction()
        player_direction_message.set_direction(velocity.angle())
        WS.send(packet)

func _draw() -> void:
    draw_circle(Vector2.ZERO, _collision_shape.radius, Color.DARK_ORCHID)
```

There is quite a lot happening here, so let's break it down:

- All the fields we need to keep track of the player's state are declared at the top of the script.
- The `instantiate` function is a static function that we can use to create a new instance of the `Actor` scene. This will be called in our state machine when we receive a new player message from the server. It takes all the player's properties as arguments, but it also takes a boolean `is_player` argument. This is so we can differentiate between the player and other players in the game. This is what we can check before accepting input or sending messages to the server.
- The `_ready` function is called when the scene is ready to be used. This is where we actually set the properties of the scene nodes, like the `position` property of the `Area2D` node from which we inherit.
- The `_physics_process` function is called every frame, and this is where we can update the player's position based on input. If the angle between the player's current velocity and the input vector is greater than 12 degrees, we will update the player's velocity and send an updated direction message to the server.
- The `_draw` function is called just once, after `_ready`, and this is where we can draw the player's hitbox. Whenever we update the player's radius, we will need to remember to call `queue_redraw()` to force the `_draw` function to be called again.

Now that we have a way to add a new player to the game, let's go ahead and get the `InGame` state to listen for a new player message from the server and do just that. But first, where will we add the player to, exactly? We need to create a new **Node2D** to the **InGame** scene called **World**. The `res://states/ingame/ingame.tscn` scene should look like this:
* **Node** - called `InGame`
  * **Node2D** - called `World`
  * **CanvasLayer** - called `UI`
    * **LineEdit**
    * **Log (log.gd)**

Now we can go ahead and modify the `ingame.gd` script to add new players to the world.

```directory
/client/states/ingame/ingame.gd
```
```gd
# ...

const Actor := preload("res://objects/actor/actor.gd")

# ...

@onready var _world := $World as Node2D

# ...

func _on_ws_packet_received(packet: packets.Packet) -> void:
    # ...
    elif packet.has_player():
        _handle_player_msg(sender_id, packet.get_player())

# ...

func _handle_player_msg(sender_id: int, player_msg: packets.PlayerMessage) -> void:
    var actor_id := player_msg.get_id()
    var actor_name := player_msg.get_name()
    var x := player_msg.get_x()
    var y := player_msg.get_y()
    var radius := player_msg.get_radius()
    var speed := player_msg.get_speed()

    var is_player := actor_id == GameManager.client_id
    
    var actor := Actor.instantiate(actor_id, actor_name, x, y, radius, speed, is_player)
    _world.add_child(actor)
```

This is fairly straightforward now that we have a feel for how listen for incoming packets, get their contents. We are using the static `instantiate` function of the `Actor` script to create a new instance of the `Actor` scene, and then adding it as a child of the `World` node. 

Now, when you run the server and connect to it, you should see a new player appear in the game world. It's hard to tell if the player is moving though, since the background is just a gray screen. Let's add a background to the game world.

## Adding a background

Create a new folder at `res://resources/` and import the following image into the folder as `floor.svg` (or you can make your own):
![floor.svg](/assets/images/posts/2024/11/11/floor.svg)
> You can download the image by right-clicking on it and selecting **Save image as** and save it to `/client/resources`.

Now, in the **InGame** scene, under the **World** Node2D, add a new **Sprite2D** node called `Floor`. Now make the following edits to the `Floor` sprite:
1. Set the **Texture** property to `resources/floor.svg` (use the **Quick Load...** option in the drop-down)
2. Tick the **Enabled** checkbox under **Region**
3. Set the **Rect**'s **w** and **h** to `10000` each, under **Region**
4. Choose **Enabled** for the **Repeat** property under **Texture**

{% include img.html src="posts/2024/11/11/floor_sprite.png" alt="Floor Sprite" %}

Now, when you run the game, you should see a tiled floor in the background. You should also see the player moving around the screen. So far though, we aren't doing anything with the `PlayerDirectionMessage` packet we added earlier. This is what we need to allow the server to keep track of the player's position and broadcast it to all other clients. Let's add this logic now.

## Tracking player movement on the server

We are going to need to keep an accurate representation of the player's position on the server, which means we'll need a do some game loop logic.

In the `InGame` state, we'll create a new function called `syncPlayer`, which will take a `delta` argument. If you have worked with Godot or Unity before, you might be familiar with the concept of delta time. This is the time it took to render the last frame, and it is useful for keeping the game running at a consistent speed, regardless of the frame rate. In our context, `delta` will represent the number of seconds since the player's position was last updated. We will be making calls to this function in a loop, running at a fixed rate. Let's see that in action:

```directory
/server/internal/server/states/ingame.go
```
```go
import (
    // ...
    "math"
    // ...
)

func (g *InGame) syncPlayer(delta float64) {
    newX := g.player.X + g.player.Speed*math.Cos(g.player.Direction)*delta
    newY := g.player.Y + g.player.Speed*math.Sin(g.player.Direction)*delta

    g.player.X = newX
    g.player.Y = newY

    updatePacket := packets.NewPlayer(g.client.Id(), g.player)
    g.client.Broadcast(updatePacket)
    go g.client.SocketSend(updatePacket)
}
```

Here, we are using a bit of simple trigonometry to calculate the new position of the player based on the player's current direction and speed. You can interact with the formula [here](https://www.desmos.com/calculator/lktktkssjs) to see it in action.

We are then updating the player's position and sending the update to all clients. We are also sending the update to the client that owns the player, so that they can ensure they are in-sync with the server. This can cause rubber-banding if the client's position is too far from the server's position, but we will address this in a future post. Notice we are sending the packet in a goroutine, so that we don't block the game loop, and because we don't really care about the result of the send operation, or when it completes.

Since we are broadcasting the `PlayerMessage` packet, we need to expect it in the `HandleMessage` method. In this case, all we need to do is forward the packet on to the client on behalf of the sender.

```directory
/server/internal/server/states/ingame.go
```
```go
func (g *InGame) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    case *packets.Packet_Player:
        g.handlePlayer(senderId, message)
    }
}

func (g *InGame) handlePlayer(senderId uint64, message *packets.Packet_Player) {
    if senderId == g.client.Id() {
        g.logger.Println("Received player message from our own client, ignoring")
        return
    }
    g.client.SocketSendAs(message, senderId)
}
```


Now, we need to call this function in a loop, in a goroutine. To do this, let's create a new function called `playerUpdateLoop` in the `InGame` state:

```directory
/server/internal/server/states/ingame.go
```
```go
import (
    "context"
    "time"
    // ...
)

func (g *InGame) playerUpdateLoop(ctx context.Context) {
    const delta float64 = 0.05
    ticker := time.NewTicker(time.Duration(delta*1000) * time.Millisecond)
    defer ticker.Stop()

    for {
        select {
        case <-ticker.C:
            g.syncPlayer(delta)
        case <-ctx.Done():
            return
        }
    }
}
```

This function will run in a loop, updating the player's position every 50 milliseconds. We are using a `time.Ticker` to achieve this. We are also using a `defer` statement to ensure that the ticker is stopped when the function exits. Notice how we are also passing in a context that we can listen to for a signal to stop the loop. Let's define get a cancel function for this loop in the `InGame` struct:

```directory
/server/internal/server/states/ingame.go
```
```go
type InGame struct {
    // ...
    cancelPlayerUpdateLoop context.CancelFunc
    // ...
}
```

Now let's get this loop started in a goroutine as soon as the first `PlayerDirectionMessage` is received.

```directory
/server/internal/server/states/ingame.go
```
```go
func (g *InGame) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    // ...
    case *packets.Packet_PlayerDirection:
        g.handlePlayerDirection(senderId, message)
    }
}

func (g *InGame) handlePlayerDirection(senderId uint64, message *packets.Packet_PlayerDirection) {
    if senderId == g.client.Id() {
        g.player.Direction = message.PlayerDirection.Direction

        // If this is the first time receiving a player direction message from our client, start the player update loop
        if g.cancelPlayerUpdateLoop == nil {
            ctx, cancel := context.WithCancel(context.Background())
            g.cancelPlayerUpdateLoop = cancel
            go g.playerUpdateLoop(ctx)
        }
    }
}
```

Finally, we need to stop the player update loop whenever the player is not in-game. Let's add the following code to the `OnExit` method of the `InGame` state:

```directory
/server/internal/server/states/ingame.go
```
```go
func (g *InGame) OnExit() {
    if g.cancelPlayerUpdateLoop != nil {
        g.cancelPlayerUpdateLoop()
    }
    // ...
}
```

> ⚠️ **Note**: If you try and run the game at this point, you will notice a flood of new players being added every 50 milliseconds. This is because on the client side, we are not keeping track of the players that already exist in the game--we are simply adding a new player every time we receive a `PlayerMessage` packet. We will address this in the next section.

## Tracking other players on the client

Now that we have the server broadcasting player updates to all clients, we need to listen for these updates on the client side and update the player's position accordingly. Let's add this logic to the `ingame.gd` script that manages our in-game state. We will need to keep a map of all the players in the game, and we can use the player's ID as the key. Let's add this map near the top of the script:

```directory
/client/states/ingame/ingame.gd
```
```gd
# ...
var _players: Dictionary[int, Actor]
# ...
```

Now, where we are already handling the `PlayerMessage` packet, we need to surround our player actor instantiation with a check to see if the player already exists in the `_players` map. If they do, we will update the player's position instead of creating a new player. Let's add this logic now:

```directory
/client/states/ingame/ingame.gd
```
```gd
func _handle_player_msg(sender_id: int, player_msg: packets.PlayerMessage) -> void:
    # ...
    if actor_id not in _players:
        # This is a new player, so we need to create a new actor
        var actor := Actor.instantiate(actor_id, actor_name, x, y, radius, speed, is_player)
        _world.add_child(actor)
        _players[actor_id] = actor
    else:
        # This is an existing player, so we need to update their position
        var actor := _players[actor_id]
        actor.position.x = x
        actor.position.y = y
```

If you run the game now with two clients connected, it should be possible to find the other player and see them moving around the screen. If you are having difficulty finding the other, you can change the camera's zoom level to zoom out and see the entire game world. Just add something like the following to the `_input` function of `res://objects/actor/actor.gd`. It will allow you to zoom in and out using the scroll wheel:

```directory
/client/objects/actor/actor.gd
```
```gd
func _input(event):
    if is_player and event is InputEventMouseButton and event.is_pressed():
        match event.button_index:
            MOUSE_BUTTON_WHEEL_UP:
                _camera.zoom.x = min(4, _camera.zoom.x + 0.1)
            MOUSE_BUTTON_WHEEL_DOWN:
                _camera.zoom.x = max(0.1, _camera.zoom.x - 0.1)

        _camera.zoom.y = _camera.zoom.x
```

Now you should be able to zoom in and out using the scroll wheel. You can also see the other player moving around the screen. The movement is going to be very janky, since we are not interpolating the player's position between updates. This is something we can look at in the next post.

So it's far from perfect, but we have made good progress in this post. We have added gameplay to our MMO, and we can see other players moving around the screen. In <strong><a href="/2024/11/14/godot-golang-mmo-part-7" class="sparkle-less">the next post</a></strong>, we will look at smoothing out the player's movement, and adding some more gameplay elements to the game. Stay tuned!

---

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.
