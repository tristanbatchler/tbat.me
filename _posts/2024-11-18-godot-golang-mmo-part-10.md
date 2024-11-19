---
title: §10 Adding the final touches to our Godot 4 Go MMO
description: Let's add another feature to the game and allow players to search the leaderboard for their friends! These are the final features we will be adding to our game, before we move on to polishing everything up and deploying.
redditurl: 
---

This is the final part of the series we will concern ourselves with adding new features to the game. We just have two more features to add, and then we will move on to polishing everything up and deploying the game over the next two parts.

As a reminder, in the [last part](/2024/11/16/godot-golang-mmo-part-9/), we added a hiscores and a leaderboard to the game. In this part, we want to:
1. Give players a random chance to drop a spore and lose mass over time, giving them a reason to keep eating as much as possible
2. Allow players to search the leaderboard for themselves or their friends

This should be a shorter post than usual, since we should be very familiar with the codebase, tools, and workflow by now. I will also be a bit more brief on explanations where we've already covered the topic in detail. Let's get started!

<small>*But first...*</small>
## Homework solution

At the end of the last part, we noted there is no way to go back to the main menu from the hiscores screen. We will go over a solution to this before we start adding new features. <small>If you already completed the homework, good job! Feel free to skip ahead to the [next section](#dropping-spores), although you may want to skim through the solution to solidify your understanding of the concepts.</small>

Firstly, we will need to make a new packet to signal to the server that the client wants to go back to the `Connected` state.

```directory
/shared/packets.proto
```

```protobuf
message FinishedBrowsingHiscoresMessage { }

message Packet {
    // ...
    oneof msg {
        FinishedBrowsingHiscoresMessage finished_browsing_hiscores = 17;
    }
}
```

Next, let's get the server to listen for this packet in the `BrowsingHiscores` state, and transition back to the `Connected` state when it receives it.

```directory
/server/internal/server/states/browsingHiscores.go
```
```go
func (b *BrowsingHiscores) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    case *packets.Packet_FinishedBrowsingHiscores:
        b.handleFinishedBrowsingHiscores(senderId, message)
    }
}

func (b *BrowsingHiscores) handleFinishedBrowsingHiscores(_ uint64, _ *packets.Packet_FinishedBrowsingHiscores) {
    b.client.SetState(&Connected{})
}
```

Finally, we'll need a way to send this packet from the client. We will add a "Back" button that will send this packet when clicked. To do this, open up Godot, open the scene editor for `res://states/browsing_hiscores/browsing_hiscores.tscn`. Now, the way we left the scene in the last part, it will be difficult to position a button nicely, so let's fix that quickly:
1. Add a `VBoxContainer` just under the `UI` node, and set its anchor preset to **Full Rect**
2. Reposition the existing `Hiscores` node to be a child of the `VBoxContainer`
3. Add a `Button` node to the `VBoxContainer`, just above the `Hiscores` node. Name the button `BackButton`, and set the `Text` property to "Back"

Your scene should look like this, which I will admit is not the prettiest, but that's what the next part is for! We will make everything look nice and pretty eventually, but for now, we just want to get the functionality working.
![Browsing hiscores scene](/assets/css/images/posts/2024/11/18/browsing_hiscores_scene.png)

Now, let's edit the script for this scene to send the `FinishedBrowsingHiscoresMessage` packet when the button is clicked. We will also need to fix up the node path to the `Hiscores` node, since we moved it to be a child of the `VBoxContainer`.

```directory
/client/states/browsing_hiscores/browsing_hiscores.gd
```

```gdscript
@onready var _back_button := $UI/VBoxContainer/BackButton as Button
@onready var _hiscores := $UI/VBoxContainer/Hiscores as Hiscores

func _ready() -> void:
    _back_button.pressed.connect(_on_back_button_pressed)
    # ...

func _on_back_button_pressed() -> void:
    var packet := packets.Packet.new()
    packet.new_finished_browsing_hiscores()
    WS.send(packet)
    GameManager.set_state(GameManager.State.CONNECTED)
```

Now, when you run the game, you should be able to go back to the main menu from the hiscores screen. You should also be able to do all the things you could normally do in the connected state, like log in, register, and even go back to the hiscores screen.

<video controls>
  <source src="/assets/css/images/posts/2024/11/18/ch10-hw.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

## Dropping spores

At the moment, our MMO doesn't incentivize players to keep eating once they reach a certain size. We want to add a mechanic where players have a random chance to drop a spore, which will cause them to lose mass over time. This will give players a reason to keep eating, as to at least maintain their size, if not grow larger. Let's get started!

There are many ways we could implement this, but the simplest and lowest effort approach is probably to hook in to the existing `syncPlayer` method in the `InGame` state on the server. We will add a random chance to drop a spore and broadcast it to all clients, plus we'll strategically update the player's radius right before we broadcast our update. So we will be injecting this logic right after we update the player's position, but before we form the `updatePacket`:

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) syncPlayer(delta float64) {
    // ...

    // Drop a spore
    probability := g.player.Radius / float64(server.MaxSpores*5)
    if rand.Float64() < probability && g.player.Radius > 10 {
        spore := &objects.Spore{
            X:      g.player.X,
            Y:      g.player.Y,
            Radius: min(5+g.player.Radius/50, 15),
        }
        sporeId := g.client.SharedGameObjects().Spores.Add(spore)
        g.client.Broadcast(packets.NewSpore(sporeId, spore))
        go g.client.SocketSend(packets.NewSpore(sporeId, spore))
        g.player.Radius = g.nextRadius(-radToMass(spore.Radius))
    }

    // Broadcast the updated player state
    // ...
}
```

This code will drop a spore with a probability that increases with the player's size, but only if the player is larger than 10 units. The spore will have a radius between 5 and 15 units, and will be broadcast to all clients. We also send the spore to the client that dropped it, so they can see it immediately. Finally, we reduce the player's radius by the mass of the spore by using a negative value in the `nextRadius` method.

Now, if you run the game, you might notice the dropped spores are appearing on top of the player, but are immediately being consumed again since they are colliding with the player. It might be difficult to spot this at all, since they will only be there for a split second after they spawn. To fix this, we're going to need to do two things:
1. Make the client not consume the spore if it spawns on top of them
2. Add a new spore consumption validation check on the server in case a hacked client disables the first point.

### Making the client ignore spores that spawn on top of them

We are going to add a new flag to pass into the spore's `instantiate` function, which will tell us whether the spore was dropped by the player, and is still underneath the player. This flag will be turned off if ever the spore exits an actor's collision shape, and won't be turned back on ever again.

To achieve this, let's modify the `res://objects/spore/spore.gd` script to allow for this flag:

```directory
/client/objects/spore/spore.gd
```
```gdscript
const Actor := preload("res://objects/actor/actor.gd")

static func instantiate(spore_id: int, x: float, y: float, radius: float, underneath_player: bool) -> Spore:
    # ...
    spore.underneath_player = underneath_player
    # ...

func _ready() -> void:
    if underneath_player:
        area_exited.connect(_on_area_exited)
    # ...

func _on_area_exited(area: Area2D) -> void:
    if area is Actor:
        underneath_player = false
```

Now, we need to pass this flag when we instantiate the spore in the client's `InGame` state:

```directory
/client/states/ingame/ingame.gd
```
```gdscript
func _handle_spore_msg(sender_id: int, spore_msg: packets.SporeMessage) -> void:
    # ...
    var underneath_player := false
    if GameManager.client_id in _players:
        var player := _players[GameManager.client_id]
        var player_pos := Vector2(player.position.x, player.position.y)
        var spore_pos := Vector2(x, y)
        underneath_player = player_pos.distance_squared_to(spore_pos) < player.radius * player.radius

    if spore_id not in _spores:
        var spore := Spore.instantiate(spore_id, x, y, radius, underneath_player)
        # ...
```

We are inserting the logic just after we define the variables from the message, and before we add the spore as a child to the world. For absolute clarity, here's the full method:

<details markdown="1">
<summary>Click to expand</summary>

```gdscript
```directory
/client/states/ingame/ingame.gd
```
```gdscript
func _handle_spore_msg(sender_id: int, spore_msg: packets.SporeMessage) -> void:
    var spore_id := spore_msg.get_id()
    var x := spore_msg.get_x()
    var y := spore_msg.get_y()
    var radius := spore_msg.get_radius()
    var underneath_player := false
    
    if GameManager.client_id in _players:
        var player := _players[GameManager.client_id]
        var player_pos := Vector2(player.position.x, player.position.y)
        var spore_pos := Vector2(x, y)
        underneath_player = player_pos.distance_squared_to(spore_pos) < player.radius * player.radius

    if spore_id not in _spores:
        var spore := Spore.instantiate(spore_id, x, y, radius, underneath_player)
        _world.add_child(spore)
        _spores[spore_id] = spore
```
</details>

So now, in a perfect world, we would be finished with this feature! Here's a video of the spores dropping from various players, and the players losing mass over time as they consume the spores (I have increased the spore drop rate for demonstration purposes):

<video controls>
  <source src="/assets/css/images/posts/2024/11/18/client-eating.webm" type="video/webm">
  Your browser does not support the video tag.
</video>
<small>*It was an absolute nightmare to record this...*</small>

The only problem is, we do not live in a perfect world. Rule number one of networking: **never trust the client**. We need to add a new check on the server to ensure that the client is not consuming spores that are underneath them. Our approach here will be to add a timestamp to the spore object to signify when it was dropped. Then, when the client says they've consumed that spore, we will check if enough time has passed since the spore was dropped. If not, we will ignore the consumption request.

Let's start by adding a timestamp to the spore object:

```directory
/server/internal/server/objects/gameObjects.go
```
```go
import "time"

type Spore struct {
    // ...
    DroppedBy *Player
    DroppedAt time.Time
}
```

We do not need to worry about setting these new fields unless we are dropping the spore, since the `DroppedBy` field will default to `nil`, and the `DroppedAt` field won't matter. So let's modify the spore dropping logic to set these fields:

```directory
/server/internal/server/states/ingame.go
```
```go
func (g *InGame) syncPlayer(delta float64) {
    // ...

    // Drop a spore
    // ...
    if rand.Float64() < probability && g.player.Radius > 10 {
        spore := &objects.Spore{
            // ...
            DroppedBy: g.player,
            DroppedAt: time.Now(),
        }
        // ...
    }
    // ...
}
```

Now, over to the spore consumption validation logic we implemented in <a href="/2024/11/15/godot-golang-mmo-part-8#spore-consumption-validation" target="_blank">§08</a>. We will add a new check to ensure that the spore wasn't dropped after the time it takes for the player to travel combined radius of the player and the spore. This works because the minimum distance the player has to travel so the spore is not underneath them is their own radius, then the spore's radius. Then, best case scenario, the player turns around instantly and consumes the spore.

We know the player's speed in units per second, since the server assigns it to the player. Rearranging the simlple formula $$\text{distance} = \text{speed} \times \text{time}$$, we know that $$\text{time} = \frac{\text{distance}}{\text{speed}}$$. So, the minimum time (in seconds) it should take for the player to consume the spore is the sum of the radii of the player and the spore, divided by the player's speed. We will add this check to the `handleSporeConsumed` method:

```directory
/server/internal/server/states/ingame.go
```
```go
func (g *InGame) handleSporeConsumed(senderId uint64, message *packets.Packet_SporeConsumed) {
    // First check if the spore exists
    // ...

    // Next, check if the spore is close enough...
    // ...

    // Finally, check if the spore wasn't dropped by the player too recently
    err = g.validatePlayerDropCooldown(spore, 10)
    if err != nil {
        g.logger.Println(errMsg + err.Error())
        return
    }
    
    // If we made it this far, the spore consumption is valid...
}

func (g *InGame) validatePlayerDropCooldown(spore *objects.Spore, buffer float64) error {
    minAcceptableDistance := spore.Radius + g.player.Radius - buffer
    minAcceptableTime := time.Duration(minAcceptableDistance/g.player.Speed) * time.Second
    if spore.DroppedBy == g.player && time.Since(spore.DroppedAt) < minAcceptableTime {
        return fmt.Errorf("player dropped the spore too recently (time since drop: %v, min acceptable time: %v)", time.Since(spore.DroppedAt), minAcceptableTime)
    }
    return nil
}
```

We also include a buffer distance in this check, to allow for a little bit of leeway in case the server isn't synced perfectly with the client. This buffer is set to 10 units, but you can adjust this value to your liking.

Now, if you run the game, you shouldn't see any difference. The spores will still drop, and the players will still consume them. However, if you were to modify the client to consume spores that are underneath them (i.e. undo the changes we made to the client just above), you'll see the server complaining about the player dropping the spore too recently, and the player will appear to consume the spore but keep shrinking regardless. Any players witnessing this will see the player shrinking, but the dropped spores will still be there.

## Searching the leaderboard
*Coming soon...*