---
title: §7 Adding Objectives + Polishing the Godot 4 Go MMO
description: So we have a basic functioning MMO, but it's not very fun and movement is a bit janky. Let's make things a bit easier on the eyes and keep players engaged with objectives.
redditurl: 
---

Nice to see you again! In [the last post](/2024/11/11/godot-golang-mmo-part-6), we finally got some gameplay down, and we left off in a pretty good spot. We have a basic space where players can move around and spot each other, but it is very unpolished and I wouldn't really call it a "game" since it lacks objectives! Let's fix that today by adding some spores to collect and let the player grow. We will also be making the movement more fluid and restoring the chat functionality we kinda lost in the last post. Let's get right into it!

## Bringing back the chat
Low-hanging fruit, let's quickly restore our chatroom logic we got rid of in <a href="/2024/11/10/godot-golang-mmo-part-5#get-rid-of-chat-handling" target="_blank">§5</a>. All we need to do here is add a new case to the `HandleMessage` method in our `InGame` state handler:

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

Note the `handleChat` method is just a repeat of the code we had to remove in §5, which we originally wrote in <a href="/2024/11/09/godot-golang-mmo-part-3#add-chat-logic" target="_blank">§3</a>.

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

		var msg_direction := player_msg.get_direction()
		actor.velocity = msg_speed * Vector2.from_angle(msg_direction)
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
	SporeMessage spore = 10;
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

Now, to the interesting stuff: let's add a new file to our `objects` package to handle spawning game objects, since we will need to have the ability to place spores and players around the map, with some eventual logic to stop them from spawning on top of each other, for example. But for now, we'll just have a simple `SpawnCoords` function to give a random position on the map:

```directory
/server/internal/server/objects/spawn.go
```

```go
package objects

import (
	"math/rand/v2"
)

func SpawnCoords() (float64, float64) {
	return rand.Float64() * 1000, rand.Float64() * 1000
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

This section of code simply *starts* sending spores to the client in the background, so the client can start rendering them as soon as possible. We also added a small delay between each spore to avoid flooding the client with messages, which could cause the client to lag. The client interfacer won't block on this goroutine, so it can continue to process other messages while the spores are being sent.

This basically just allows the client to get into the game without needing to wait for all the spores to be sent, which is a better user experience, with the minor drawback that the player might see the spores pop in one by one. This should take less than a few seconds though, so it's not a big deal. Another approach would be to send all the spores in batches, or at once, but that would require a bit more work, so we could come back to that later if we find it necessary.

### Rendering the spores
Coming soon...