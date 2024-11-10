---
title: Adding Gameplay to the MMO with Godot 4 and Golang
description: Time to add a new state to our game server and handle player creation, movement, disconnection, and game loop.
redditurl: 
---

Welcome back to the Godot 4 + Golang MMO series. In [the last post](/posts/2024/11/10/godot-golang-mmo-pasrt-5), we finally finished laying down the groundwork with the database connections. Now it's time to add some much-needed gameplay to our MMO. We'll start by adding a new state to our server called `InGame`, make some new packets, and start processing them.

## Players

Before we do any of that, we will need to create a new struct to represent our players. It will need to hold a player's name, position, speed, direction, and radius. Keeping track of these players can be done using the `SharedCollection` data structure we created in [part 3](/posts/2024/11/09/godot-golang-mmo-part-3#making-a-custom-data-structure).

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
/server/internal/server/client.go
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

Create a new file called `ingame.go` in the `/server/internal/server/states` directory. It needs to implement our `ClientState` interface, so add the following code to the file:

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
    log.Printf("Adding player %s to the shared collection", g.player.Name)
	go g.client.SharedGameObjects().Players.Add(g.player, g.client.Id())
}

func (g *InGame) HandleMessage(senderId uint64, message packets.Msg) {
}

func (g *InGame) OnExit() {
}
```

See how we are adding the player to the `SharedGameObjects` collection when the state is entered, and we are ensuring that the player is added with the client's ID as the key. I am not sure if this will be useful, but it makes more sense to me to have the player ID be the same as the client ID.

Remember this is a shared collection owned by the hub, so any state from any client can access it. We might be stuck waiting for access to change the collection, so we run the `Add` method in a goroutine, since we don't really care *when* it gets added, just that it does. For more sensitive operations, it would be more appropriate to wait for the operation to complete.

We can transition to this state when the client logs in successfully in the `Connected` state. Let's add that logic now, to the end of the `handleLogin` method:

```directory
/server/internal/server/states/connected.go
```
```go
func (c *Connected) handleLogin(senderId uint64, message *packets.Packet_LoginRequest) {
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
/server/pkg/packets/packets.proto
```
```proto
message PlayerMessage { uint64 id = 1; string name = 2; double x = 3; double y = 4; double radius = 5; double speed = 6; }
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

Now, don't forget to compile the proto file to generate the new Go code, and do the same for the GDScript code in Godot Godobuf.

We will also add a new helper function to your `utils.go` file:

```directory
/server/pkg/packets/utils.go
```
```go
import "server/internal/server/objects"

func NewPlayer(id uint64, player *objects.Player) Msg {
	return &Packet_Player{
		Player: &PlayerMessage{
			Id:     id,
			Name:   player.Name,
			X:      player.X,
			Y:      player.Y,
			Radius: player.Radius,
			Speed:  player.Speed,
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

![Actor Scene](/assets/css/images/posts/2024/11/11/actor_scene.png)

Open up the `res://objects/actor/actor.tscn` scene and add a **CollisionShape2D** node as a child of the **Actor** node. Set the shape of the **CollisionShape2D** to a new **CircleShape2D**. This will represent the player's hitbox.

Add another child node to the **Actor** node so that it is a sibling of the **CollisionShape2D** node. This new node should be a **Label** node. This will represent the player's name. Set the **Horizontal Alignment** and **Vertical Alignment** properties of the **Label** node to **Center** and then choose the **Center** anchor preset to position the label in the center of the player.

![Actor Scene](/assets/css/images/posts/2024/11/11/actor_scene_2.png)

Finally, add a **Camera2D** sibling. This is what we can use to follow the player around the screen and change the zoom level as we grow.

Now, let's attach a new script, `res://objects/actor/actor.gd`, to the **Actor** node. Add the following code to the script:

```directory
/client/objects/actor/actor.gd
```
```gd
extends Area2D

const packets = preload("res://packets.gd")

const Scene := preload("res://objects/actor/actor.tscn")
const Actor := preload("res://objects/actor/actor.gd")
const Self := Actor

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

static func instantiate(actor_id: int, actor_name: String, x: float, y: float, radius: float, speed: float, is_player: bool) -> Self:
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
		
	var mouse_pos = get_global_mouse_position()
	
	var input_vec = position.direction_to(mouse_pos).normalized()
	if abs(velocity.angle_to(input_vec)) > TAU / 15: # 12 degrees
		velocity = input_vec * speed
		var packet = packets.Packet.new()
		var player_direction_message = packet.new_player_direction()
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
* **InGame** (Node)
  * **World** (Node2D)
  * **UI** (CanvasLayer)
    * **LineEdit**
    * **Log** (log.tscn)

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
	var msg_name := player_msg.get_name()
	var msg_x := player_msg.get_x()
	var msg_y := player_msg.get_y()
	var msg_rad := player_msg.get_radius()
	var msg_speed := player_msg.get_speed()

    var is_player := actor_id == GameManager.client_id
    
    var actor := Actor.instantiate(actor_id, msg_name, msg_x, msg_y, msg_rad, msg_speed, is_player)
    _world.add_child(actor)
```

This is fairly straightforward now that we have a feel for how listen for incoming packets, get their contents. We are using the static `instantiate` function of the `Actor` script to create a new instance of the `Actor` scene, and then adding it as a child of the `World` node. 

Now, when you run the server and connect to it, you should see a new player appear in the game world. It's hard to tell if the player is moving though, since the background is just a gray screen. Let's add a background to the game world.