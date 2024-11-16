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
            
            entry.queue_free()
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

Make sure to remove the test code from the `_ready` function in `res://states/connected/connected.gd`, and remove the **Hiscores** scene from the `Connected` scene, as that was just a test. Let's actually add it to the game now.

## Adding live scores to the game
*Coming soon...*