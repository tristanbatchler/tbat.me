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

*Coming soon...*