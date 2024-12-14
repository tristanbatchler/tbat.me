---
title: "§08 Introduce Competitive Metrics to Your Godot 4 MMO with Go"
description: "Encourage competition! Add scoring mechanics and server-side validation to ensure fair play as players strive for the top spot."
redditurl: 
project: godot4golang
---

{% include math.html %}

Welcome back! In the [last part](/2024/11/14/godot-golang-mmo-part-7), we introduced spores that players could eat to grow. Now, we’ll take things further by letting the server determine whether a player should grow after eating a spore, then notifying all other players of the change.

This opens the door to competitive gameplay, as we begin to incorporate scoring mechanics. With the added possibility of players eating each other, we’ll have the foundation for a truly competitive MMO. Let’s jump in and bring this to life!

Here is a sneak peek of what we will achieve today:
<video controls>
  <source src="/assets/images/posts/2024/11/15/ch8-preview.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

As always, if do you want to start here without viewing the previous lesson, feel free to download the source code for release [v0.07](https://github.com/tristanbatchler/Godot4Go_MMO/releases/tag/v0.07) in the [official GitHub repository](https://github.com/tristanbatchler/Godot4Go_MMO).

## Growing the player

First, we left off with the player eating spores and telling the server about it, but the server isn't doing anything with that information. It would be great if the server could validate the player's actions, and either accept or reject them. This way, we can prevent cheating, and make sure that the game is fair for everyone. If the changes are accepted, the server will then broadcast the changes to all other players, for other clients to interpret and display.

Let's start by removing the debug message we left in the `InGame` state's `HandleMessage` method and replace it with a call to a new handler method called `handleSporeConsumed`.

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    // ...
    case *packets.Packet_SporeConsumed:
        g.handleSporeConsumed(senderId, message)
    }
}

func (g *InGame) handleSporeConsumed(senderId uint64, message *packets.Packet_SporeConsumed) {
    // We will implement this method in a moment
}

```

{% include highlight.html anchor="spore-consumption-validation" text="Now, the handler method is going to have to check a few things:" %}
1. Does the spore the player said they ate *actually exist*?
2. Was the player anywhere *near* the spore they said they ate?
3. If the player ate the spore, how much should they grow?

So it's clear we're going to need some new methods to help us with this. Let's start with the first one, which will check if the spore exists.

### 1. Does the spore exist?

Add this new method to the `InGame` struct:

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) getSpore(sporeId uint64) (*objects.Spore, error) {
    spore, exists := g.client.SharedGameObjects().Spores.Get(sporeId)
    if !exists {
        return nil, fmt.Errorf("spore with ID %d does not exist", sporeId)
    }
    return spore, nil
}
```

This is more of a convenience wrapper around the `Get` method of the `Spores` collection from the hub, but at it gives us a chance to grab an error message we can use later, plus it will help make our handler method just a bit cleaner. 

### 2. Was the player near the spore?
Next up, we need to check if the player was near the spore they said they ate. Now we don't want to be too strict about this, because the synchronization between the server and the client isn't ever going to be perfect, and we don't want to punish the player for that. So we can check if the player is within a certain buffer distance of the spore.

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) validatePlayerCloseToObject(objX, objY, objRadius, buffer float64) error {
    realDX := g.player.X - objX
    realDY := g.player.Y - objY
    realDistSq := realDX*realDX + realDY*realDY

    thresholdDist := g.player.Radius + buffer + objRadius
    thresholdDistSq := thresholdDist * thresholdDist

    if realDistSq > thresholdDistSq {
        return fmt.Errorf("player is too far from the object (distSq: %f, thresholdSq: %f)", realDistSq, thresholdDistSq)
    }
    return nil
}
```

Here is some basic math to calculate the distance between the two circles. We are avoiding an expensive square root operation by comparing squared distances. A diagram might help to visualize this better:
{% include img.html src="posts/2024/11/15/combinedRadii.svg" alt="Circle collision diagram" %}

In the diagram, it is clear that the distance between the two circles is $$\text{pRad} + \text{buffer} + \text{sRad}$$, a.k.a. `player.Radius + buffer + objRadius`. If the real distance (calculated by the Pythagorean theorem) is greater than this threshold, then the player is not close enough to the object.

### 3. How much should the player grow?

I've been looking forward to this part for a while, because I can finally put my degree in math to good use. Well, not really, it's more like high school level math, but hey, it's fun nonetheless. We need to be able to calculate the player's new radius based on the size of what they just ate. 

When the player consumes something, they absorb its mass. For the sake of this game, let's assume the mass of players and spores is proportional to their area. This means that
* if the player's original radius is $$R_0$$, their original mass is $$M_0 = \pi R_0^2$$
* if the spore's radius is $$r$$, their mass is $$m = \pi r^2$$

When the player eats the spore, their new mass will be the sum of the two masses, i.e. 
<div style="text-align: center;">
$$
M_1 := M_0 + m
$$
</div>

To find the player's new radius, $$R_1$$, we need to solve the equation $$M_1 := \pi R_1^2$$ for $$R_1$$:
<div style="text-align: center;">
$$
\begin{align*}
M_0 + m &= \pi R_1^2 \\
\frac{M_0 + m}{\pi} &= R_1^2 \\
R_1 &= \sqrt{\frac{M_0 + m}{\pi}}
\end{align*}
$$
</div>

So, we'll need a method to calculate $$M_0$$ and $$m$$, let's call that `radToMass`, and another method to calculate $$R_1$$, call it `massToRad`.

```directory
/server/internal/server/states/ingame.go
```

```go
func radToMass(radius float64) float64 {
    return math.Pi * radius * radius
}

func massToRad(mass float64) float64 {
    return math.Sqrt(mass / math.Pi)
}
```

Now, we can use these methods to calculate the player's new radius after eating a spore.

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) nextRadius(massDiff float64) float64 {
    oldMass := radToMass(g.player.Radius)
    newMass := oldMass + massDiff
    return massToRad(newMass)
}
```

### Putting it all together
Finally, we can implement the `handleSporeConsumed` method.

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) handleSporeConsumed(senderId uint64, message *packets.Packet_SporeConsumed) {
    if senderId != g.client.Id() {
        g.client.SocketSendAs(message, senderId)
        return
    }

    // If the spore was supposedly consumed by our own player, we need to verify the plausibility of the event
    errMsg := "Could not verify spore consumption: "

    // First check if the spore exists
    sporeId := message.SporeConsumed.SporeId
    spore, err := g.getSpore(sporeId)
    if err != nil {
        g.logger.Println(errMsg + err.Error())
        return
    }

    // Next, check if the spore is close enough to the player to be consumed
    err = g.validatePlayerCloseToObject(spore.X, spore.Y, spore.Radius, 10)
    if err != nil {
        g.logger.Println(errMsg + err.Error())
        return
    }

    // If we made it this far, the spore consumption is valid, so grow the player, remove the spore, and broadcast the event
    sporeMass := radToMass(spore.Radius)
    g.player.Radius = g.nextRadius(sporeMass)

    go g.client.SharedGameObjects().Spores.Remove(sporeId)

    g.client.Broadcast(message)
}
```

We are using a strategy where we check for the easiest things first, and if we fail at any point, we return early. This way, we can avoid making the server crunch numbers unnecessarily. If we make it to the end, we can be confident that the player's growth is valid, and we can broadcast the event to all players. Speaking of which, what happens when this event is broadcasted to us? It is handled at the top of the method, where we just forward the message on to the client. This way, the client can update the player's size and remove the spore from the game.

We are also using a goroutine to remove the spore from the hub, because we don't really care when it happens, as long as it happens. This way, we can avoid blocking the server while it waits to acquire a lock.

Note that we are not doing anything when we detect foul play, but you could consider having a system to penalize players who cheat. For now, we are just logging the error and moving on. It would cause the cheater's game to go out of sync with the server (because on the client side, the spores they collide with would still be there), but so be it; they don't deserve a pristine experience if they are going to cheat!

### Processing spore consumption on the client side

Now that the server is correctly handling spore consumption and sending the event to all clients if it is valid, we need to process this event in Godot. We will need to update the player's size and remove the spore from the game. Let's listen for that in the `InGame` state's `_on_ws_packet_received` method and make a call to a new handler:

```directory
/client/states/ingame/ingame.gd
```

```gd
func _on_ws_packet_received(packet: packets.Packet) -> void:
    # ...
    elif packet.has_spore_consumed():
         _handle_spore_consumed_msg(sender_id, packet.get_spore_consumed())

func  _handle_spore_consumed_msg(sender_id: int, spore_consumed_msg: packets.SporeConsumedMessage) -> void:
    if sender_id in _players:
        var actor := _players[sender_id]
        var actor_mass := _rad_to_mass(actor.radius)

        var spore_id := spore_consumed_msg.get_spore_id()
        if spore_id in _spores:
            var spore := _spores[spore_id]
            var spore_mass := _rad_to_mass(spore.radius)
            _set_actor_mass(actor, actor_mass + spore_mass)
            _remove_spore(spore)

func _rad_to_mass(radius: float) -> float:
    return radius * radius * PI
```

This is pretty much a direct translation of the Go code we wrote for the server, so I don't think I need to explain it in detail. The only difference is that instead of having a `nextRadius` method, we are going to define a function called `_set_actor_mass`, which will perform the same calculations. This way, it gives us an opportunity to add some extra logic if we need to in the future.

```directory
/client/states/ingame/ingame.gd
```

```gd
func _set_actor_mass(actor: Actor, new_mass: float) -> void:
    actor.radius = sqrt(new_mass / PI)
```

So now, if you run the game, you might be surprised to see that nobody is growing! There is one key detail we missed: `_draw` is only called once when an actor is created, so we don't see anyone's size change when we update `radius`. Even if we did, it would be meaningless because we also forgot to update the collision shape's radius along with the visual radius. Let's make sure it's impossible to forget this by adding a setter for the radius that updates the collision shape and redraws the actor.

```directory
/client/objects/actor/actor.gd
```

```gd
var radius: float:
    set(new_radius):
        radius = new_radius
        _collision_shape.set_radius(radius)
        queue_redraw()
```

This is a cool feature of Godot that means the `radius` property will automatically update the collision shape and redraw the actor whenever it appears on the left-hand-side of an `=` sign. This effectively makes it so that we can't forget to update the collision shape and redraw the actor when we change the radius.

**Now** if we run the game, we will see other players growing in size when they eat, but you won't see yourself grow yet! What gives? This is because we aren't sending the spore consumption event to ourselves (no need since we already know we ate the spore). We simply need to use our new `_set_actor_mass` method in the `_consume_spore` method we wrote in <a href="/2024/11/14/godot-golang-mmo-part-7#consuming-spores" target="_blank">the last part</a>.

```directory
/client/states/ingame/ingame.gd
```

```gd
func _consume_spore(spore: Spore) -> void:
    var player = _players[GameManager.client_id]
    var player_mass := _rad_to_mass(player.radius)
    var spore_mass := _rad_to_mass(spore.radius)
    _set_actor_mass(player, player_mass + spore_mass)
    
    # ...
```

Now, when you eat a spore, you should see yourself grow as well!

## Eating other players

Now that we have the concept of mass, and players can see themselves and their opponents grow, it is a good time to introduce the concept of eating other players. Implementing this feature will be very similar to eating spores, but with a couple of key differences:
1. You can only eat another player if your mass is 150% of theirs or more.
2. When you eat another player, you will gain their mass, and they will respawn at a random location with a smaller mass.

Let's get to work on this! First, we need to add a new message type to our protocol buffer file.

```directory
/protocol/packets.proto
```

```proto
message PlayerConsumedMessage { uint64 player_id = 1; }

message Packet {
    // ...
    oneof msg {
        // ...
        PlayerConsumedMessage player_consumed = 13;
    }
}
```

Now, on the client side's `InGame` state code, we can add to our `_on_player_area_entered` function to check if we're colliding with another actor and call a new function called `_collide_actor` if we are.

```directory
/client/states/ingame/ingame.gd
```

```gd
func _on_player_area_entered(area: Area2D) -> void:
    # ...
    elif area is Actor:
        _collide_actor(area as Actor)

func _collide_actor(actor: Actor) -> void:
    var player := _players[GameManager.client_id]
    var player_mass := _rad_to_mass(player.radius)
    var actor_mass := _rad_to_mass(actor.radius)

    if player_mass > actor_mass * 1.5:
        _consume_actor(actor)
```

So here is a simple check to see if the player's mass is 150% of the actor's mass. If it is, we call a new method called `_consume_actor`, which we will define in a moment. We don't need to worry about checking the reverse case, where *we* are the ones being eaten, because the server will tell us if that happens (because another client will have called `_consume_actor` on their end). We will handle that later.

```directory
/client/states/ingame/ingame.gd
```

```gd
func _consume_actor(actor: Actor) -> void:
    var player := _players[GameManager.client_id]
    var player_mass := _rad_to_mass(player.radius)
    var actor_mass := _rad_to_mass(actor.radius)
    _set_actor_mass(player, player_mass + actor_mass)

    var packet := packets.Packet.new()
    var player_consumed_msg := packet.new_player_consumed()
    player_consumed_msg.set_player_id(actor.actor_id)
    WS.send(packet)
    _remove_player(actor)
```

This is almost identical to the `_consume_spore` method, so nothing should be very shocking here. We are sending new information to the server which we need to remember to handle, but for now, we also need to define the `_remove_player` method, which shouldn't need any explanation either.

```directory
/client/states/ingame/ingame.gd
```

```gd
func _remove_player(actor: Actor) -> void:
    _players.erase(actor.actor_id)
    actor.queue_free()
```

Now, we need to handle this new message type on the server side.

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    // ...
    case *packets.Packet_PlayerConsumed:
        g.handlePlayerConsumed(senderId, message)
    }
}

func (g *InGame) handlePlayerConsumed(senderId uint64, message *packets.Packet_PlayerConsumed) {
    if senderId != g.client.Id() {
        g.client.SocketSendAs(message, senderId)

        if message.PlayerConsumed.PlayerId == g.client.Id() {
            log.Println("Player was consumed, respawning")
            g.client.SetState(&InGame{
                player: &objects.Player{
                    Name: g.player.Name,
                },
            })
        }

        return
    }

    // If the other player was supposedly consumed by our own player, we need to verify the plausibility of the event
    errMsg := "Could not verify player consumption: "

    // First, check the other player's radius is smaller than our player's
	if g.player.Radius <= other.Radius*1.5 {
		g.logger.Println(errMsg + "player's radius not big enough")
		return
	}

    // Next, check if the player exists
    otherId := message.PlayerConsumed.PlayerId
    other, err := g.getOtherPlayer(otherId)
    if err != nil {
        g.logger.Println(errMsg + err.Error())
        return
    }

    // Finally, check if the player is close enough to the other to be consumed
    err = g.validatePlayerCloseToObject(other.X, other.Y, other.Radius, 10)
    if err != nil {
        g.logger.Println(errMsg + err.Error())
        return
    }

    // If we made it this far, the player consumption is valid, so grow the player, remove the consumed other, and broadcast the event
    otherMass := radToMass(other.Radius)
    g.player.Radius = g.nextRadius(otherMass)

    go g.client.SharedGameObjects().Players.Remove(otherId)

    g.client.Broadcast(message)
}

func (g *InGame) getOtherPlayer(otherId uint64) (*objects.Player, error) {
    other, exists := g.client.SharedGameObjects().Players.Get(otherId)
    if !exists {
        return nil, fmt.Errorf("player with ID %d does not exist", otherId)
    }
    return other, nil
}
```

So the player consumption logic is pretty much the same as that for the spores, except we have a check to see if the player being eaten is our own player. If that's the case, we simply restart the state, which will respawn the player at a random location with a smaller mass. We don't need to remove the player from the shared collection, because that will be done by the client whose player ate us, plus we will be added back with the same ID when we respawn anyway.

In the spirit of checking the easiest things first, we are also ensuring that the player's radius is big enough to eat the other player before we check if the other player exists or is close enough to be eaten. This way, we can avoid unnecessary calculations if the player is too small to eat the other player.

If we run the game now, everything should be working as expected. You can eat spores to grow, and eat other players to grow even more. If you are eaten, you will respawn at a random location with the original starting mass. The game is starting to look like a competitive MMO!

If you play this game long enough, you will start noticing a couple issues:
1. It is possible for players to respawn into other players, causing them to be eaten immediately, which isn't very fun.
2. The spores don't respawn, so eventually, the server will run out of spores for players to eat.

Let's address these issues before we wrap up for today.

## Respawn logic

So far, we've been able to get away with spawning stuff at purely random coordinates, but now that we have the concept of eating other players, we need to be a bit more thoughtful. We need to make sure that players don't spawn inside each other, and it would be nice if the spores could avoid spawning inside players as well when we get to that.

Let's start by revisiting the `spawn.go` file we created in <a href="/2024/11/14/godot-golang-mmo-part-7#spawning-spors" target="_blank">the last part</a> and adding some new features to the `SpawnCoords` function.

```directory
/server/internal/server/objects/spawn.go
```

```go
func SpawnCoords(radius float64, playersToAvoid *SharedCollection[*Player], sporesToAvoid *SharedCollection[*Spore]) (float64, float64) {
    var bound float64 = 3000
    const maxTries int = 25

    tries := 0
    for {
        x := bound * (2*rand.Float64() - 1)
        y := bound * (2*rand.Float64() - 1)

        if !isTooClose(x, y, radius, playersToAvoid, getPlayerPosition, getPlayerRadius) &&
            !isTooClose(x, y, radius, sporesToAvoid, getSporePosition, getSporeRadius) {
            return x, y
        }

        tries++
        if tries > maxTries {
            bound *= 2
            tries = 0
        }
    }
}
```

This function will keep trying to find a random coordinate until it finds one that is not too close to any of the collections passed in. If it fails to find a coordinate after a certain number of tries, it will double the search area and try again. This way, we can be sure that we will eventually find a suitable coordinate, even if it takes a while.

But you might rightly be wondering what `isTooClose`, `getPlayerPosition`, `getPlayerRadius`, `getSporePosition`, and `getSporeRadius` are. These are helper functions that let us check if a coordinate is too close to any of the objects in the collections passed in. Let's define these functions now.

```directory
/server/internal/server/objects/spawn.go
```

```go
func isTooClose[T any](x float64, y float64, radius float64, objects *SharedCollection[T], getPosition func(T) (float64, float64), getRadius func(T) float64) bool {
    // Not too close if there are no objects
    if objects == nil {
        return false
    }

    // Check if any object is too close
    tooClose := false
    objects.ForEach(func(_ uint64, object T) {
        if tooClose {
            return
        }

        objX, objY := getPosition(object)
        objRad := getRadius(object)
        xDst := objX - x
        yDst := objY - y
        dstSq := xDst*xDst + yDst*yDst

        if dstSq <= (radius+objRad)*(radius+objRad) {
            tooClose = true
            return
        }
    })

    return tooClose
}
```

The `isTooClose` function simply tells us whether a circle with the given position and radius would overlap with any of the objects in the provided collection. The `getPosition` and `getRadius` functions are passed in as arguments so that we can use this function with any type of object that has a position and radius. An alternative strategy would be to use interfaces, but it can quickly become cumbersome to work with, so while this approach isn't great, it's going to have to do for now.

```directory
/server/internal/server/objects/spawn.go
```

```go
var getPlayerPosition = func(p *Player) (float64, float64) { return p.X, p.Y }
var getPlayerRadius = func(p *Player) float64 { return p.Radius }
var getSporePosition = func(s *Spore) (float64, float64) { return s.X, s.Y }
var getSporeRadius = func(s *Spore) float64 { return s.Radius }
```

And that's it! Remember the whole point of this exercise is to make sure that players and spores don't spawn inside each other, so we'd better go and use our new `SpawnCoords` function in the `InGame` state's `OnEnter` method.

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) OnEnter() {
    // ...
    // Set the initial properties of the player
    g.player.X, g.player.Y = objects.SpawnCoords(g.player.Radius, g.client.SharedGameObjects().Players, nil)
    // ...
}
```

We now need to fix up the spore spawning logic, which was already using the old version of `SpawnCoords`. Let's update that now.

```directory
/server/internal/server/hub.go
```

```go
func (h *Hub) newSpore() *objects.Spore {
    // ...
    x, y := objects.SpawnCoords(sporeRadius, h.SharedGameObjects.Players, h.SharedGameObjects.Spores)
    // ...
}
```

This will ensure that spores don't spawn inside players or other spores, which should give us a much nicer distribution of spores around the map and stop from larger players becoming even larger when we add spore replenishment logic next.

And there we have it! When we run the game now, players should no longer spawn inside each other, and we should notice the pattern of spores around the map looks much less clumpy. We are now ready to implement spore respawning.

## Replenishing spores

The last thing we need to do today is to make sure that the number of spores on the map stays more-or-less constant. We can achieve that by running a loop on the hub that checks the rough number of spores in the shared collection every few seconds, and adds back any that are missing. Let's start by adding a new method to the `Hub` struct that will do this.

```directory
/server/internal/server/hub.go
```

```go
import (
    // ...
    "time"
    // ...
)

func (h *Hub) replenishSporesLoop(rate time.Duration) {
    ticker := time.NewTicker(rate)
    defer ticker.Stop()

    for range ticker.C {
        sporesRemaining := h.SharedGameObjects.Spores.Len()
        diff := MaxSpores - sporesRemaining

        if diff <= 0 {
            continue
        }

        log.Printf("%d spores remain - going to replenish %d spores\n", sporesRemaining, diff)

        // Don't really want to spawn too many at a time, otherwise it can cause a lag spike
        for i := 0; i < min(diff, 10); i++ {
            spore := h.newSpore()
            sporeId := h.SharedGameObjects.Spores.Add(spore)

            h.BroadcastChan <- &packets.Packet{
                SenderId: 0,
                Msg:      packets.NewSpore(sporeId, spore),
            }

            // Sleep a bit to avoid lag spikes
            time.Sleep(50 * time.Millisecond)
        }
    }
}

```

If we call this method in the background, it will go ahead and replenish spores at a supplied rate if there are fewer than the maximum number of spores on the map. We are also adding a small sleep between each spore spawn to avoid lag spikes, which can happen if we spawn too many spores at once. For every new spore we spawn, we are also broadcasting the event to all clients, so they can add the spore to their local collections. The special `SenderId` of 0 indicates that the event is coming from the server.

Let's call this method in the `Hub`'s `Run` method to make the loop run every 2 seconds (feel free to adjust this rate to your liking).

```directory
/server/internal/server/hub.go
```

```go
func (h *Hub) Run() {
    // ...
    go h.replenishSporesLoop(2 * time.Second)
    // ...
}
```

Now we just need to make sure we handle the spore messages in the `InGame` state's `HandleMessage` method.

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    // ...
    case *packets.Packet_Spore:
        g.handleSpore(senderId, message)
    }
}

func (g *InGame) handleSpore(senderId uint64, message *packets.Packet_Spore) {
    g.client.SocketSendAs(message, senderId)
}
```

This is a very simple handler that just forwards the spore message to the client. We don't need to do anything else because the client is already configured to handle spore messages, since we wrote the handler in <a href="/2024/11/14/godot-golang-mmo-part-7#handle-spores" target="_blank">the last part</a>.

So now, if you run the game, you should see that the number of spores on the map stays more-or-less constant, and you should be able to see them spawning in from time to time around the map.

And that's it for today! We've allowed players to eat each other and grow (all validated by the server), and we've addressed some issues with spawning and spore replenishment. The game is starting to look like a competitive MMO, and we are well on our way to having a complete game. In <strong><a href="/2024/11/16/godot-golang-mmo-part-9" class="sparkle-less">the next part</a></strong>, we will add a hiscore system to the game, so players can compete to be the best in the game. Until then, happy coding!

---

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.
