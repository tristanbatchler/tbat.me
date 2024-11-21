---
title: §11 Polishing the MMO made in Go and Godot 4.4
description: Having finished the features of our MMO, we are almost ready for deployment. The only thing missing is some serious polish to make our game shine.
redditurl: 
---

[Last time](/2024/11/18/godot-golang-mmo-part-10) we just finished adding the final features of our MMO. Now, with deployment right around the corner, we could **really** use some polish. In this part, we will be focusing solely on that: making the game look and feel as good as possible. That way, players will be more likely to stick around and enjoy the game. Let's get started!

## Disconnecting players

You may have noticed that when a player disconnects, the other players are never notified. This is because we never bothered to implement a disconnect packet... until now. Let's go ahead and add that.

```directory
/shared/packets.proto
```

```protobuf
message DisconnectMessage { string reason = 1; }

message Packet {
    // ...
    oneof msg {
        // ...
        DisconnectMessage disconnect = 19;
    }
}
```

```directory
/server/pkg/packets/util.go
```

```go
func NewDisconnect(reason string) Msg {
    return &Packet_Disconnect{
        Disconnect: &DisconnectMessage{
            Reason: reason,
        },
    }
}
```

We don't really need the `reason` payload, but I thought it might be nice to include it, as it could indicate whether it was a clean disconnect or not, an unexpected one, or even just a logout or a kick. Now, let's go ahead and broadcast this message on the client interfacer's `Close` method.

```directory
/server/internal/server/clients/websocket.go
```

```go
func (c *WebSocketClient) Close(reason string) {
    c.Broadcast(packets.NewDisconnect(reason))
    // ...
}
```

Just because we are broadcasting the message doesn't mean we are doing anything with it though, so we first need to listen for it in our client state handlers' `HandleMessage` methods (the only one that matters is going to be the `InGame` state), and forward it on to the client. In fact, we are going to let the client send their own disconnect message to the server, for when they want to log out, so we also need to listen for that and broadcast it to everyone else too.

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    // ...
    case *packets.Packet_Disconnect:
        g.handleDisconnect(senderId, message)
    }
}

func (g *InGame) handleDisconnect(senderId uint64, message *packets.Packet_Disconnect) {
    if senderId == g.client.Id() {
        g.client.Broadcast(message)
        g.client.SetState(&Connected{})
    } else {
        go g.client.SocketSendAs(message, senderId)
    }
}
```

Then, in Godot, we can remove the player and maybe log something when we receive a disconnect message. This will be handled in our `ingame.gd` script.

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _on_ws_packet_received(packet: packets.Packet) -> void:
    # ...
    elif packet.has_disconnect():
        _handle_disconnect_msg(sender_id, packet.get_disconnect())

func _handle_disconnect_msg(sender_id: int, disconnect_msg: packets.DisconnectMessage) -> void:
    if sender_id in _players:
        var player := _players[sender_id]
        var reason := disconnect_msg.get_reason()
        _log.info("%s disconnected because %s" % [player.actor_name, reason])
        _remove_player(player)
```

That's all we need to do to handle disconnects as it stands, although it would be nice to have a "Logout" button in the in-game state scene. While we're at it, we could definitely polish a few other things too.

## Overhauling the InGame UI

The in-game UI is pretty sad right now. For starters, it doesn't even let mobile players use the chat, because there's no send button (PC players can just press Enter). There's also no margin, so the chat is right up against the edge of the screen. Lastly, there's no logout button! Let's fix all of that.

Let's insert a margin container right under the `UI` node in the `ingame.tscn` scene. Then let's make the line edit node as part of a HBoxContainer, along with two buttons: one for sending the message and one for logging out.

After some rearranging, everything under the UI node should look like this:

- **MarginContainer**
    - **VBoxContainer**
        - **HBoxContainer**
            - **Button** - called `LogoutButton`
            - **LineEdit**
            - **Button** - called `SendButton`
        - **Hiscores (instanced hiscores.tscn)**
        - **Log (log.gd)**

Now, we need to reorganize a few things.
1. Set the margin container's anchor preset to **Full Rect**
2. Set the margin container's **Theme Overrides > Constants > Margin** properties to your liking - I chose 20 for all sides
3. Enable the line edit's **Horizontal Expand** property
4. Set the **Text** property of the logout and send buttons to "Logout" and "Send", respectively.

When all is said and done, the scene should look something like this:
![InGame UI](/assets/css/images/posts/2024/11/20/ingame_ui.png)


Now, because we restructured, all of our `@onready var ...` lines in the `ingame.gd` script are going to be wrong. We need to update them to reflect the new structure. Here's what they should look like once fixed (I have also included the new buttons and hooked them up to their respective signals and implemented methods):

```directory
/client/states/ingame/ingame.gd
```

```gdscript
@onready var _logout_button := $UI/MarginContainer/VBoxContainer/HBoxContainer/LogoutButton as Button
@onready var _line_edit := $UI/MarginContainer/VBoxContainer/HBoxContainer/LineEdit as LineEdit
@onready var _send_button := $UI/MarginContainer/VBoxContainer/HBoxContainer/SendButton as Button
@onready var _log := $UI/MarginContainer/VBoxContainer/Log as Log
@onready var _hiscores := $UI/MarginContainer/VBoxContainer/Hiscores as Hiscores

func _ready() -> void:
    # ...
    _logout_button.pressed.connect(_on_logout_button_pressed)
    _send_button.pressed.connect(_on_send_button_pressed)

func _on_logout_button_pressed() -> void:
    var packet := packets.Packet.new()
    var disconnect_msg := packet.new_disconnect()
    disconnect_msg.set_reason("logged out")
    WS.send(packet)
    GameManager.set_state(GameManager.State.CONNECTED)

func _on_send_button_pressed() -> void:
    _on_line_edit_text_entered(_line_edit.text)
```

This shouldn't need much explaining. The only notable aspect here is we are sending a disconnect message to the server when the logout button is pressed, and then we are changing our state back to the `Connected` state.

Go ahead and try it out! You should now be able to send messages on mobile and log out from the game. The chat should also look a lot nicer with the margin container.

<video controls>
  <source src="/assets/css/images/posts/2024/11/20/logout_demo.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

## Revamping the login screen

Now that we've zhuzhed up the in-game UI, let's do the same for the login screen. The process for registering vs. logging in is identical, which doesn't make much sense, so we should separate those out as well.

### Centering the form and adding a title

Let's get everything centered and away from the top edge of the screen. We can do that by simply opening up the `res://states/connected/connects.tscn` scene and setting the top VBoxContainer's anchor preset to **Center** and then setting the **Custom Minimum Size**'s **x** value to something like 300. Because we've already set the other elements to expand, this is all we should need to do to get it looking pretty centered.

We should center the buttons as well, though, so set the HBoxContainer's **Alignment** property to **Center** too.

Finally, we should add a cool background and title to the login screen! Add a **RichTextLabel** node to the top of the VBoxContainer and set its **Text** property to whatever you want to call your game. I'm going with "Radius Rumble". Make sure to check the **Fit Content** property, so the text doesn't get cut off.

There's [a lot of cool stuff](https://docs.godotengine.org/en/stable/tutorials/ui/bbcode_in_richtextlabel.html) you can do if you enable the **BBCode Enabled** property on the RichTextLabel, for example:

```bbcode
[center][rainbow][shake]Radius Rumble[/shake][/rainbow][/center]
```

You can also make the text bigger by using the **Theme Overrides > Font Sizes > Normal Font Size** property.

![Login Screen](/assets/css/images/posts/2024/11/20/login_screen.png)

You can really go wild with this, so feel free to experiment!

### Adding a background image

We can also add a background image to the login screen. I'll opt for the same tiled texture from inside the game, but maybe throw a cool shader effect on it to make it look more interesting. 

To do this, simply add a **Sprite2D** node as a child of the root `Connected` node (so it is a sibling to the `UI` node) and call it `Background`. Your `res://states/connected/connected.tscn` tree should now look like this:

- **Node** - called `Connected`
    - **Sprite2D** - called `Background`
    - **CanvasLayer** - called `UI`
      - **VBoxConatainer**
        - **RichTextLabel**
        - **LineEdit** - called `Username`
        - **LineEdit** - called `Password`
        - **HBoxContainer**
          - **Button** - called `LoginButton`
          - **Button** - called `RegisterButton`
          - **Button** - called `HiscoresButton`
        - **Log (log.gd)** - called `Log`

Now make the following edits to the `Background` sprite:
1. Set the **Texture** property to `resources/floor.svg` (use the **Quick Load...** option in the drop-down)
2. Untick the **Centered** property under **Offset**
3. Tick the **Enabled** checkbox under **Region**
4. Set the **Rect**'s **w** and **h** to the size of your viewport (found under **Project Settings > Display > Window > Size**)
5. Choose **Enabled** for the **Repeat** property under **Texture**

![Background Sprite](/assets/css/images/posts/2024/11/20/background_sprite.png)

It looks pretty good already, but we can make it look even better with a shader. With the `Background` sprite still selected, expand the **Material** property in the inspector, click the dropdown next to **Material** and choose **New ShaderMaterial**. This will assign a new, blank shader material to the sprite. If you click on the shader material, it will expand to show a **Shader** dropdown which you can open and choose **New Shader**. This will prompt you to create a new script, which you can save under `res://resources/background_effect.gdshader`.

![Shader Material](/assets/css/images/posts/2024/11/20/shader_material.png)

If you open up the shader script, you can paste whatever cool shader code you want in there. I have never worked with shaders before, so I went to [Godot Shaders](https://godotshaders.com) and found this cool [Sine Morphing](https://godotshaders.com/shader/sine-morphing) one. I copied the code and pasted it into my shader script. It looks like this:

```glsl
shader_type canvas_item;

// --- Uniforms --- //
uniform vec2 amplitutde = vec2(1.0, 0.0);
uniform vec2 speed = vec2(1.0, 0.0);

// --- Functions --- //
void fragment() {
    vec2 pos = mod((UV - amplitutde * sin(TIME + vec2(UV.y, UV.x) * speed)) / TEXTURE_PIXEL_SIZE,
            1.0 / TEXTURE_PIXEL_SIZE) * TEXTURE_PIXEL_SIZE;
    COLOR = texture(TEXTURE, pos);
}
```

<video controls loop>
  <source src="/assets/css/images/posts/2024/11/20/background_demo.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

Looking good! Let's add some accessibility features to the login screen now.

### Accessibility / privacy

I'll just blast through this: we need to censor the password field, and easily let users cycle through the fields with the tab key. We can do this by enabling the **Secret** property on the password line edit in the inspector. We can also choose all the relevant the **Neighbor** nodes under the **Focus** section of the inspector for each line edit and button. There are more details in the official documentation [here](https://docs.godotengine.org/en/stable/tutorials/ui/gui_navigation.html).

Let's also enable the `Log` node's **Scroll Following** property, so the log will always show the most recent messages. We should do that in the InGame and BrowsingHiscores scenes too, while we think of it.

We should also add prompts to the line edits, so users know what they are for. Set the **Placeholder Text** property of the username line edit to "Username" and the password line edit to "Password".

There's a lot more we could do here, like letting users press Enter to log in, or having the Username field focused initially, but I think this is good enough for now.

### Revamping the hiscores screen

Finally, let's pretty much do the same thing to the hiscores screen. We'll be adding the same title, the same centering technique, and the same background image and shader effect. I will leave this as an exercise for the reader (hint: you can copy and paste the `Background` sprite and RichTextLabel from the `Connected` scene and all the properties will be the same).

<video controls>
  <source src="/assets/css/images/posts/2024/11/20/copypaste.webm" type="video/webm">
    Your browser does not support the video tag.
</video>

Don't forget to change your code if you adjust the scene structure or node names!

## Unified theme

Now that we have more-or-less committed to certain nodes and properties, we can easily change the look and feel of the UI by changing the [**theme**](https://docs.godotengine.org/en/stable/classes/class_theme.html).

We are going to make a simple theme that improves the contrast and size of the text in the game. To do this, we need to create a new theme resource. Right-click on the `res://resources/` folder and choose **Create New > Resource...** then choose **Theme**. Name it `game_theme.tres` and click **Save**.

When you double-click on the theme from the scene editor, you will see a ton of options in the bottom **Theme** panel. This is where you can override any property of all the UI elements. You can even get other people's themes [itch.io](https://itch.io/c/1473270/themes-for-godot-games).

I will just be making a few simple changes though, so I will walk you through them. First, let's change the font size for buttons.

1. Click on the **`+`** button at the top-right of the **Theme** panel
   ![Add Style](/assets/css/images/posts/2024/11/20/add_style.png)
    ![alt text](image.png)

2. Choose Button and click **Add Type**
3. Click on the **Font Size** tab and click the **`+`** button to override the default font size
4. Choose **24** and click **Save**
   ![Button Font Size](/assets/css/images/posts/2024/11/20/button_font_size.png)

You won't see the changes in our scenes yet, because we haven't applied the theme to them. We can do this by selecting the `VBoxContainer` nodes in the `Connected` and `BrowsingHiscores` scenes and setting the **Theme** property to `res://resources/game_theme.tres`.

Let's give the same treatment to the line edits, labels, and rich text labels. Just follow the same steps as above, but choose **LineEdit**, **Label**, and **RichTextLabel** instead of **Button**.

Let's also give a bit more contrast to your labels and rich text labels by changing the **font_shadow_color** to something darker that will stand out against the background. I went with `#30170872`.

So now our game looks like this:
![Connected Screen](/assets/css/images/posts/2024/11/20/connected_screen.png)

This is cool and all, but there's just one more feature I want to add before we call it a day. It would be really great if players could choose their color when they register, and having a separate registration screen would make more sense. That way, we can also get users to type their password twice to confirm it.

## Adding a separate registration screen
*Coming soon...*