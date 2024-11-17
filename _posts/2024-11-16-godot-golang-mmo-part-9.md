---
title: §09 Adding a hiscore leaderboard to our MMO made with Godot and Golang
description: Let's add a browsable, searchable, hiscore leaderboard to our MMO, so players can see how they rank against others.
redditurl: 
---

We are approaching the end of this series, having just finished [allowing players to eat each other and grow in size](/2024/11/15/godot-golang-mmo-part-8), but we are still lacking a permanent way for players to see how they rank against others. I think it's time to add a hiscore leaderboard to our game, so let's get started!

## The plan

Our goal by the end of this part is to have a hiscore leaderboard that players can access from the main menu. It will look something like this (though the design will be a bit rough until we get a chance to polish everything in an upcoming part):
![Hiscore leaderboard](/assets/css/images/posts/2024/11/16/hiscore-leaderboard.png)

To pull this off, we are going to need a few things, which we will tackle in order:

1. A new class in Godot to format and display the leaderboard. This can be versatile enough to display both in-game and in the main menu
2. A player's best score needs to be saved to the database, so a new table for player information, associated with the user who is playing
3. New SQL queries to save and fetch players' hiscores
4. New protobuf messages to handle requesting and sending hiscores
5. A new state in the server to handle hiscore requests
6. A new state in the client to display the hiscore leaderboard and handle hiscore responses

We have a lot of work ahead of us, but we are going to use everything we have learned so far to make this happen. Let's get started!

## The leaderboard class

Similar to the `Log` class we created back in <a href="/2024/11/09/godot-golang-mmo-part-3#building-a-custom-log-scene-in-godot" target="_blank">§03</a>, we are going to create a new class in Godot to handle the leaderboard. The class itself won't be responsible for fetching any information from the server, but it will be a place for us to store data into and have it display in a table format. This means we can put it into the game straight away to keep track of live, *current* scores, and then later we will use it in the main menu to display players' *best* scores.

1. Create a new folder at `res://classes/hiscores/`
2. Right-click the new `hiscores` folder and select **Create new...** and then **Scene**
3. Enter *hiscores** as the name of the scene
4. Choose **ScrollContainer** as the root node
5. Click **OK**

![Hiscores scene](/assets/css/images/posts/2024/11/16/hiscores-scene.png)

We will set the scroll container to take up the screen's entire area, but when we add it to other scenes, we can resize it as needed. To do this, simply use the **Full Rect** anchor preset at the top of the scene editor when you have the root node selected.

Also ensure the **Shrink Begin** and **Expand** options are selected for the **Vertical** container sizing option in the inspector (under "Layout"), or simply use the handy **Sizing settings** button at the top of the scene editor to set it. This will allow the hiscore board to be resized and positioned correctly when we add it to other scenes.

![Hiscores scene full rect](/assets/css/images/posts/2024/11/16/hiscores-scene-full-rect.png)

Now go ahead and add the following nodes so that the scene tree looks like this:

- **ScrollContainer** - called `Hiscores`
  - **VBoxContainer**
    - **HBoxContainer**
      - **Label** - called `Name`
      - **Label** - called `Score`

Right now, everything is all clumped together, so let's fix the layout.

1. Select the **VBoxContainer** node and choose the **Fill** and **Expand** options for both horizontal and vertical alignment in the **Container Sizing** section of the inspector (under "Layout"), or simply use the handy **Sizing settings** button at the top of the scene editor.
   ![VBoxContainer sizing settings](/assets/css/images/posts/2024/11/16/vboxcontainer-sizing-settings.png)

2. For the **HBoxContainer**, simply choose **Shrink Begin** for the **Vertical** container size, and don't change anything else. This will force each row to stay the same height, one after the other.

3. The **Name** label should have **Fill** and **Expand** selected for the horizontal alignment, so that it pushes the adjacent score label to the right. Also set the **Custom minimum size**'s **x** value (also under "Layout" in the inspector) to 150px to give it a bit of space to start out.
    ![Name label sizing settings](/assets/css/images/posts/2024/11/16/name-label-sizing-settings.png)

4. Finally, set the **Score** label to **Shrink End** for the horizontal alignment, so that it doesn't take up any more space than it needs to.

If you enter some dummy data into the labels, and duplicate the **HBoxContainer** a few times, you should see something like this:
![Hiscores scene with dummy data](/assets/css/images/posts/2024/11/16/hiscores-scene-dummy-data.png)

Remove the duplicate **HBoxContainer** nodes if you added them, and remember to save the scene. Let's add a new script at `res://classes/hiscores/hiscores.gd` and attach it to the root node.

```directory
/client/classes/hiscores/hiscores.gd
```

```gdscript
class_name Hiscores
extends ScrollContainer

var _scores: Array[int]

@onready var _vbox := $VBoxContainer as VBoxContainer
@onready var _entry_template := $VBoxContainer/HBoxContainer as HBoxContainer

func _add_hiscore(name: String, score: int) -> void:
    _scores.append(score)
    _scores.sort()
    var pos := len(_scores) - _scores.find(score) - 1 # -1 to keep real entries above the template
    
    var entry: HBoxContainer = _entry_template.duplicate()
    var name_label: Label = entry.get_child(0)
    var score_label: Label = entry.get_child(1)
    
    _vbox.add_child(entry)
    
    _vbox.move_child(entry, pos)
    
    name_label.text = name
    score_label.text = str(score)
    
    entry.show()
```

So far, the script isn't too complicated. We are internally keeping track of scores in an array, which we sort each time a new score is added. This ensures that the hiscore entries are added in the correct order. The private `_add_hiscore` function is responsible for doing just that: it takes a name and a score, adds it to the internal array, finds the position in the scene tree where it should be inserted, then puts a modified copy of the entry template there.

We will not be calling this function externally, however, as we are going to instead call something more versatile: `set_hiscore`. 

```gdscript
func set_hiscore(name: String, score: int) -> void:
    remove_hiscore(name)
    _add_hiscore(name, score)
```

This function will remove any existing hiscore entry for the given name, then add the new one. This way, we can update a player's score without having to worry about duplicates. But we obviously need to add the `remove_hiscore` function as well:

```gdscript
func remove_hiscore(name: String) -> void:
    for i in range(len(_scores)):
        var entry := _vbox.get_child(i)
        var name_label := entry.get_child(0)
        
        if name_label.text == name:
            _scores.remove_at(len(_scores) - i - 1)
            
            entry.free()
            return
```

This very simple function iterates through the hiscore entries, finds the one with the matching name, removes it from the internal array, then removes it from the scene tree.

Let's test this out by adding our new hiscores scene to the `Connected` scene somewhere. I added it to the bottom of the `Connected` scene's **VBoxContainer**, just below the `Log` node. 
> Note that, unlike the `Log` node, we need to click and drag the `Hiscores` scene from the file system to the scene tree to add the entire scene, along with its children. If you simply try and add a new **Hiscores** node, it will not come with any of the children we set up in the scene editor, therefore it will not work. We were able to get away with this for the `Log` node because it was a single node with no children.

Also be sure to set the **Custom Minimum Size**'s **y** value (under "Layout" in the inspector) to 200px to allow some entries to be visible.
![Hiscores test scene](/assets/css/images/posts/2024/11/16/hiscores-test-scene.png)

Then, I added the following test code to the `_ready` function in `res://states/connected/connected.gd`:

```directory
/client/states/connected/connected.gd
```

```gdscript
func _ready() -> void:
    # ...
    
    var _hiscores := $UI/VBoxContainer/Hiscores as Hiscores
    _hiscores.set_hiscore("Bob Barker", 10000)
    _hiscores.set_hiscore("Adam Sandler", 5000)
    _hiscores.set_hiscore("Tristan", 5001)
```

Now, when I run the game, I should expect to see "Bob Barker" at the top of the hiscore list, followed by "Tristan" and then "Adam Sandler", which is half what I see. I also see the placeholder text at the bottom of the list, which obviously isn't what we want. 
![Hiscores scene with test data](/assets/css/images/posts/2024/11/16/hiscores-scene-test-data.png)

Let's fix that by simply clicking the 👁️ icon to the right of the **HBoxContainer** template in the scene editor of the **Hiscores** scene. This will hide the placeholder entry and make everything right with the world.
![Hiscores scene with test data hidden](/assets/css/images/posts/2024/11/16/hiscores-scene-test-data-hidden.png)

You might instead want to keep them visible while you are working on the scene, and hide them programmatically, so for that, feel free to add the following to the `_ready` function in `res://classes/hiscores/hiscores.gd`:

```directory
/client/classes/hiscores/hiscores.gd
```

```gdscript
func _ready() -> void:
    _entry_template.hide()
```

Make sure to remove the test code from the `_ready` function in `res://states/connected/connected.gd`, and remove the **Hiscores** scene from the `Connected` scene, as that was just a test. Let's actually add it to the game now.

## Adding live scores to the game

We are already able to drop in our new **Hiscores** scene to our **InGame** state scene, but first we will need a little restructuring to make it easier to manage the positioning of the elements. Restructure the `UI` canvas layer in the **InGame** scene so that it looks like this:
- **UI** - called `UI`
  - **VBoxContainer**
    - **LineEdit**
    - **Hiscores**
    - **Log**

1. Choose the **Full Rect** anchor preset for the **VBoxContainer** node 
2. Choose the **Shrink End** container sizing option for both the **Vertical** and **Horizontal** options for the **Hiscores** node
3. Set the **Custom Minimum Size**'s **x** value to 200px for the **Hiscores** node
4. Set the  **Custom Minimum Size**'s **y** value to 150px for the **Hiscores** node

![New InGame scene](/assets/css/images/posts/2024/11/16/new-ingame-scene.png)

Now, we will have broken our `ingame.gd` script by moving the LineEdit and Log nodes under the VBoxContainer, so let's fix that as well as add a reference to our new Hiscores node.

```directory
/client/states/ingame/ingame.gd
```

```gdscript
@onready var _line_edit := $UI/VBoxContainer/LineEdit as LineEdit
@onready var _log := $UI/VBoxConainter/Log as Log
@onready var _hiscores := $UI/VBoxContainer/Hiscores as Hiscores
```

Now, whenever we update an actor's mass, we should also update the hiscore list. Luckily we have a function called `_set_actor_mass` already, so let's add to that:

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _set_actor_mass(actor: Actor, new_mass: float) -> void:
    # ...
    _hiscores.set_hiscore(actor.actor_name, roundi(new_mass))
```

Now, whenever an actor's mass changes, the hiscore list will update accordingly. But we also need to remove the actor from the hiscores when they are removed from the game, so go ahead and add a similar line to the `_remove_player` function:

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _remove_player(actor: Actor) -> void:
    # ...
    _hiscores.remove_hiscore(actor.actor_name)
```

Now, when we run the game, we should see the hiscore list updating as we eat things, and it should dynamically sort itself as different players overtake each other.

There is just one problem, which is that the player's hiscore won't be added when they first join the game - only when they first eat something. Harder to notice is the fact that radius updates from the server (e.g. if an actor's radius is mismatched from the client) won't update the hiscore list either. Both of these are due to the fact that we are setting the actor's radius directly rather than via the `_set_actor_mass` function. Luckily, it is easy to fix, since we just need to use the `_rad_to_mass` function to calculate the mass from the radius, then call `_set_actor_mass` with the result.

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _add_actor(actor_id: int, actor_name: String, x: float, y: float, radius: float, speed: float, is_player: bool) -> void:
    var actor := Actor.instantiate(actor_id, actor_name, x, y, radius, speed, is_player)
    _set_actor_mass(actor, _rad_to_mass(radius))
    # ...

func _update_actor(actor_id: int, x: float, y: float, direction: float, speed: float, radius: float, is_player: bool) -> void:
    var actor := _players[actor_id]
    _world.add_child(actor)
    actor.radius = radius
    _set_actor_mass(actor, _rad_to_mass(radius))
    # ...
```

That should be everything we need to add live hiscores to the game. Here's what it looks like now:
<video controls>
  <source src="/assets/css/images/posts/2024/11/16/ingame-hiscores.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

Now, let's tackle stage 2 of our plan: saving the player's best score to the database.

## Saving players in the database

We are going to need a new table in the database to store player information, including their best score. Later on, we will want to save more information, like when we add character customization, but for now, we will just save the player's name and their best score.

It's been a while since we've done this; we first set up the database in <a href="/2024/11/10/godot-golang-mmo-part-5#schema-setup" target="_blank">§05</a>, so let's refresh our memory on how to do this.

Open up the `schema.sql` config file in our `/server/internal/db/config/` directory. Recall this is where we give the definition of all the tables we want to create in our database. Add the following to the bottom of the file:

```directory
/server/internal/db/config/schema.sql
```

```sql
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL UNIQUE,
    best_score INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

This will create a table called `players` with the following structure:

| Column Name | Data Type | Description |
| --- | --- | --- |
| id | int | A unique identifier for the player |
| name | string | The name of the player |
| best_score | int | The player's best score of all time |
| user_id | int | A reference to the user who owns this player |

Including the `user_id` column will allow us to easily associate a player with a user, which can be useful for things like finding the player a particular user is playing as, or for deleting all of a user's players when they delete their account, etc. We probably won't use it in this series, but it's good to have it there for future reference.

Now, if we simply re-run the server, it will automatically create the table for us, but no data will be added to it. We obviously have a few users in the database at this point, but none of them will magically have a player associated with them. Typically, manipulating data after the fact, especially on a production server, is done with what's called a "migration". `sqlc` does not support migrations, and I personally think they are a bit overkill for a small project like this, so we will simply delete the database and start fresh. If you are working on a production server, you could hand-write a migration script to populate the `players` table with the necessary data, or check if a user has a player associated with them when they log in, and create one if they don't.

To delete the database, simply remove the `db.sqlite` file in the `/server/cmd/` directory, then re-run the server. This will create a new, empty database for us to work with.

To save a player to the database, we will need to add a new SQL query to the `queries.sql` file in the `/server/internal/db/` directory. This query will insert a new player into the `players` table, and return the new player to us. 

```directory
/server/internal/db/queries.go
```

```sql
-- name: CreatePlayer :one
INSERT INTO players (
    user_id, name
) VALUES (
    ?, ?
)
RETURNING *;
```

This query is very simple, since we only need to specify the player's user ID and name. All other fields have default values, so we don't need to worry about them.

Run the following command from the root of the project to generate a new Go function called `CreatePlayer` in our `db` package:

```bash
sqlc generate -f server/internal/server/db/config/sqlc.yml
```

Now, we can actually use this query to create a new player when a new user registers. Let's revisit the `Connected` state and find the `handleRegister` function. We will create the player right near the end of the function, after we create the user and immediately before we send the `Ok` packet back to the client.

```directory
/server/internal/server/states/connected.go
```

```go
func (c *Connected) handleRegister(senderId uint64, message *packets.Packet_RegisterRequest) {
    // ...

    _, err = c.queries.CreatePlayer(c.dbCtx, db.CreatePlayerParams{
        UserID: user.ID,
        Name:   message.RegisterRequest.Username,
    })

    if err != nil {
        c.logger.Printf("Failed to create player for user %s: %v\n", username, err)
        c.client.SocketSend(genericFailMessage)
        return
    }
    
    // ...
}
```

You will probably have not declared the `user` variable, since we weren't doing anything with the result of the `CreateUser` response, we simply threw it away before. But now we need its ID to create the players, so instead of the line `_, err = c.db.CreateUser(...)`, simply change it to `user, err := c.db.CreateUser(...)`.

Also, note we are using the `message.RegisterRequest.Username` as the player's name. This is the string that the client sent to the server, before we validated it and transformed it to lowercase. This is ideal for the player name, since it may have stylistic capitalization that the user wants to keep, which is fine for the player name, but not for the username.

## Tracking hiscores in the database

Now that we have a way to create players in the database, we need to update the player's best score whenever they eat something. We will need a new query to update the player's best score, and we will need to call this query whenever a player's mass changes. 

But we only want to update the player's best score if the new mass is greater than the current best score. So how do we get that? We could query the database every time we want to update the player's best score, but that seems like a lot of unnecessary work. Instead, we can keep track of the player's best score in the `objects.Player` struct, which is retrieved from the database when the player logs in. This way, we can simply compare the new mass to the player's best score, and only update the database if the new mass is greater.

So let's add some new fields to the `objects.Player` struct to help keep track of the player's best score.

```directory
/server/internal/server/objects/gameObjects.go
```

```go
type Player struct {
    // ...
    DbId      int64
    BestScore int64
}
```

We are adding a new field called `DbId`, which will store the player's ID in the database. This will be useful for making queries that require the player's ID, like updating the player's best score. We are also adding a new field called `BestScore`, which is more self-explanatory.

We will also need a new query to get a player based on their ID (we limited the query to one result, since we are only ever going to get one player with a given ID). 

```directory
/server/internal/db/queries.go
```

```sql
-- name: GetPlayerByUserID :one
SELECT * FROM players
WHERE user_id = ? LIMIT 1;
```

Remember to compile the queries again as we did above, before moving on to the next step.

Now, when we handle the login request in the `Connected` state, let's retrieve the player's best score from the database and store it in the `Player` struct we pass to the `InGame` state. So enter the following code at the end of the `handleLogin` function, after we send the `Ok` response to the client.

```directory
/server/internal/server/states/connected.go
```

```go
func (c *Connected) handleLogin(senderId uint64, message *packets.Packet_LoginRequest) {
    // ...
    player, err := c.queries.GetPlayerByUserID(c.dbCtx, user.ID)

    if err != nil {
        c.logger.Printf("Error getting player for user %s: %v\n", username, err)
        c.client.SocketSend(genericFailMessage)
        return
    }

    c.client.SetState(&InGame{
        player: &objects.Player{
            Name:      player.Name,
            DbId:      player.ID,
            BestScore: player.BestScore,
        },
    })
}
```

Now, onto actually updating the player's best score. We will need a new query to update the player's best score, and we will need to call this query whenever a player's mass changes. 

```directory
/server/internal/db/queries.go
```

```sql
-- name: UpdatePlayerBestScore :exec
UPDATE players
SET best_score = ?
WHERE id = ?;
```

This is a very simple query to update the `best_score` field of a player with the given ID. We use `:exec` to denote the fact that this query doesn't return any rows. 

Now, we need to call this query whenever we update the eats something, but only if the resulting mass is greater than the player's current best score. To handle that's let's make a new function in the `InGame` state called `syncPlayerBestScore`.

```directory
/server/internal/server/states/ingame.go
```
    
```go
func (g *InGame) syncPlayerBestScore() {
    currentScore := int64(math.Round(radToMass(g.player.Radius)))
    if currentScore > g.player.BestScore {
        g.player.BestScore = currentScore
        err := g.client.DbTx().Queries.UpdatePlayerBestScore(g.client.DbTx().Ctx, db.UpdatePlayerBestScoreParams{
            ID:        g.player.DbId,
            BestScore: g.player.BestScore,
        })
        if err != nil {
            g.logger.Printf("Error updating player best score: %v\n", err)
        }
    }
}
```

Most of the time, we don't really care about the result of the query, or when exactly it runs, so we can just sort of "fire and forget" it with a goroutine. We will do this at the end of the `handleSporeConsumed` and `handlePlayerConsumed` functions:

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) handleSporeConsumed(senderId uint64, message *packets.Packet_SporeConsumed) {
    // ...
    go g.syncPlayerBestScore()
}

func (g *InGame) handlePlayerConsumed(senderId uint64, message *packets.Packet_PlayerConsumed) {
    // ...
    go g.syncPlayerBestScore()
}
```

The only time we really care about the result of the query is when the player leaves the game, because we want to make sure the player's best score is updated before they leave. So we will call the `syncPlayerBestScore` function directly in the `OnExit` function of the `InGame` state.

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) OnExit() {
    g.syncPlayerBestScore()
}
```

Here's an example of where it would be nice to be managing our database contexts a bit better, because this would be a great place to implement some retry logic in case the query fails. But for now, we just log the error and accept that the player's best score may not be updated in the database if the query fails.

Now, when we run the game, we should see the player's best score updating in the database as they eat things. We can verify this by running the following query on the database:

```sql
SELECT * FROM players;
```

I won't go into too much detail on how to do that here, as there are many resources online that can help with that, but I am using a VS Code extension called [SQLite](https://marketplace.visualstudio.com/items?itemName=alexcvzz.vscode-sqlite) to run the query directly from the editor.
![SQLite extension](/assets/css/images/posts/2024/11/16/sqlite-extension.png)

So that ticks off stage 3 of our plan. Now, let's move on to stage 4: adding protobuf messages to handle requesting and sending hiscores.

## Adding new protobuf messages

For now, we need a way for the client to request the hiscore leaderboard from the server, and for the server to respond with the hiscore leaderboard. The former is dead simple since it requires no payload, and the latter can be achieved using protobuf's `repeated` field type, similarly to what you would have done if you followed the optional optimization at the end of <a href="/2024/11/14/godot-golang-mmo-part-7#repeated-field" target="_blank">§07</a>.

In case you didn't follow that section, a repeated field is just a way of stuffing multiple instances of a message into a single message. This is useful for things like a list of hiscores, where each hiscore is a message with a name and a score.

Let's define the new messages in the `packets.proto` file in the `/shared/` directory.

```directory
/shared/packets.proto
```

```protobuf
message HiscoreBoardRequestMessage { }
message HiscoreMessage { uint64 rank = 1; string name = 2; uint64 score = 3; }
message HiscoreBoardMessage { repeated HiscoreMessage hiscores = 1; }

message Packet {
    // ...
    oneof msg {
        // ...
        HiscoreBoardRequestMessage hiscore_board_request = 14;
        HiscoreMessage hiscore = 15;
        HiscoreBoardMessage hiscore_board = 16;
    }
}
```

So the idea is that the client will send a `HiscoreBoardRequestMessage` to the server, when it wants to browse the hiscore leaderboard. The server will respond with a `HiscoreBoardMessage`, which contains a list of `HiscoreMessage` messages, each of which contains a rank, a name, and a score retrieved from the database.

Let's go ahead and define helper functions for the only message the server needs to send in our `util.go` file:

```directory
/server/pkg/packets/util.go
```

```go
func NewHiscoreBoard(hiscores []*HiscoreMessage) Msg {
    return &Packet_HiscoreBoard{
        HiscoreBoard: &HiscoreBoardMessage{
            Hiscores: hiscores,
        },
    }
}
```


It would be good to handle these messages in a different state, since this logic doesn't really fit in to either the `Connected` or `InGame` states. So let's create a new state called `BrowsingHiscores` to handle this.

## Adding a new server state

It's been a while since we've done this, so here's the rundown on how to add a new state to the server:
First, create a new file in the `/server/internal/server/states/` directory called `browsingHiscores.go`. We will first lay out the methods required to implement the `ClientStateHandler` interface that we defined way back in <a href="/2024/11/10/godot-golang-mmo-part-4#clientstatehandler-definition" target="_blank">§04</a>
```directory
/server/internal/server/states/browsingHiscores.go
```

```go
package states

import (
    "context"
    "fmt"
    "log"

    "server/internal/server"
    "server/internal/server/db"
    "server/pkg/packets"
)

type BrowsingHiscores struct {
    client  server.ClientInterfacer
    logger  *log.Logger
    queries db.Queries
    dbCtx   context.Context
}

func (b *BrowsingHiscores) Name() string {
    return "BrowsingHiscores"
}

func (b *BrowsingHiscores) SetClient(client server.ClientInterfacer) {
    b.client = client
    loggingPrefix := fmt.Sprintf("Client %d [%s]: ", client.Id(), b.Name())
    b.logger = log.New(log.Writer(), loggingPrefix, log.LstdFlags)
    b.queries = *client.DbTx().Queries
    b.dbCtx = client.DbTx().Ctx
}

func (b *BrowsingHiscores) OnEnter() {
}

func (b *BrowsingHiscores) HandleMessage(senderId uint64, message packets.Msg) {
}

func (b *BrowsingHiscores) OnExit() {
}
```

*<small>(we know we are going to use the database a lot in this state, so I have gone ahead and set up the `queries` and `dbCtx` fields in the `SetClient` function, much like we did in the `Connected` state back in <a href="/2024/11/10/godot-golang-mmo-part-5#saving-db-params" target="_blank">§05</a>)</small>*

Now, let's see if we can listen for a `HiscoreBoardRequestMessage` in the `Connected` state, and switch to the `BrowsingHiscores` state when we receive one.

```directory
/server/internal/server/states/connected.go
```

```go
func (c *Connected) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    // ...
    case *packets.Packet_HiscoreBoardRequest:
        c.handleHiscoreBoardRequest(senderId, message)
    }
}

func (c *Connected) handleHiscoreBoardRequest(senderId uint64, _ *packets.Packet_HiscoreBoardRequest) {
    c.client.SetState(&BrowsingHiscores{})
}
```

Now, in the `OnEnter` function of the `BrowsingHiscores` state, let's send a `HiscoreBoardMessage` back to the client with some dummy data, just to make sure everything is working.

```directory
/server/internal/server/states/browsingHiscores.go
```

```go
func (b *BrowsingHiscores) OnEnter() {
    b.client.SocketSend(packets.NewHiscoreBoard(
        []*packets.HiscoreMessage{
            {Rank: 5, Name: "Bob Barker", Score: 100},
            {Rank: 4, Name: "Tristan", Score: 250},
            {Rank: 3, Name: "Adam Sandler", Score: 1000},
        },
    ))
}
```

Now, that should be enough to get us started and test that the client can request and receive the hiscore leaderboard from the server. Let's move on to the client side.

## Adding a new client state

We will need a new state in the client to handle browsing the hiscore leaderboard. This is where it will be able to do things like display the leaderboard, search for a player, etc.

First, create a new directory at `res://states/browsing_hiscores/` and create a new scene called `browsing_hiscores.tscn` of type `Node2D`.

Before we forget, let's go ahead and register the new state with the game manager:

```directory
/client/game_manager.gd
```

```gdscript
enum State {
    # ...
    BROWSING_HISCORES,
}

var _states_scenes: Dictionary[State, String] = {
    # ...
    State.BROWSING_HISCORES: "res://states/browsing_hiscores/browsing_hiscores.tscn",
}
```

Now, we should be able to switch to the `BrowsingHiscores` state from the `Connected` state. Let's test this by adding a button to the `Connected` scene that sends a `HiscoreBoardRequestMessage` to the server.

Add a new button to the connected scene, right next to the **Register** button, call it **HiscoresButton** and set the text to "Hiscores".
![Hiscores button](/assets/css/images/posts/2024/11/16/hiscores-button.png)

Now, let's hook the button up to switch to the `BrowsingHiscores` state when it is pressed. Add the following code to the connected state script:

```directory
/client/states/connected/connected.gd
```

```gdscript
@onready var _hiscores_button := $UI/VBoxContainer/HBoxContainer/HiscoresButton as Button

func _ready() -> void:
    # ...
    _hiscores_button.pressed.connect(_on_hiscores_button_pressed)

func _on_hiscores_button_pressed() -> void:
    GameManager.set_state(GameManager.State.BROWSING_HISCORES)
```

Now, when we run the game, we should be able to press the **Hiscores** button in the main menu, and then get met with a blank screen. This is because we haven't actually added anything to the `BrowsingHiscores` scene yet. Let's add a hiscore leaderboard to the scene, and then add a script to send the `HiscoreBoardRequestMessage` to the server when the scene is entered, and populate the leaderboard with the response.

First, add a **CanvasLayer** node to the `browsing_hiscores.tscn` scene, and name it `UI`. Then, click and drag our `res://classes/hiscores/hiscores.tscn` scene into the `UI` node to add it to the scene tree. This will add the hiscore leaderboard to the scene, ready to be populated with data.

Attach a script called `browsing_hiscores.gd` to the root node of the `browsing_hiscores.tscn` scene.

```directory
/client/states/browsing_hiscores/browsing_hiscores.gd
```

```gdscript

```

Now, when we run the game, we should be able to press the **Hiscores** button in the main menu, and then see the hiscore leaderboard populate with the dummy data we sent from the server.
![Hiscores scene with dummy data](/assets/css/images/posts/2024/11/16/got-dummy-data.png)

We can also see the server was obviously able to switch to the `BrowsingHiscores` state:

```plaintext
2024/11/18 07:39:56 New client connected from [::1]:57389
Client 1: 2024/11/18 07:39:56 Switching from state None to Connected
Client 1: 2024/11/18 07:39:58 Switching from state Connected to BrowsingHiscores
```

Great, we are almost there! Now we just need to actually fetch the top 10 hiscores from the database whenever we receive a `HiscoreBoardRequestMessage` in the `BrowsingHiscores` state on the server, and send that data back to the client.

Let's add a new query to the `queries.sql` file to get the top hiscores from the database.

```directory
/server/internal/db/config/queries.sql
```

```sql
-- name: GetTopScores :many
SELECT p.name, p.best_score
FROM players p
ORDER BY p.best_score DESC
LIMIT ?
OFFSET ?;
```

This will simply select `?` rows from the `players` table, ordered by `best_score` from best to worst. We use another parameter to offset the results, so we can easily paginate the results, or get 10 hiscores from a certain rank, etc. We won't be using this feature quite yet, but we are adding it now to make it easier to add later.

After compiling the queries, we can use this in the `BrowsingHiscores` state:

```directory
/server/internal/server/states/browsingHiscores.go
```

```go
func (b *BrowsingHiscores) OnEnter() {
func (b *BrowsingHiscores) OnEnter() {
    const limit int64 = 10
    const offset int64 = 0

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

It looks like a lot, but a good chunk of it is error handling and constructing the hiscore messages to stuff inside the response. If you run the game now, you should see some real hiscores in the hiscore leaderboard when you press the **Hiscores** button in the main menu.

## Homework

Just one more thing: there's currently no way to go back to the main menu from the hiscores screen. See if you can figure out how to add a button to the hiscores screen that sends a message to the server to switch back to the `Connected` state, and switch state on the client as well. We will go over the solution in the next post.

## Conclusion

So that's it for this post! We have successfully added live hiscores to the game, saved the player's best score to the database, made a way to request, retrieve, and receive that information.

<strong><a href="/2024/11/18/godot-golang-mmo-part-10" class="sparkle-less">In the next post</a></strong>, we will make the game a bit more interesting by making players drop spores and lose mass over time, and also provide a way to search the leaderboard by player name. Hopefully it will be a shorter post than this one! 

--- 

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.