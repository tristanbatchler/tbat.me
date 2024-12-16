---
title: "§11 Polish Your Godot 4 MMO for Launch"
description: "Prepare for deployment by adding polish to your MMO. Refine visuals, fix bugs, and ensure a smooth experience for your players."
redditurl: 
project: godot4golang
---

[Last time](/2024/11/18/godot-golang-mmo-part-10) we just finished adding the final features of our MMO. Now, with deployment right around the corner, we could **really** use some polish. In this part, we will be focusing solely on that: making the game look and feel as good as possible. That way, players will be more likely to stick around and enjoy the game. 

Each one of these sections could be technically be considered optional, and none of them will depend on each other, so feel free to pick and choose which ones are important to you, and don't feel the need to do them in any particular order. Let's get started!

As always, if do you want to start here without viewing the previous lesson, feel free to download the source code for release [v0.10](https://github.com/tristanbatchler/Godot4Go_MMO/releases/tag/v0.10) in the [official GitHub repository](https://github.com/tristanbatchler/Godot4Go_MMO).

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
        _remove_actor(player)
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
{% include img.html src="posts/2024/11/20/ingame_ui.png" alt="InGame UI" %}


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
  <source src="/assets/images/posts/2024/11/20/logout_demo.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

## Revamping the login screen

Now that we've zhuzhed up the in-game UI, let's do the same for the login screen. The process for registering vs. logging in is identical, which doesn't make much sense, so we should separate those out as well.

### Centering the form and adding a title

Let's get everything centered and away from the top edge of the screen. We can do that by simply opening up the `res://states/connected/connected.tscn` scene and inserting a margin container, much like we did for the in-game scene, as a parent of the VBoxContainer's. Then set the margin container's anchor preset to **Full Rect** and override the theme's margin constants to whatever you like.

We should center the buttons as well, though, so set the HBoxContainer's **Alignment** property to **Center** too.

{% include img.html src="posts/2024/11/20/centered_login_screen.png" alt="Centered Login Screen" %}

We should add a cool title to the login screen! Add a **RichTextLabel** node to the top of the VBoxContainer and set its **Text** property to whatever you want to call your game. I'm going with "Radius Rumble". Make sure to check the **Fit Content** property, so the text doesn't get cut off.

There's [a lot of cool stuff](https://docs.godotengine.org/en/stable/tutorials/ui/bbcode_in_richtextlabel.html) you can do if you enable the **BBCode Enabled** property on the RichTextLabel, for example:

```bbcode
[center][rainbow][shake][b]Radius Rumble[/b][/shake][/rainbow][/center]
```

You can also make the text bigger by using the **Theme Overrides > Font Sizes > Bold Font Size** property.

{% include img.html src="posts/2024/11/20/login_screen.png" alt="Login Screen" %}

You can really go wild with this, so feel free to experiment!

### Adding a background image

We can also add a background image to the login screen. I'll opt for the same tiled texture from inside the game, but maybe throw a cool shader effect on it to make it look more interesting. 

To do this, simply add a **Sprite2D** node as a child of the root `Connected` node (so it is a sibling to the `UI` node) and call it `Background`. Your `res://states/connected/connected.tscn` tree should now look like this:

- **Node** - called `Connected`
    - **Sprite2D** - called `Background`
    - **CanvasLayer** - called `UI`
      - **MarginContainer**
        - **VBoxContainer**
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
2. Un-tick the **Centered** property under **Offset**
3. Tick the **Enabled** checkbox under **Region**
4. Set the **Rect**'s **w** and **h** to the size of your viewport (found under **Project Settings > Display > Window > Size**)
5. Choose **Enabled** for the **Repeat** property under **Texture**

{% include img.html src="posts/2024/11/20/background_sprite.png" alt="Background Sprite" %}

It looks pretty good already, but we can make it look even better with a shader. With the `Background` sprite still selected, expand the **Material** property in the inspector, click the dropdown next to **Material** and choose **New ShaderMaterial**. This will assign a new, blank shader material to the sprite. If you click on the shader material, it will expand to show a **Shader** dropdown which you can open and choose **New Shader**. This will prompt you to create a new script, which you can save under `res://resources/background_effect.gdshader`.

{% include img.html src="posts/2024/11/20/shader_material.png" alt="Shader Material" %}

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
  <source src="/assets/images/posts/2024/11/20/background_demo.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

Looking good! Let's add some accessibility features to the login screen now.

### Accessibility / privacy

I'll just blast through this: we need to censor the password field, and easily let users cycle through the fields with the tab key. We can do this by enabling the **Secret** property on the password line edit in the inspector. For users on mobile devices, it's important the auto-suggest feature doesn't show their password, so you can also select **Password** under the **Virtual Keyboard Type** property.

We can also choose all the relevant the **Neighbor** nodes under the **Focus** section of the inspector for each line edit and button. There are more details in the official documentation [here](https://docs.godotengine.org/en/stable/tutorials/ui/gui_navigation.html).

Let's also enable the `Log` node's **Scroll Following** property, so the log will always show the most recent messages. We should do that in the InGame and BrowsingHiscores scenes too, while we think of it.

We should also add prompts to the line edits, so users know what they are for. Set the **Placeholder Text** property of the username line edit to "Username" and the password line edit to "Password".

There's a lot more we could do here, like letting users press Enter to log in, or having the Username field focused initially, but I think this is good enough for now.

### Revamping the hiscores screen

Finally, let's pretty much do the same thing to the hiscores screen. We'll be adding the same title and the same background image and shader effect. You can also add a margin container like we did with the in-game UI. I will leave this as an exercise for the reader (hint: you can copy and paste the `Background` sprite and RichTextLabel from the `Connected` scene and all the properties will be the same).

<video controls>
  <source src="/assets/images/posts/2024/11/20/copypaste.webm" type="video/webm">
    Your browser does not support the video tag.
</video>

Don't forget to change your code if you adjust the scene structure or node names!

## Unified theme

Now that we have more-or-less committed to certain nodes and properties, we can easily change the look and feel of the UI by changing the [**theme**](https://docs.godotengine.org/en/stable/classes/class_theme.html).

We are going to make a simple theme that improves the contrast and size of the text in the game. To do this, we need to create a new theme resource. Right-click on the `res://resources/` folder and choose **Create New > Resource...** then choose **Theme**. Name it `game_theme.tres` and click **Save**.

When you double-click on the theme from the scene editor, you will see a ton of options in the bottom **Theme** panel. This is where you can override any property of all the UI elements. You can even get other people's themes [itch.io](https://itch.io/c/1473270/themes-for-godot-games).

I will just be making a few simple changes though, so I will walk you through them. First, let's change the font size for buttons.

1. Click on the **`+`** button at the top-right of the **Theme** panel
   {% include img.html src="posts/2024/11/20/add_style.png" alt="Add Style" %}

2. Choose Button and click **Add Type**
3. Click on the **Font Size** tab and click the **`+`** button to override the default font size
4. Choose **24** and click **Save**
   {% include img.html src="posts/2024/11/20/button_font_size.png" alt="Button Font Size" %}

You won't see the changes in our scenes yet, because we haven't applied the theme to them. We can do this by selecting the `VBoxContainer` nodes in the `Connected` and `BrowsingHiscores` scenes and setting the **Theme** property to `res://resources/game_theme.tres`.

Let's give the same treatment to the line edits, labels, and rich text labels. Just follow the same steps as above, but choose **LineEdit**, **Label**, and **RichTextLabel** instead of **Button**.

Let's also give a bit more contrast to your labels and rich text labels by changing the **font_shadow_color** to something darker that will stand out against the background. I went with `#30170872`.

So now our game looks like this:
{% include img.html src="posts/2024/11/20/connected_screen.png" alt="Connected Screen" %}

## Making the window resizable

It is possible to resize the window currently, but it has a couple of issues. It doesn't scale the UI or the game world, so it gives an unfair advantage to players who have a larger screen while also making it harder to read the text on-screen. We can fix that by going to **Project Settings > Display > Window > Stretch** and setting the stretch **Mode** to **viewport** and the **Aspect** to **Keep**. 

Now, when you resize the window, the game will scale to fit the window, and the UI will scale with it. When we eventually deploy our game to the web, this will be very important, as our game might be embedded into different sized frames, so we need to account for that.


## Adding a separate registration screen

It would be really great if players could choose their color when they register, and having a separate registration screen would make more sense. That way, we can also get users to type their password twice to confirm it as well.

### Extracting the login form to a new scene

Let's start by extracting the username and password fields into a separate scene. Create a new folder called `res://classes/login_form/` and save a new scene called `login_form.tscn` in there. Create a new scene at `res://classes/login_form/login_form.tscn` with root node type `VBoxContainer`. Make the following scene:

- **VBoxContainer** - called `LoginForm`
  - **LineEdit** - called `Username`
  - **LineEdit** - called `Password`
  - **HBoxContainer**
    - **Button** - called `LoginButton`
    - **Button** - called `HiscoresButton`

To speed things along, you can simply copy and paste node we need from the already existing `Connected` scene.

Set the **Anchor** property of the `LoginForm` to **Full Rect**. Now, remove the `Username` and `Password` line edits, as well as the entire HBoxContainer from the `Connected` scene. We will add this scene back to the `Connected` scene underneath the `RichTextLabel` node (simply click and drag `login_form.tscn` from the FileSystem panel into the `Connected` scene tree). 

We have lost the register button and broken our `connected.gd` script, but don't panic; we will be adding it back somewhere more suitable and fixing things up.

At the moment, your `Connected` scene should look like this:

- **Node** - called `Connected`
  - **Sprite2D** - called `Background`
  - **CanvasLayer** - called `UI`
    - **MarginContainer**
      - **VBoxContainer**
        - **RichTextLabel**
        - **LoginForm (instanced login_form.tscn)**
        - **Log (log.gd)**

{% include img.html src="posts/2024/11/20/half_refactored_connected.png" alt="Half refactored Connected scene" %}


Now, we need our `connected.gd` script to know whenever the login form has been submitted. The best way to achieve this is through a custom signal on the login form. Attach a new script to the `LoginForm` node and add the following code.

```directory
/client/classes/login_form/login_form.gd
```

```gdscript
class_name LoginForm
extends VBoxContainer

@onready var _username_field := $Username as LineEdit
@onready var _password_field := $Password as LineEdit
@onready var _login_button := $HBoxContainer/LoginButton as Button
@onready var _hiscores_button := $HBoxContainer/HiscoresButton as Button

signal form_submitted(username: String, password: String)

func _ready() -> void:
    _login_button.pressed.connect(_on_login_button_pressed)
    _hiscores_button.pressed.connect(_on_hiscores_button_pressed)

func _on_login_button_pressed() -> void:
    form_submitted.emit(_username_field.text, _password_field.text)

func _on_hiscores_button_pressed() -> void:
    GameManager.set_state(GameManager.State.BROWSING_HISCORES)
```

Here, we are straight up copying the logic for the hiscores button from the `connected.gd` script. We are also emitting a signal whenever the login button is pressed, passing the username and password as arguments.

Let's head back to the `connected.gd` script to fix up the references to nodes that don't exist anymore, and replace it with logic to handle the new signal.

1. **Remove** the following references:

    ```directory
    /client/states/connected/connected.gd
    ```

    ```gdscript
    # Remove these four references
    @onready var _username_field := $UI/MarginContainer/VBoxContainer/Username as LineEdit
    @onready var _password_field := $UI/MarginContainer/VBoxContainer/Password as LineEdit
    @onready var _login_button := $UI/MarginContainer/VBoxContainer/HBoxContainer/LoginButton as Button
    @onready var _register_button := $UI/MarginContainer/VBoxContainer/HBoxContainer/RegisterButton as Button
    @onready var _hiscores_button := $UI/MarginContainer/VBoxContainer/HBoxContainer/HiscoresButton as Button

    func _ready() -> void: # Don't actually remove *this* line
        _login_button.pressed.connect(_on_login_button_pressed) # Remove this
        _register_button.pressed.connect(_on_register_button_pressed) # and this
        _hiscores_button.pressed.connect(_on_hiscores_button_pressed) # this too

    # Remove all of these methods entirely
    func _on_login_button_pressed() -> void:
        # ...

    func _on_register_button_pressed() -> void:
        # ...

    func _on_hiscores_button_pressed() -> void:
        # ...
    ```

2. **Add** the following code:

    ```directory
    /client/states/connected/connected.gd
    ```

    ```gdscript
    @onready var _login_form := $UI/MarginContainer/VBoxContainer/LoginForm as LoginForm

    func _ready() -> void:
        # ...
        _login_form.form_submitted.connect(_on_login_form_submitted)

    func _on_login_form_submitted(username: String, password: String) -> void:
        var packet := packets.Packet.new()
        var login_request_msg := packet.new_login_request()
        login_request_msg.set_username(username)
        login_request_msg.set_password(password)
        WS.send(packet)
        _action_on_ok_received = func(): GameManager.set_state(GameManager.State.INGAME)
    ```

For reference, the new `connected.gd` script should look like this:

<details markdown="1">
<summary>Click to expand</summary>

```directory
/client/states/connected/connected.gd
```

```gdscript
extends Node

const packets := preload("res://packets.gd")

var _action_on_ok_received: Callable

@onready var _register_button := $UI/MarginContainer/VBoxContainer/HBoxContainer/RegisterButton as Button
@onready var _log := $UI/MarginContainer/VBoxContainer/Log as Log
@onready var _login_form := $UI/MarginContainer/VBoxContainer/LoginForm as LoginForm

func _ready() -> void:
    WS.packet_received.connect(_on_ws_packet_received)
    WS.connection_closed.connect(_on_ws_connection_closed)
    _login_form.form_submitted.connect(_on_login_form_submitted)

func _on_ws_packet_received(packet: packets.Packet) -> void:
    var sender_id := packet.get_sender_id()
    if packet.has_deny_response():
        var deny_response_message := packet.get_deny_response()
        _log.error(deny_response_message.get_reason())
    elif packet.has_ok_response():
        _action_on_ok_received.call()
    
func _on_ws_connection_closed() -> void:
    pass
    
func _on_login_form_submitted(username: String, password: String) -> void:
    var packet := packets.Packet.new()
    var login_request_msg := packet.new_login_request()
    login_request_msg.set_username(username)
    login_request_msg.set_password(password)
    WS.send(packet)
    _action_on_ok_received = func(): GameManager.set_state(GameManager.State.INGAME)
```
</details>

Now, you should be able to log in with the new login form, and browse the hiscores too. Nothing should be different from before except for the fact we've lost the register button. We will add that back in now.

### Adding a new registration form

Let's create new folder called `res://classes/register_form/` and duplicate the `login_form.tscn` scene as `register_form.tscn` and move it into the new folder. Open the scene and rename the `LoginForm` node to `RegisterForm`. Also make the following changes:

1. Duplicate the `Password` line edit and call it `ConfirmPassword`. Change the placeholder text to "Confirm password".
2. Rename the `LoginButton` to `ConfirmButton` and change the text to "Confirm".
3. Rename the `HiscoresButton` to `CancelButton` and change the text to "Cancel".
4. Detach the `login_form.gd` script from the root `RegisterForm` node (right-click on the root node and choose **Detach Script**).
   {% include img.html src="posts/2024/11/20/detach_script.png" alt="Detach Script" %}

Now, we need to attach a new script which will be similar to the login script we made before, in that it will emit a `form_submitted` signal containing the registration data. Here's what the script should look like:

```directory
/client/classes/register_form/register_form.gd
```

```gdscript
class_name RegisterForm
extends VBoxContainer

@onready var _username_field := $Username as LineEdit
@onready var _password_field := $Password as LineEdit
@onready var _confirm_password_field := $ConfirmPassword as LineEdit
@onready var _confirm_button := $HBoxContainer/ConfirmButton as Button
@onready var _cancel_button := $HBoxContainer/CancelButton as Button

signal form_submitted(username: String, password: String, confirm_password: String)
signal form_cancelled()

func _ready() -> void:
    _confirm_button.pressed.connect(_on_confirm_button_pressed)
    _cancel_button.pressed.connect(_on_cancel_button_pressed)

func _on_confirm_button_pressed() -> void:
    form_submitted.emit(_username_field.text, _password_field.text, _confirm_password_field.text)

func _on_cancel_button_pressed() -> void:
    form_cancelled.emit()
```

Note that we are not doing any validation to check the password fields match here, as that will be done in the connected state script, which has access to log errors. We are also emitting a `form_cancelled` signal, which will be used to switch back to the login form from the connected state script.

Let's get this new form into the `Connected` scene. Drag the `register_form.tscn` scene from the FileSystem panel into the `Connected` scene tree, underneath the `LoginForm` node. Your scene should now look a bit funny, because the login form and registration forms are both present, stacked on top of each other.

Our solution to this is to hide the registration form by default, and when a registration button is pressed, we will hide the login form and show the registration form. When the `form_cancelled` signal is emitted, we will do the opposite.

Let's get started by clicking the 👁️ button to the right of the `RegisterForm` node in the `Connected` scene:
{% include img.html src="posts/2024/11/20/hide_register_form.png" alt="Hide Register Form" %}

Now, let's add the logic to the `connected.gd` script to handle the new registration form.

```directory
/client/states/connected/connected.gd
```

```gdscript
@onready var _register_form := $UI/MarginContainer/VBoxContainer/RegisterForm as RegisterForm

func _ready() -> void:
    # ...
    _register_form.form_submitted.connect(_on_register_form_submitted)
    _register_form.form_cancelled.connect(_on_register_form_cancelled)

func _on_register_form_submitted(username: String, password: String, confirm_password: String) -> void:
    if password != confirm_password:
        _log.error("Passwords do not match")
        return

    var packet := packets.Packet.new()
    var register_request_msg := packet.new_register_request()
    register_request_msg.set_username(username)
    register_request_msg.set_password(password)
    WS.send(packet)
    _action_on_ok_received = func(): _log.success("Registration successful! Go back and log in with your new account.")

func _on_register_form_cancelled() -> void:
    _register_form.hide()
    _login_form.show()
```

Now, if we run the game, it should work exactly the same as before, but we can't test the registration form yet, because we haven't added a button to reveal it. Let's do that now.

### Adding a register button

We need to add a way to register in the `Connected` scene. To do this, we will add a **RichTextLabel** node to the `VBoxContainer` node in the `Connected` scene, just underneath the two forms and above the log. Call it `RegisterPrompt`, enable the **Fit Content** and **BBCode Enabled**, and set the **Text** property to something like:

```bbcode

[center][i]Don't have an account? [color=#E3A071][url=register]Create one here![/url][/color][/i][/center]
```

We are going to take advantage of the [`url` BBCode tag](https://docs.godotengine.org/en/stable/tutorials/ui/bbcode_in_richtextlabel.html#doc-bbcode-in-richtextlabel-handling-url-tag-clicks) to emit a signal when the user clicks on the link. To do this, head on over to the `connected.gd` script and add the following code:

```directory
/client/states/connected/connected.gd
```

```gdscript
@onready var _register_prompt := $UI/MarginContainer/VBoxContainer/RegisterPrompt as RichTextLabel

func _ready() -> void:
    # ...
    _register_prompt.meta_clicked.connect(_on_register_prompt_meta_clicked)

func _on_register_form_cancelled() -> void:
    # ...
    _register_prompt.hide()

func _on_register_prompt_meta_clicked(meta) -> void:
    if meta is String and meta == "register":
        _login_form.hide()
        _register_form.show()
        _register_prompt.hide()
```

Now, when you run the game, you should be able to click on the link in the `Connected` scene and reveal the registration form. You can also click the cancel button to go back to the login form. Everything should be looking great now!

<video controls>
  <source src="/assets/images/posts/2024/11/20/registration_screen_demo.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

### Setting up the server to handle custom player colors

Now that we have a registration form, we can add a color picker to it. But first, we'd better update our packets and database to allow for a color field.

When you think about it, a color can be represented in many ways:
* As a string, like `"#FF0000"` for red
* As an array of floats, like `[1.0, 0.0, 0.0]`
* As an array of integers, like `[255, 0, 0]`
* etc.

These are all valid ways to represent colors, but there is one more way that I believe is the most convenient for us: a simple 32-bit integer. This is because you can fit a number between 0 and 255 into just 8 bits, meaning we have enough room to store four of these in a 32-bit integer. There are typically three or four channels in a color (red, green, blue, and sometimes alpha), so we can just stuff all of these into a single 32-bit integer. Luckily, Godot is well-equipped to handle this, as its `Color` class has a `hex` function that will convert an integer like we described into a `Color` object. Similarly, the inverse method exists, called `to_rgba32`, which will convert a `Color` object into a 32-bit integer. We will take advantage of this in our game to store player colors efficiently in our packets and database.

Let's start by adding a color field to our packets. We will be modifying our existing `RegisterRequestMessage` and `PlayerMessage` to include a color field.

```directory
/shared/packets.proto
```

```protobuf
message RegisterRequestMessage { /* ... */ int32 color = 3; }
message PlayerMessage { /* ... */ int32 color = 8; }
```

Now (after recompiling protobufs), let's update our `Player` object struct and our `NewPlayer` helper function to include a color field.

```directory
/server/internal/objects/gameObjects.go
```

```go
type Player struct {
    // ...
    Color int32
}
```

```directory
/server/pkg/packets/util.go
```

```go
func NewPlayer(id uint64, player *objects.Player) Msg {
    return &Packet_Player{
        Player: &PlayerMessage{
            // ...
            Color: player.Color,
        },
    }
}
```

Let's update our database schema to include a color field in the `players` table.

```directory
/server/internal/server/db/config/schema.sql
```

```sql
CREATE TABLE IF NOT EXISTS players (
    /* ... */
    color INTEGER NOT NULL,
    /* ... */
);
```

We'll also need to update our `CreatePlayer` query to include the color field.

```directory
/server/internal/server/db/config/queries.sql
```

```sql
-- name: CreatePlayer :one
INSERT INTO players (
    user_id, name, color
) VALUES (
    ?, ?, ?
)
RETURNING *;
```

Now after recompiling the SQL with `sqlc` and deleting the old database <small>(`/server/cmd/db.sqlite` - see <a href="/2024/11/16/godot-golang-mmo-part-9#delete-db" target="_blank">§09</a> as a reminder on *why* we choose to do this)</small>, we can update the server connected state handler to handle the new color field. First, we will update the register request handler to include the color field when it creates a new player in the database.

```directory
/server/internal/server/states/connected.go
```

```go
func (c *Connected) handleRegisterRequest(senderId uint64, message *packets.Packet_RegisterRequest) {
    // ...
    _, err = c.queries.CreatePlayer(c.dbCtx, db.CreatePlayerParams{
        // ...
        Color: int64(message.RegisterRequest.Color),
    })
    // ...
```

Annoyingly, we need to cast the `int32` to an `int64` here, because `sqlc` just assumes everything to be inserted into an `INTEGER` field is 64-bit. This won't screw up our data though, just a slight annoyance.

Now, just update the login request handler to include the color field when it creates and passes the `Player` object to the in-game state:

```directory
/server/internal/server/states/connected.go
```

```go
func (c *Connected) handleLoginRequest(senderId uint64, message *packets.Packet_LoginRequest) {
    // ...
    c.client.SetState(&InGame{
        player: &objects.Player{
            // ...
            Color: int32(player.Color),
        },
    })
}
```
<small>(another annoying cast because the `player.Color` came from the database as an `int64`).</small>

## Letting players choose their color on registration

Now, we're ready to add the color picker to our registration form in Godot, and send the chosen color with the registration request.

Open up the `res://classes/register_form/register_form.tscn` scene and add a new **ColorPicker** node under the root `RegisterForm` (VBoxContainer) node, just underneath the `ConfirmPassword` line edit. Disable the **Edit Alpha** property, so players can't easily choose a transparent color, and also disable the **Can Add Swatches** property, since we don't need that.

For the **Picker Shape**, choose whichever shape you like. Also disable everything under the **Customization** section in the inspector, since most of these are unnecessary and take up space.
{% include img.html src="posts/2024/11/20/color_picker.png" alt="Color Picker" %}

Now, we just need to hook this up to our `register_form.gd` script, include the color in our `form_submitted` signal, and handle it in the `connected.gd` script.

```directory
/client/classes/register_form/register_form.gd
```

```gdscript
@onready var _color_picker := $ColorPicker as ColorPicker

signal form_submitted(username: String, password: String, confirm_password: String, color: Color)

func _on_confirm_button_pressed() -> void:
    form_submitted.emit(_username_field.text, _password_field.text, _confirm_password_field.text, _color_picker.color)
```

```directory
/client/states/connected/connected.gd
```

```gdscript
func _on_register_form_submitted(username: String, password: String, confirm_password: String, color: Color) -> void:
    # ...
    register_request_msg.set_color(color.to_rgba32())
    # ...
```

Now, when you run the game, you should be able to choose a color when you register. The color should be sent to the server and stored in the database. The only thing missing is that the color isn't actually being used in the game yet! Let's fix that now.

### Showing player colors in the game

Back to Godot, first need to update our `Actor` object to include a color field, and update its constructor to include this field. Then we can update the `_draw` method to use this color when drawing the actor.

```directory
/client/objects/actor/actor.gd
```

```gdscript
var color: Color

static func instantiate(actor_id: int, actor_name: String, x: float, y: float, radius: float, speed: float, color: Color, is_player: bool) -> Actor:
    # ...
    actor.color = color
    # ...

func _draw() -> void:
    draw_circle(Vector2.ZERO, _collision_shape.radius, color)
```

Finally, update the `ingame.gd` script to receive the color from the `PlayerMessage` packet and use it when instantiating a new actor.

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _handle_player_msg(sender_id: int, player_msg: packets.PlayerMessage) -> void:
    # ...
    var color_hex := player_msg.get_color()

    var color := Color.hex(color_hex)
    # ...

    if actor_id not in _players:
        _add_actor(actor_id, actor_name, x, y, radius, speed, color, is_player)
    # ...

func _add_actor(actor_id: int, actor_name: String, x: float, y: float, radius: float, speed: float, color: Color, is_player: bool) -> void:
    var actor := Actor.instantiate(actor_id, actor_name, x, y, radius, speed, color, is_player)
    # ...
```


Now, when you run the game, you should see players with different colors. You can also test this by registering a new account with a different color.

<video controls>
  <source src="/assets/images/posts/2024/11/20/registration_demo_2.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

## Auto-zooming the camera

Instead of letting the player scroll to zoom out as far as they like, let's make the camera automatically zoom out whenever the player grows. The player will still be able to zoom in, but the maximum zoom out will be limited to a certain distance.

We will be working entirely in the `res://objects/actor/actor.gd` script for this. First, let's add two new variables near the top of the script, just above the `@onready` variables:

```directory
/client/objects/actor/actor.gd
```

```gdscript
var _target_zoom := 2.0
var _furthest_zoom_allowed := _target_zoom
```

This is going to convey the idea that the camera will start at a zoom of 2x, and the furthest zoom allowed at the beginning will also be 2x. The goal is to update the `_furthest_zoom_allowed` variable whenever the player grows, and we will incorporate some logic to update `_target_zoom` and the camera's actual zoom level as well.

Let's add a new method to the script called `_update_zoom` that will handle all of this logic.

```directory
/client/objects/actor/actor.gd
```

```gdscript
func _update_zoom() -> void:
    if not is_player:
        return

    var new_furthest_zoom_allowed := 2 * start_rad / radius
    if is_equal_approx(_target_zoom, _furthest_zoom_allowed):
        _target_zoom = new_furthest_zoom_allowed
    _furthest_zoom_allowed = new_furthest_zoom_allowed
```

Here, we are taking the updated furthest zoom allowed to be inversely proportional to the player's radius. This means that the camera will zoom out as the player grows. Note we are only modifying the `_target_zoom` variable if the player is already zoomed all the way out. This will allow the player to zoom in if they want, and not have the camera zoom out while they are zoomed in. We are using the `is_equal_approx` function to compare the two floats, as comparing floats directly can be unreliable due to floating-point precision errors.

Now, this is all great, but we're not *actually* updating the camera's zoom level. We will do this in the `_process` method, which is called every frame.

```directory
func _process(_delta: float) -> void:
    if not is_equal_approx(_camera.zoom.x, _target_zoom):
        _camera.zoom -= Vector2(1, 1) * (_camera.zoom.x - _target_zoom) * 0.05
```

This is a simple linear interpolation between the camera's current zoom level and the target zoom level. The `0.05` value is the speed at which the camera will zoom in or out. You can adjust this value to make the camera zoom in or out faster or slower.

Finally, we need to call the `_update_zoom` method whenever the player grows. The perfect place to do that will be in our `radius` setter method:

```directory
/client/objects/actor/actor.gd
```

```gdscript
var radius: float:
    set(new_radius):
        radius = new_radius
        _collision_shape.set_radius(radius)
        _update_zoom()
        queue_redraw()
```

We just need to adjust the `_input` method to update the `_target_zoom` instead of the `_camera.zoom` directly, and cap the zoom level at the `_furthest_zoom_allowed` value.

```directory
/client/objects/actor/actor.gd
```

```gdscript
func _input(event):
    if is_player and event is InputEventMouseButton and event.is_pressed():
        match event.button_index:
            MOUSE_BUTTON_WHEEL_UP:
                _target_zoom = min(4, _target_zoom + 0.1)
            MOUSE_BUTTON_WHEEL_DOWN:
                _target_zoom = max(_furthest_zoom_allowed, _target_zoom - 0.1)
```

So now, whenever the player grows, the camera will zoom out to accommodate them. You can test this by running the game and watching the camera zoom out as you grow.

It would be even nicer if the nameplate font size scaled with the camera zoom level, so let's add that in now. We will just tack on this logic to the start of the `_update_zoom` method, but we need to be careful not to try and change the font size if the node isn't ready yet, such as when the player is first instantiated.

```directory
/client/objects/actor/actor.gd
```

```gdscript
func _update_zoom() -> void:
    if is_node_ready():
        _nameplate.add_theme_font_size_override("font_size", max(16, radius / 2))
    # ...
```

There, now as the player grows, users won't have to squint to read their nameplate.

<video controls>
  <source src="/assets/images/posts/2024/11/20/autozoom.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

## Hiding spores on top of players

One more annoying thing is that spores dropped by players are drawn on top, which looks pretty jarring. Luckily, the fix is very simple. We just need to change the `z_index` of the actors to be higher than the spores'. We can do this in the `ingame.gd` script, just after we add the new actor to the world.

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _add_actor(actor_id: int, actor_name: String, x: float, y: float, radius: float, speed: float, is_player: bool) -> void:
    var actor := Actor.instantiate(actor_id, actor_name, x, y, radius, speed, is_player)
    _world.add_child(actor)
    actor.z_index = 1
    # ...
```

Now, when you run the game, the spores should be drawn underneath the players, which looks a lot better.

## A better approach to lag adjustment

You may not have noticed if you are just playing the game on your own machine, but there are always imperfections with the server syncing the player's position with the client. We are currently naively accounting for that by periodically sending the server's version of the player to the client, and the client will just snap to that position. This works, but feels pretty horrible especially if playing on a server with a high ping. 

To demonstrate this, I've simulated a bad sync by forcing the client's speed to be 10% faster than what the server thinks it is. I've drawn the server's version of the player as a blue ghost, so you can see the difference.
<video controls>
  <source src="/assets/images/posts/2024/11/20/raw-snap.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

We can do better by subtly interpolating the player's position between the server's version and the client's version.

Let's add a new variable to the actor script to represent the server position, and we will suitably call it `server_position`. We will initially set it to the player's position, and then constantly interpolate towards it in the `_physics_process` method.

```directory
/client/objects/actor/actor.gd
```

```gdscript
var server_position: Vector2

func _ready():
    position.x = start_x
    position.y = start_y
    server_position = position
    # ...

func _physics_process(delta) -> void:
    position += velocity * delta
    target_pos += velocity * delta
    position += (target_pos - position) * 0.05
    # ...
```

Here, we are interpolating the player's position towards the `server_position` variable by 5% every frame. This will make the player's movement look a lot smoother, especially when the server's version of the player is constantly changing. You can adjust the `0.05` value to make the interpolation faster or slower.

Note that we are simultaneously updating our true position, but also the `server_position` variable according to our velocity vector. This is because the server position variable will only be updated every so often (whenever the server decides to send us an update), so we need to keep the offset between the two consistent until we start interpolating.

For example, here's what happens when we **don't** add our velocity to the server position every frame:
<video controls>
  <source src="/assets/images/posts/2024/11/20/no-added-vel.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

And this is what it looks like when we **do**:
<video controls>
  <source src="/assets/images/posts/2024/11/20/added-vel.webm" type="video/webm">
  Your browser does not support the video tag.
</video>

Hopefully you agree that the second video demonstrates a much smoother user experience, without compromising the accuracy of the player's position.

With all that aside, we still aren't updating the `server_position` anywhere in our code! We do that in the `ingame.gd` script, where we handle updating our actors. Replace the existing, naive position update with the following:

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _update_actor(actor_id: int, x: float, y: float, direction: float, speed: float, radius: float, is_player: bool) -> void:
    # ...
    var server_position := Vector2(x, y)
    if actor.position.distance_squared_to(server_position) > 50:
        actor.server_position = Vector2(x, y)
```

Note that we still won't update the `server_position` if the position mismatch is small enough, since we can still allow the player to live in their local version of the world if the difference is negligible. This will just help things feel a bit better for the player, because we've built our server to be slightly forgiving when it comes to validation checks anyway.

> Now, you probably won't notice any difference when you run the game, but you can simulate a bad sync if you like, by changing the `speed` variable in the `instantiate` method of `actor.gd`, i.e.
> ```gdscript
> actor.speed = speed * 1.1
> ```
> Remember to revert the change when you're done testing, though!


## Conclusion

So our game is looking and feeling a lot better compared to when we started this part. Everything should be a lot more accessible to mobile users, too, which will be important for <strong><a href="/2024/11/22/godot-golang-mmo-part-12" class="sparkle-less">the next part</a></strong> where we will be deploying our game to the web. That will be the final part of this series, so I hope you will join me for that. If you've made it this far, give yourself a pat on the back! You have done a lot of work, and your game is looking great. Until next time!

--- 

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.