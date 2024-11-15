---
title: §8 Adding Scores and Competition to Golang MMO with Godot 4
description: We are going to let our players grow and fight to be the best in the game, all while letting the Go server validate what's happening to prevent cheating.
redditurl: 
---

Welcome back! In the [last part](/2024/11/14/godot-golang-mmo-part-7), we added spores to our game, and gave players the opportunity to eat them. Today, we are going to expand upon that by letting the server decide if the player should grow after eating spores, then tell all other players about the change. This inherently will give rise to the concept of scores, and combined with the possibility for players to eat each other, we will have a competitive game.

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

Now, the handler method is going to have to check a few things:
1. Does the spore the player said they ate *actually exist*?
2. Was the player anywhere *near* the spore they said they ate?
3. If the player ate the spore, how much should they grow?

So it's clear we're going to need some new methods to help us with this. Let's start with the first one, which will check if the spore exists.

### 1. Does the spore exist?
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
![Circle collision diagram](/assets/css/images/posts/2024/11/15/combinedRadii.svg)

In the diagram, it is clear that the distance between the two circles is $$\text{pRad} + \text{buffer} + \text{sRad}$$, a.k.a. `player.Radius + buffer + objRadius`. If the real distance (calculated by the Pythagorean theorem) is greater than this threshold, then the player is not close enough to the object.

### 3. How much should the player grow?

I've been looking forward to this part for a while, because I can finally put my degree in math to good use. Well, not really, it's more like high school level math, but hey, it's fun nonetheless. We need to be able to calculate the player's new radius based on the size of what they just ate. 

When the player consumes something, they absorb its mass. For the sake of this game, let's assume the mass of players and spores is proportional to their area. This means that
* if the player's original radius is $$R_0$$, their original is $$M_0 = \pi R_0^2$$
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

So, we'll need a method to calculate $M_0$ and $m$, let's call that `radToMass`, and another method to calculate $R_1$, call it `massToRad`.

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
        g.logger.Println("Received spore consumption message from another player, ignoring")
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
    
    updatePacket := packets.NewPlayer(g.client.Id(), g.player)
    g.client.Broadcast(updatePacket)
    go g.client.SocketSend(updatePacket)
}
```

We are using a strategy where we check for the easiest things first, and if we fail at any point, we return early. This way, we can avoid making the server crunch numbers unnecessarily. If we make it to the end, we can be confident that the player's growth is valid, and we can broadcast the change to all players (including the player who grew: we already have logic on the client side to update the player's size, so we might as well use it).

We are also using goroutines for things that don't need to be done synchronously, like removing the spore from the hub and sending the update packet to the client. This way, we can keep the server responsive and not block it on I/O operations or waiting to acquire locks. We don't really care about the outcome or order of these operations, so we can justify firing and forgetting them.

Note that we are not doing anything when we detect foul play, but you could consider having a system to penalize players who cheat. For now, we are just logging the error and moving on. It would cause the cheater's game to go out of sync with the server (because on the client side, the spores they collide with would still be there), but so be it; they don't deserve a pristine experience if they are going to cheat!

