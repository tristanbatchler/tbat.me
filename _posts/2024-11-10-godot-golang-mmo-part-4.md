---
title: Supercharging our Godot 4 Golang MMO with state machines
description: Harness the power of state machines to create a more robust and maintainable codebase for our scalable MMO project.
redditurl: 
---

So far we've been building our Godot 4 Golang MMO project with a focus on scalability and maintainability. Before implementing more complex features, now is a good time to add some more structure to our codebase. In this part, we'll implement a basic, yet powerful state machine system on both the client and server sides. This will allow us to manage the game's logic in a more organized and maintainable way. Without further ado, let's jump right in!

## Building on the client interfacer
So far we've built a pretty good idea of what a client interfacer should look like, but there are definitely some features missing. One of these features is the ability to manage the client's state. But what **is** the client's state? In the context of our MMO, that could be things like "*is the client current in the game?*", "*is the client currently in a menu?*", "*is the client currently disconnected and trying to reconnect?*", and so on. 

There are one two things we want to do with the client's state:
1. Actually define the states, so we know we will need to make a new interface called `ClientStateHandler`
2. Set the client's state, so we know we will need to add a `SetState` method to the `ClientInterfacer`

Elaborating on the first point, a client's state handler doesn't need to be anything fancy, it should just need a name, a set of instructions to run when entering and exiting the state, and it needs to be able to handle packets.

With that in mind, let's add a new interface to our `hub.go` file:

```directory
/server/internal/server/hub.go
```
```go
// A structure for a state machine to process the client's messages
type ClientStateHandler interface {
    Name() string

    // Inject the client into the state handler
    SetClient(client ClientInterfacer)

    OnEnter()
    HandleMessage(senderId uint64, message packets.Msg)

    // Cleanup the state handler and perform any last actions
    OnExit()
}
```

You might notice we've included a `SetClient` method. This is because we want to be able to access the client's data from the state handler. This is useful for things like sending packets to the client, or checking the client's current state.

Next, let's modify the `ClientInterfacer` interface to include a `SetState` method:

```directory
/server/internal/server/hub.go
```
```go
type ClientInterfacer interface {
    // ...
    SetState(newState ClientStateHandler)
    // ...
}
```

## Creating a basic state handler

Now that we have the basic structure in place, let's implement a simple state handler called `Connected`. Create a new folder inside `/server/internal/server` called `states`, and inside that folder create a new file called `connected.go`. 

```directory
/server/internal/server/states/connected.go
```
```go
package states

import (
    "fmt"
    "log"

    "server/internal/server"
    "server/pkg/packets"
)

type Connected struct {
    client server.ClientInterfacer
    logger *log.Logger
}

func (c *Connected) Name() string {
    return "Connected"
}

func (c *Connected) SetClient(client server.ClientInterfacer) {
    c.client = client
    loggingPrefix := fmt.Sprintf("Client %d [%s]: ", client.Id(), c.Name())
    c.logger = log.New(log.Writer(), loggingPrefix, log.LstdFlags)
}

func (c *Connected) OnEnter() {
    // A newly connected client will want to know its own ID first
    c.client.SocketSend(packets.NewId(c.client.Id()))
}

func (c *Connected) HandleMessage(senderId uint64, message packets.Msg) {
}

func (c *Connected) OnExit() {
}
```

This is a good start, and shouldn't be difficult to understand. We are taking over the logging from the client interfacer, so we can include not only the client's ID, but also the state the client is in. This will make debugging much easier. 

In the `OnEnter` method, we are already starting to abstract some existing logic away from the client interfacer. Instead of the client interfacer worrying about what packets to send, we can just call `SocketSend` and let the state handler worry about what to send. We will go back and remove the old logic from the client interfacer later, since we will need to refactor the client interfacer to use the state machine.

We are leaving the `HandleMessage` and `OnExit` methods empty for now, but the basic structure for any state handler is to switch on the message type and handle it accordingly. Let's come back to this later.

As a quick reference, this is what your server folder structure should look like now:

<details markdown="1">
<summary>Click to expand</summary>
```
/server/
│   go.mod
│   go.sum
│   
├───cmd
│       main.go
│       
├───internal
│   └───server
│       │   hub.go
│       │   
│       ├───clients
│       │       websocket.go
│       │       
│       ├───objects
│       │       sharedCollection.go
│       │       
│       └───states
│               connected.go
│
└───pkg
    └───packets
            packets.pb.go
            util.go
```
</details>

## Refactoring the websocket client interfacer

You should see errors complaining that our `WebSocketClient` type doesn't implement `ClientInterfacer` because it doesn't have a `SetState` method. Let's fix that by adding a `state` field to our `WebSocketClient` struct:

```directory
/server/internal/server/clients/websocket.go
```
```go
type WebSocketClient struct {
    // ...
    state server.ClientStateHandler
    //...
}
```

Then we can implement the `SetState` method:

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) SetState(state server.ClientStateHandler) {
    prevStateName := "None"
    if c.state != nil {
        prevStateName = c.state.Name()
        c.state.OnExit()
    }

    newStateName := "None"
    if state != nil {
        newStateName = state.Name()
    }

    c.logger.Printf("Switching from state %s to %s", prevStateName, newStateName)

    c.state = state

    if c.state != nil {
        c.state.SetClient(c)
        c.state.OnEnter()
    }
}
```

This method is pretty straightforward. We are checking if the client is already in a state, and if so, we call the `OnExit` method of the current state. We then set the new state, and call the `OnEnter` method of the new state. Adding logging here is very useful for debugging, as you can see the state transitions in the console.

That should appease the compiler, but we still have some work to do. Now that we have a means to set the client's state, and we have a state that sends the client its ID, we can completely remove the ID-sending logic from the `Initialize` method, and replace it with a call to `SetState`:

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) Initialize(id uint64) {
    // ...
    c.SetState(&states.Connected{})
}
```

Of course, we'll need to import the `states` package at the top of the file:

```go
import (
    // ...
    "server/internal/server/states"
)
```

Now, technically, we can restart the server and should still have the same working chatroom we had at the end of the last part. But we've laid the groundwork for a much more robust and maintainable codebase. Try it out as a sanity check, and if everything is still working, we can move on to refactoring the client interfacer's `ProcessMessage` method to use the state machine, then move the existing logic to the `Connected` state handler.

Cut the contents of the `ProcessMessage` method from the `WebSocketClient` struct, and paste it into the `HandleMessage` method of the `Connected` state handler. After making sure to fix references the state's client interfacer, the `HandleMessage` method should look like this:

```directory
/server/internal/server/states/connected.go
```
```go
func (c *Connected) HandleMessage(senderId uint64, message packets.Msg) {
    if senderId == c.client.Id() {
        c.client.Broadcast(message)
    } else {
        c.client.SocketSendAs(message, senderId)
    }
}
```
Now, where the `ProcessMessage` method was, we can call the `HandleMessage` method of the current state:

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) ProcessMessage(senderId uint64, message packets.Msg) {
    c.state.HandleMessage(senderId, message)
}
```

The last thing we should do is ensure we set the client's state to `nil` when the client connection is closed. This is important because we don't want to keep a reference to the client's state after the client has disconnected. We can do this by adding a call to `SetState(nil)` in the `Close` method of the `WebSocketClient`:

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) Close(reason string) {
    // ...
    c.SetState(nil)
    // ...
}
```

Yet again, we've made a lot of changes, so it's a good idea to restart the server and make sure everything is still working as expected. If it is, congratulations! You've successfully implemented a basic state machine system for the server side of our MMO project. Let's go ahead and do the same for the client side.

## Creating a state manager in Godot

In Godot, it will be useful to break our different areas of logic into separate scenes and scripts. Obviously, we will need a way to transition between these scenes, so we would benefit from an autoload/singleton script that can do all that for us, and we can simply call methods on it to change the game's state from anywhere in the game. If we're going to create a singleton for managing the game's state, we might as well let it hold some other things we might need, like the client's ID too.

Create a new script called `game_manager.gd` with the following code:

```directory
/client/game_managewr.gd
```
```gd
extends Node

enum State {
    ENTERED,
    INGAME,
}

var _states_scenes: Dictionary[State, String] = {
    State.ENTERED: "res://states/entered/entered.tscn",
    State.INGAME: "res://states/ingame/ingame.tscn",
}

var client_id: int
var _current_scene_root: Node

func set_state(state: State) -> void:
    if _current_scene_root != null:
        _current_scene_root.queue_free()

    var scene: PackedScene = load(_states_scenes[state])
    _current_scene_root = scene.instantiate()

    add_child(_current_scene_root)
```

This script serves to expose three things globally:
1. The client's ID
2. An enum of the game's states
3. A method to change the game's state

The first two are pretty self-explanatory. The third has the effect that, when called from another scene, it will instantiate whatever scene is associated with the state passed to it, and add it as a child of the autoload/singleton node which is automatically placed in the root of the scene tree.

The way we've set up this script this means is if we register it as a global autoload called `GameManager` and create some scenes for the different states of the game, we can simply call `GameManager.set_state(GameManager.State.ENTERED)` from `main.gd`, for instance, to instance our `entered.tscn` scene and add it to the scene tree. It would end up looking like this in the remote scene tree:
![Godot scene tree](/assets/css/images/posts/2024/11/10/godot_scene_tree.png)

This is a very powerful pattern, and it will allow us to keep our game's logic organized and maintainable.

By the way, the **Entered** state will be the initial state of the game, and will be responsible for connecting to the server and listening for a client ID and transitioning to the **InGame** state when it receives the ID. The **InGame** state will be responsible for running the chatroom logic, for now, but will be expanded upon later, alongside new states for things like browsing menus, creating characters, etc.

So let's go ahead and register our new script as an autoload. We've done this before with the `websocket_client.gd` script, but as a reminder, you can do this by going to **Project > Project Settings > Gloabls**, ensuring you are on the **Autoload** tab, and entering `res://game_manager.gd` into the **Path** field, and **GameManager** into the **Node Name** field. Then click **Add** and **Close**.

Now let's actually create the scenes for the different states of the game. Create a new folder called `states` in the root of the project, and inside that folder create two new folders called `entered` and `ingame`. Inside each of these folders, create a new scene called `entered.tscn` and `ingame.tscn`, respectively, both of which should have a root type of **Node**:
![Godot scene tree](/assets/css/images/posts/2024/11/10/godot_states.png)

For now, let's just add a **CanvasLayer** node to each scene called **UI**, and our custom **Log** node as a child of each canvas layer, making sure to let it take up the full size of the screen with the **Full Rect** anchor preset.

We can now attach a script to the `entered.tscn` scene's root node that will connect to the server and listen for the client ID. Create a new script at `res://states/entered/entered.gd` with the following code which is basically just copy-and-pasted from `main.gd`:

```directory
/client/states/entered/entered.gd
```
```gd
extends Node

const packets := preload("res://packets.gd")

@onready var _log := $UI/Log as Log

func _ready() -> void:
    WS.connected_to_server.connect(_on_ws_connected_to_server)
    WS.connection_closed.connect(_on_ws_connection_closed)
    WS.packet_received.connect(_on_ws_packet_received)

    _log.info("Connecting to server...")
    WS.connect_to_url("ws://localhost:8080/ws")

func _on_ws_connected_to_server() -> void:
    _log.info("Connected to server")

func _on_ws_connection_closed() -> void:
    _log.info("Connection closed")

func _on_ws_packet_received(packet: packets.Packet) -> void:
    var sender_id := packet.get_sender_id()
    if packet.has_id():
        _handle_id_msg(sender_id, packet.get_id())

func _handle_id_msg(sender_id: int, id_msg: packets.IdMessage) -> void:
    GameManager.client_id = id_msg.get_id()
    GameManager.set_state(GameManager.State.INGAME)
```

You can see this is essentially the same as `main.gd`, so we don't need to go over it again. The only difference is that we are setting the client ID in the `GameManager` singleton when we receive it, and then transitioning to the **InGame** state.

Now, we can finish gutting the `main.gd` script and transfer its chatroom logic to a new `ingame.gd` script. First, let's add a **LineEdit** node to the `ingame.tscn` scene's **UI** node so that it matches what we had in `main.gd`. Remember to set the anchors the same way, to your liking. Then, attach a new script to the `ingame.tscn` scene's root node at `res://states/ingame/ingame.gd` with the following code:
```directory
/client/states/ingame/ingame.gd
```
```gd
extends Node

const packets := preload("res://packets.gd")

@onready var _line_edit := $UI/LineEdit as LineEdit
@onready var _log := $UI/Log as Log

func _ready() -> void:
    WS.connection_closed.connect(_on_ws_connection_closed)
    WS.packet_received.connect(_on_ws_packet_received)

    _line_edit.text_submitted.connect(_on_line_edit_text_entered)

func _on_ws_connection_closed() -> void:
    _log.error("Connection closed")

func _on_ws_packet_received(packet: packets.Packet) -> void:
    var sender_id := packet.get_sender_id()
    if packet.has_chat():
        _handle_chat_msg(sender_id, packet.get_chat())

func _handle_chat_msg(sender_id: int, chat_msg: packets.ChatMessage) -> void:
    _log.chat("Client %d" % sender_id, chat_msg.get_msg())

func _on_line_edit_text_entered(text: String) -> void:
    var packet := packets.Packet.new()
    var chat_msg := packet.new_chat()
    chat_msg.set_msg(text)
    
    var err = WS.send(packet)
    if err:
        _log.error("Error sending chat message")
    else:
        _log.chat("You", text)
    _line_edit.text = ""
```

Again, this is just a migration of the chatroom logic from `main.gd`, so we don't need to go over it again. This lets us completely get rid of everything in `main.gd` because now its only job is to set the game's state to **Entered** when the game starts.

```directory
/client/main.gd
```
```gd
extends Node

func _ready() -> void:
    GameManager.set_state(GameManager.State.ENTERED)
```

Now, if you run the game, you should see the chatroom working as expected, but now with the game's logic broken up into separate scenes and scripts. Congratulations! You have implemented a state machine on both the client and server sides of our MMO project. This is some much-needed organization that will pave the way to more complex features in the future.

Stay tuned for the [next part](/2024/11/10/godot-golang-mmo-part-5), where we will set up a database and implement user registration and login functionality. I hope to see you there!

---

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.