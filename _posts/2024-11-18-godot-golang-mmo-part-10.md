---
title: "§10 Add the Final Touches to Your Godot 4 Go MMO"
description: "As we approach the finish line, we’ll implement friend search functionality and finalize the core features of our MMO."
redditurl: 
project: godot4golang
---

{% include math.html %}

This is the last part of the series we will concern ourselves with adding new features to the game. We just have two more features to add, and then we will move on to polishing everything up and deploying the game over the next two parts.

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
{% include img.html src="posts/2024/11/18/browsing_hiscores_scene.png" alt="Browsing hiscores scene" %}

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
  <source src="/assets/images/posts/2024/11/18/ch10-hw.webm" type="video/webm">
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

var underneath_player: bool

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

Now we can use this new flag to determine whether the player should consume the spore or not. We can add a check to the `_consume_spore` method in the InGame state script:

```directory
/client/states/ingame/ingame.gd
```
```gdscript
func _consume_spore(spore: Spore) -> void:
    if spore.underneath_player:
        return
    # ...
```

Here, we just exit the method early if the spore is underneath the player. This will prevent the player from consuming the spore if it is underneath them.

So now, in a perfect world, we would be finished with this feature! Here's a video of the spores dropping from various players, and the players losing mass over time as they consume the spores (I have increased the spore drop rate for demonstration purposes):

<video controls>
  <source src="/assets/images/posts/2024/11/18/client-eating.webm" type="video/webm">
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

Now, over to the spore consumption validation logic we implemented in <a href="/2024/11/15/godot-golang-mmo-part-8#spore-consumption-validation" target="_blank">§08</a>. We will add a new check to ensure that the spore wasn't dropped after the time it takes for the player to travel combined radius of the player and the spore. This works because the minimum distance the player has to travel such that the spore is not underneath them is their own radius, then the spore's radius. Then, best case scenario, the player turns around instantly and consumes the spore.

We know the player's speed in units per second, since the server assigns it to the player. Rearranging the simple formula $$\text{distance} = \text{speed} \times \text{time}$$, we know that $$\text{time} = \frac{\text{distance}}{\text{speed}}$$. So, the minimum time (in seconds) it should take for the player to consume the spore is the sum of the radii of the player and the spore, divided by the player's speed. We will add this check to the `handleSporeConsumed` method:

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

We also include a buffer distance in this check, to allow for a little of leeway in case the server isn't synced perfectly with the client. This buffer is set to 10 units, but you can adjust this value to your liking.

Now, if you run the game, you shouldn't see any difference. The spores will still drop, and the players will still consume them. However, if you were to modify the client to consume spores that are underneath them (i.e. undo the changes we made to the client just above), you'll see the server complaining about the player dropping the spore too recently, and the player will appear to consume the spore but keep shrinking regardless. Any players witnessing this will see the player shrinking, but the dropped spores will still be there.

## Searching the leaderboard

Our leaderboard currently shows the top 10 players, but it would be even more exciting if we could search for a specific player who maybe isn't in the top 10. This is what we will be going for in this session.

<video controls>
  <source src="/assets/images/posts/2024/11/18/hiscores_demo.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

We're going to need a few things to make this work:
1. A new packet to send the search query to the server
2. A new query on the database to search for the player
3. A new method on the server to handle the search query
4. A search bar on the client to send the search query
5. A way to highlight the searched player in the leaderboard

Let's get started and tackle these one by one.

### Hiscores search packet

This will be another simple packet, with the only data being the name of the player we want to search for:

```directory
/shared/packets.proto
```

```protobuf
message SearchHiscoreMessage { string name = 1; }

message Packet {
    // ...
    oneof msg {
        SearchHiscoreMessage search_hiscore = 18;
    }
}
```

### Hiscores search query

We need a query to retrieve the player's rank from the database. We will be able to use that to determine the offset to use in the leaderboard results to send back to the client. Let's go ahead and try to write this query:

```directory
/server/internal/db/config/queries.sql
```

```sql
-- name: GetPlayerByName :one
SELECT * FROM players
WHERE name LIKE ?
LIMIT 1;

-- name: GetPlayerRank :one
SELECT COUNT(*) + 1 AS "rank" FROM players
WHERE best_score > (
    SELECT best_score FROM players p2
    WHERE p2.id = ?
);
```

The `GetPlayerByName` is more of a helper query, used as a stepping stone to get the player's rank. The only thing to note here is we are using the `LIKE` operator to make the search case-insensitive.

The `GetPlayerRank` query is a bit more complex than the queries we've seen so far, but it is still quite simple. We are using a subquery to get the player's best score, then counting the number of players with a better score than that player. We add 1 to the count to get something starting from 1, rather than 0.

### Hiscores search handler

In our `BrowsingHiscores` state handler on the server, we will need to add a new case to handle the search query:

```directory
/server/internal/server/states/browsingHiscores.go
```

```go
func (b *BrowsingHiscores) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    // ...
    case *packets.Packet_SearchHiscore:
        b.handleSearchHiscores(senderId, message)
    }
}

func (b *BrowsingHiscores) handleSearchHiscores(_ uint64, message *packets.Packet_SearchHiscore) {
    player, err := b.queries.GetPlayerByName(b.dbCtx, message.SearchHiscore.Name)

    if err != nil {
        b.logger.Printf("Error getting player %s: %v\n", message.SearchHiscore.Name, err)
        b.client.SocketSend(packets.NewDenyResponse("No player found with that name"))
        return
    }

    playerRank, err := b.queries.GetPlayerRank(b.dbCtx, player.ID)
    if err != nil {
        b.logger.Printf("Error getting rank for player %s: %v\n", message.SearchHiscore.Name, err)
        b.client.SocketSend(packets.NewDenyResponse("Player is unranked"))
        return
    }

    const limit int64 = 10
    offset := playerRank - limit/2
    b.sendTopScores(limit, max(0, offset))
}
```

This code simply retrieves the player's rank from the database using the queries we wrote above, then sends the 10 players surrounding that player to the client. If the player happens to be in the top 5 players, the offset calculation needs to be adjusted to ensure we don't send negative offsets to the database.

You will notice we are referring to a function that does not exist yet: `b.sendTopScores`. This is because we are going to refactor slightly to extract the `OnEnter` logic into a separate method so that we can reuse it for the search query. Let's do that now. Simply replace the `OnEnter` method with the following:

```directory
/server/internal/server/states/browsingHiscores.go
```

```go
func (b *BrowsingHiscores) OnEnter() {
    b.sendTopScores(10, 0)
}
```

Now we can add the `sendTopScores` method which will contain the logic that previously was in the `OnEnter` method:

```directory
/server/internal/server/states/browsingHiscores.go
```

```go
func (b *BrowsingHiscores) sendTopScores(limit int64, offset int64) {
    topScores, err := b.queries.GetTopScores(b.dbCtx, db.GetTopScoresParams{
        Limit:  limit,
        Offset: offset,
    })
    if err != nil {
        b.logger.Printf("Error getting top %d scores from rank %d: %v\n", limit, offset+1, err)
        b.client.SocketSend(packets.NewDenyResponse("Failed to get top scores - please try again later"))
        return
    }

    hiscoreMessages := make([]*packets.HiscoreMessage, 0, limit)
    for rank, scoreRow := range topScores {
        hiscoreMessage := &packets.HiscoreMessage{
            Rank:  uint64(rank) + uint64(offset) + 1,
            Name:  scoreRow.Name,
            Score: uint64(scoreRow.BestScore),
        }
        hiscoreMessages = append(hiscoreMessages, hiscoreMessage)
    }

    b.client.SocketSend(packets.NewHiscoreBoard(hiscoreMessages))
}
```

Now, we shouldn't have any problems running our game and browsing the leaderboard as we did before. We're done with the server side of things, so let's move on to the client.

### Hiscores search bar

Let's go ahead and add some more UI to the hiscores scene to allow players to search for a player. We will group the exiting back button, with the new search bar and search button, in a `HBoxContainer` which will sit at the top of the `VBoxContainer`. Your scene tree should look like this:

- **Node** - called `BrowsingHiscores`
  - **CanvasLayer** - called `UI`
    - **VBoxContainer**
      - **HBoxContainer**
        - **Button** - called `BackButton`
        - **LineEdit**
        - **Button** - called `SearchButton`
      - **Hiscores**

The **LineEdit** node's **Expand** property should be enabled underneath the **Layout** > **Container Sizing** > **Horizontal** section of the inspector, or via the sizing settings button at the top of the scene editor.

The **SearchButton** node should have its **Text** property set to "Search".

{% include img.html src="posts/2024/11/18/hiscores_scene_tree.png" alt="Hiscores scene tree" %}

Now, we will have knocked loose the reference to the `BackButton` node in the script, so we need to fix that and add the new search button and line edit nodes:

```directory
/client/states/browsing_hiscores/browsing_hiscores.gd
```

```gdscript
@onready var _back_button := $UI/VBoxContainer/HBoxContainer/BackButton as Button
@onready var _line_edit := $UI/VBoxContainer/HBoxContainer/LineEdit as LineEdit
@onready var _search_button := $UI/VBoxContainer/HBoxContainer/SearchButton as Button

func _ready() -> void:
    _line_edit.text_submitted.connect(_on_line_edit_text_submitted)
    _search_button.pressed.connect(_on_search_button_pressed)
    # ...

func _on_line_edit_text_submitted(_new_text: String) -> void:
    _on_search_button_pressed()

func _on_search_button_pressed() -> void:
    var packet := packets.Packet.new()
    var search_hiscore_msg := packet.new_search_hiscore()
    search_hiscore_msg.set_name(_line_edit.text)
    WS.send(packet)
```

This code will send the search query to the server when the search button is pressed, or when the user presses Enter in the line edit. When the server responds, we are already mostly set up to handle the response, since we are listening to `HiscoreBoardMessage`s already <small>(although there are some issues)</small>. We just need to handle the case where the server responds with a `DenyResponse`.

Let's add a `Log (log.gd)` node to the scene, just under the `Hiscores` node, and set its **Custom Minimum Size**'s **y** value to, say, 100px. This will allow us to display the error message to the player if the server responds with a `DenyResponse`. 
{% include img.html src="posts/2024/11/18/hiscores_scene_tree_log.png" alt="Hiscores scene tree with log node" %}

We will also need to add a new method to handle this response:

```directory
/client/states/browsing_hiscores/browsing_hiscores.gd
```

```gdscript
@onready var _log := $UI/VBoxContainer/Log as Log

func _handle_deny_response(deny_response_msg: packets.DenyResponseMessage) -> void:
    _log.error(deny_response_msg.get_reason())
```

Now, when you run the game, you should have no problem searching for an existent-or-non-existent player, and the server should respond with the appropriate message. The only problem is, the leaderboard kinda just throws new entries in with the old ones, and you can end up in situations where there are more than 10 entries present, not necessarily consecutive. To fix this, we simply need to clear the leaderboard before adding the new entries. We haven't built a method to do this yet, but it should be quite simple to implement. We will add a new method to the `hiscores.gd` script:

```directory
/client/classes/hiscores/hiscores.gd
```

```gdscript
func clear_hiscores() -> void:
    _scores.clear()
    for entry in _vbox.get_children():
        if entry != _entry_template:
            entry.free()
```

Note we are being careful not to remove the template entry, as that's what we use when creating new entries. Now, we just need to call this method before adding the new entries in the `handle_hiscore_board` method:

```directory
/client/states/browsing_hiscores/browsing_hiscores.gd
```

```gdscript
func _handle_hiscore_board_msg(hiscore_board_msg: packets.HiscoreBoardMessage) -> void:
    _hiscores.clear_hiscores()
    # ...
```

Now, we should have a fully functioning search feature in our game! It will always return a window of the dataset, centered about our player of interested. But it's not so obvious that this is the case because it's not highlighted in any way. Let's add a highlight to the searched player in the leaderboard.

### Highlighting the searched player

We will finally modify the `set_hiscore` method in the `hiscore_entry.gd` script to optionally highlight the entry. We can then use that to decide whether to highlight the hiscore entry received from the server, based on what we have in the search bar. Let's add a new parameter to the `set_hiscore` method:

```directory
/client/classes/hiscores/hiscores.gd
```

```gdscript
func set_hiscore(name: String, score: int, highlight: bool = false) -> void:
    # ...
    _add_hiscore(name, score, highlight)

func _add_hiscore(name: String, score: int, highlight: bool) -> void:
    # ...
    if highlight:
        name_label.add_theme_color_override("font_color", Color.YELLOW)
```

Now, we just need to modify the `handle_hiscore_board` method to highlight the searched player (it's best to refactor a bit here, so I'll show the full method):

```directory
/client/states/browsing_hiscores/browsing_hiscores.gd
```

```gdscript
func _handle_hiscore_board_msg(hiscore_board_msg: packets.HiscoreBoardMessage) -> void:
    _hiscores.clear_hiscores()
    for hiscore_msg: packets.HiscoreMessage in hiscore_board_msg.get_hiscores():
        var name := hiscore_msg.get_name()
        var rank_and_name := "%d. %s" % [hiscore_msg.get_rank(), name]
        var score: int = hiscore_msg.get_score()
        var highlight := name.to_lower() == _line_edit.text.to_lower()
        _hiscores.set_hiscore(rank_and_name, score, highlight)
```

So now, when you search for a player, the middle entry, the one you searched for, will be highlighted in yellow.
{% include img.html src="posts/2024/11/18/hiscores_search_highlight.png" alt="Hiscores search highlight" %}

## Conclusion

So that ticks off everything we wanted to in this post! We added a new mechanic to keep players engaged, and a search feature to encourage competition and social interaction.

Even though we have a fully functioning game at this point, there is still much to be desired in the looks department. In <strong><a href="/2024/11/20/godot-golang-mmo-part-11" class="sparkle-less">the next part</a></strong>, we will focus purely on polishing up anything that needs it, and making the game look as good as possible. This will set us up nicely for the final part, where we will deploy the game and make it available for others to play. Until then, good luck with your game development!

--- 

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.
