---
title: "§03 Add Real-Time Chat to Your Godot 4 MMO with Go"
description: "What's an MMO without a way to chat with your friends? Learn how to implement an interactive chatroom for your MMO using WebSockets and Protocol Buffers a solid foundation for your MMO."
redditurl: 
project: godot4golang
---

We’ve been focusing on the server side—but now it’s time to bring the client into the mix. In [the last post](/2024/11/09/godot-golang-mmo-part-2), we set up a Go server with WebSockets and Protocol Buffers to handle messages. Now, we’ll turn our attention to Godot 4 and implement a real-time chatroom.

In this tutorial, we’ll set up the client, connect it to the server, and create a chat log to display messages. By the end, players will be able to send and receive messages in real-time—a foundational feature for any MMO.

As always, if do you want to start here without viewing the previous lesson, feel free to download the source code for release [v0.02](https://github.com/tristanbatchler/Godot4Go_MMO/releases/tag/v0.02) in the [official GitHub repository](https://github.com/tristanbatchler/Godot4Go_MMO).

[If you prefer, you can view this lesson on YouTube](https://www.youtube.com/embed/D2dl9Bo8dOs).
<center><iframe style="max-width: 750px; width: 100%;" width="560" height="315" src="https://www.youtube.com/embed/D2dl9Bo8dOs" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></center>

## The WebSocket client in Godot

We will be lifting a lot of code from the [Godot documentation](https://docs.godotengine.org/en/stable/tutorials/networking/websocket.html#minimal-client-example) for this part. Create a new script called `websocket_client.gd` and paste the following code:

```directory
/client/websocket_client.gd
```
```gd
extends Node

const packets := preload("res://packets.gd")

var socket := WebSocketPeer.new()
var last_state := WebSocketPeer.STATE_CLOSED

signal connected_to_server()
signal connection_closed()
signal packet_received(packet: packets.Packet)

func connect_to_url(url: String, tls_options: TLSOptions = null) -> int:
    var err := socket.connect_to_url(url, tls_options)
    if err != OK:
        return err

    last_state = socket.get_ready_state()
    return OK


func send(packet: packets.Packet) -> int:
    packet.set_sender_id(0)
    var data := packet.to_bytes()
    return socket.send(data)


func get_packet() -> packets.Packet:
    if socket.get_available_packet_count() < 1:
        return null
    
    var data := socket.get_packet()
    
    var packet := packets.Packet.new()
    var result := packet.from_bytes(data)
    if result != OK:
        printerr("Error forming packet from data %s" % data.get_string_from_utf8())
    
    return packet

func close(code: int = 1000, reason: String = "") -> void:
    socket.close(code, reason)
    last_state = socket.get_ready_state()


func clear() -> void:
    socket = WebSocketPeer.new()
    last_state = socket.get_ready_state()


func get_socket() -> WebSocketPeer:
    return socket


func poll() -> void:
    if socket.get_ready_state() != socket.STATE_CLOSED:
        socket.poll()

    var state := socket.get_ready_state()

    if last_state != state:
        last_state = state
        if state == socket.STATE_OPEN:
            connected_to_server.emit()
        elif state == socket.STATE_CLOSED:
            connection_closed.emit()
    while socket.get_ready_state() == socket.STATE_OPEN and socket.get_available_packet_count():
        packet_received.emit(get_packet())


func _process(_delta: float) -> void:
    poll()
```

The purpose of this script is to simply wrap the built-in `WebSocketPeer` class, provide convenience methods for connecting, sending packets, and receiving packets. Then it is used as a means to emit signals every time activity occurs on the socket, which any other script can listen to. Because it is so self-contained, and only should be used for networking, it is a good candidate for a [singleton/autoload](https://docs.godotengine.org/en/stable/tutorials/scripting/singletons_autoload.html). 
1. Go to **Project > Project Settings > Globals**
2. Select the **AutoLoad** tab
3. Enter `res://websocket_client.gd` in the **Path** field
4. Enter `WS` in the **Node Name** field. This is what will allow us to access the WebSocket client instance from any script, e.g. `WS.connect_to_url("ws://127.0.0.1:8080")`
5. Click **Add** to save the settings and close the window
{% include img.html src="posts/2024/11/09/autoload.png" alt="Godot Autoload WebSocket Client" %}

## A little test

Let's use the main scene to test the WebSocket client out. Edit `main.gd`, we might as well try connecting to the server and sending a message.

```directory
/client/main.gd
```
```gd
extends Node

const packets := preload("res://packets.gd")

func _ready() -> void:
    WS.connected_to_server.connect(_on_ws_connected_to_server)
    WS.connection_closed.connect(_on_ws_connection_closed)
    WS.packet_received.connect(_on_ws_packet_received)
    
    print("Connecting to server...")
    WS.connect_to_url("ws://127.0.0.1:8080/ws")

func _on_ws_connected_to_server() -> void:
    var packet := packets.Packet.new()
    var chat_msg := packet.new_chat()
    chat_msg.set_msg("Hello, Golang!")
    
    var err := WS.send(packet)
    if err:
        print("Error sending packet")
    else:
        print("Sent packet")
    
func _on_ws_connection_closed() -> void:
    print("Connection closed")
    
func _on_ws_packet_received(packet: packets.Packet) -> void:
    print("Received packet from the server: %s" % packet)
```

If you run the game now, you should see the following output in the console:

```
Connecting to server...
Sent packet
```

And on the server side, you should see something like this:

```
2024/11/09 16:40:54 Starting server on :8080
2024/11/09 16:40:54 Awaiting client registrations...
2024/11/09 16:42:24 New client connected from [::1]:53684
```

Congratulations! You have successfully connected to the server and sent a message. We can edit the server to handle this message and send something back to prove the communication can work both ways. To do this, simply add some code to our up-until-now empty `ProcessMessage` function in `websocket.go`:

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) ProcessMessage(senderId uint64, message packets.Msg) {
    c.logger.Printf("Received message: %T from client - echoing back...", message)
    c.SocketSend(message)
}
```

We have effectively created an echo server, one which will send back whatever message it receives. If you restart the server and run the game now, you should see the following output in the Godot output:

```
Connecting to server...
Sent packet
Received packet from the server: sender_id: 1;
chat: {
  msg: "Hello, Golang!";
};
```

And something like this on the server side:

```
2024/11/09 16:54:59 Starting server on :8080
2024/11/09 16:54:59 Awaiting client registrations...
2024/11/09 16:55:01 New client connected from [::1]:53922
Client 1: 2024/11/09 16:55:01 Received message: *packets.Packet_Chat from client - echoing back...
```

Nice! We have a working echo server. There's just one problem I hinted at in the last post. What happens if two clients connect simultaneously?

## The problem with our server

Remember in the last post where I hinted that there's a big problem with the way we're generating client IDs? The hub is storing client interfaces in a map, and we are using the length of this map at the time of registration to generate a client ID.

This is a problem because the map is not thread-safe. If two clients connect at the same time, they could both be assigned the same client ID. This would be bound to cause all sorts of problems, so we should address this now.

To prove this, we can ask Godot to run multiple instances of the game at the same time. This is an important thing to know for when we start testing multiplayer features anyway, so it's worth reading on even if you believe me about the problem.

1. Go to **Debug > Custom Run Instances...**
2. Tick **Enable Multiple Instances**
3. Enter **2** or more in the number field just below the checkbox
4. Click **OK**
{% include img.html src="posts/2024/11/09/multiple_instances.png" alt="Godot Multiple Instances" %}

Now, if you run the game, you should see two windows pop up and connect to the server. If you look at the server output, you should see something like this:

```
2024/11/09 18:51:52 Starting server on :8080
2024/11/09 18:51:52 Awaiting client registrations...
2024/11/09 18:53:50 New client connected from [::1]:55699
2024/11/09 18:53:50 New client connected from [::1]:55700
(2) Client 1: 2024/11/09 18:53:50 Received message: *packets.Packet_Chat from client - echoing back...
```

The `(2)` indicates that the exact same message was logged twice, which means two clients both with the name "Client 1" received the message. This is obviously evidence of what we feared, that the client IDs are not unique. Now, you may not have seen this happen, but if you repeat the test a few times, you should see it eventually. Obviously we don't want our server to leave things to chance, so let's fix this.

## Making a custom data structure

Come to think of it, we really need a data structure that can hold a collection of objects, each requiring a unique ID. This kind of thing will end up being extremely useful not only for keeping track of clients, but also for game objects later on.

There is a data structure in Go called a `sync.Map` which is thread-safe, so we could use this, but I personally find it too clunky to work with because it is completely untyped. One of the reasons I like Go is because of its strong typing, so it seems a shame to throw that away. Instead, I'm going to create a custom data structure which basically encapsulates a regular map, but can generate unique IDs and handle locking internally to ensure only one point of access at a time.

Create a new folder called `objects` under `internal/server` and create a new file called `sharedCollection.go`. The only import we need is `sync` for the mutex, and we will make it part of an `objects` package.

```directory
/server/internal/server/objects/sharedCollection.go
```
```go
package objects

import "sync"

// A generic, thread-safe map of objects with auto-incrementing IDs.
type SharedCollection[T any] struct {
    objectsMap map[uint64]T
    nextId     uint64
    mapMux     sync.Mutex
}

func NewSharedCollection[T any](capacity ...int) *SharedCollection[T] {
    var newObjMap map[uint64]T

    if len(capacity) > 0 {
        newObjMap = make(map[uint64]T, capacity[0])
    } else {
        newObjMap = make(map[uint64]T)
    }

    return &SharedCollection[T]{
        objectsMap: newObjMap,
        nextId:     1,
    }
}
```

You can see that so far, the structure is very simple, only requiring the underlying map (what we were naively using before), a counter for the next ID, and a mutex to lock the map when we need to access it. We also have a constructor function which allows us to specify the initial capacity of the map, which is useful for performance reasons.

We are using a generic type `T` here, which will allow us to put anything we want in here. The use of generics here is what differs between our data structure and the `sync.Map`. Now let's see the methods we will need to interact with this structure.

```directory
/server/internal/server/objects/sharedCollection.go
```
```go
// Add an object to the map with the given ID (if provided) or the next available ID.
// Returns the ID of the object added.
func (s *SharedCollection[T]) Add(obj T, id ...uint64) uint64 {
    s.mapMux.Lock()
    defer s.mapMux.Unlock()

    thisId := s.nextId
    if len(id) > 0 {
        thisId = id[0]
    }
    s.objectsMap[thisId] = obj
    s.nextId++
    return thisId
}
```

Here's our first method, `Add`, which we are already using the `sync.Mutex` to lock the map while we are adding our object. This will prevent the kind of issue we experienced before.

```directory
/server/internal/server/objects/sharedCollection.go
```
```go
// Remove removes an object from the map by ID, if it exists.
func (s *SharedCollection[T]) Remove(id uint64) {
    s.mapMux.Lock()
    defer s.mapMux.Unlock()

    delete(s.objectsMap, id)
}
```

The `Remove` method doesn't need much explanation. It simply removes an object from the map by ID.

```directory
/server/internal/server/objects/sharedCollection.go
```
```go
// Call the callback function for each object in the map.
func (s *SharedCollection[T]) ForEach(callback func(uint64, T)) {
    // Create a local copy while holding the lock.
    s.mapMux.Lock()
    localCopy := make(map[uint64]T, len(s.objectsMap))
    for id, obj := range s.objectsMap {
        localCopy[id] = obj
    }
    s.mapMux.Unlock()

    // Iterate over the local copy without holding the lock.
    for id, obj := range localCopy {
        callback(id, obj)
    }
}
```

We need a way to iterate over the objects in our collection, so we define a `ForEach` method which takes a callback function as an argument. This kind of thing is pretty popular in languages like JavaScript and Go, and we will see it in action later. It's worth noting we only lock the map while we create a local copy of it to iterate over. This is ideal for two reasons:
1. We don't want any other goroutine to modify the map while we are iterating over it
2. If the callback function takes a long time to execute, we don't want to be holding the lock for that long as it could block other goroutines from accessing the map for an unnecessarily long time.

```directory
/server/internal/server/objects/sharedCollection.go
```
```go
// Get the object with the given ID, if it exists, otherwise nil.
// Also returns a boolean indicating whether the object was found.
func (s *SharedCollection[T]) Get(id uint64) (T, bool) {
    s.mapMux.Lock()
    defer s.mapMux.Unlock()

    obj, ok := s.objectsMap[id]
    return obj, ok
}
```

The `Get` method shouldn't need any explanation, and now for our final method:

```directory
/server/internal/server/objects/sharedCollection.go
```
```go
// Get the approximate number of objects in the map.
// The reason this is approximate is because we don't lock the map to get the length.
func (s *SharedCollection[T]) Len() int {
    return len(s.objectsMap)
}
```

The `Len` method might surprise you. We are not locking the map, so we can't rely on the length of the map being accurate. The reason for this is simple: I never found a reason to need an accurate number of objects in a shared collection at any point, so I figured we may as well save the performance hit of locking the map. If you need an accurate count, you can always manage the mutex as we did in each other method.

## Replacing the client map

Now that we have our new data structure, we can replace the map in the hub with it. We will also need to make some changes to the `RegisterClient` and `UnregisterClient` methods to use the new data structure.

First, import our `objects` package in `hub.go`:

```directory
/server/internal/server/hub.go
```
```go
package server

import (
    "log"
    "net/http"
    "server/internal/server/objects"
    "server/pkg/packets"
)
```

Next replace the `Clients` field in the `Hub` struct to be of type `*objects.SharedCollection[ClientInterfacer]`:

```directory
/server/internal/server/hub.go
```
```go
type Hub struct {
    Clients *objects.SharedCollection[ClientInterfacer]
    // ...
}
```

Also change the `NewHub` function to initialize the `Clients` field with a new `SharedCollection`:

```directory
/server/internal/server/hub.go
```
```go
func NewHub() *Hub {
    return &Hub{
        Clients: objects.NewSharedCollection[ClientInterfacer](),
        // ...
    }
}
```

Now there's quite a few changes to make in the `Run` method, so I'll just show you the whole thing:

```directory
/server/internal/server/hub.go
```
```go
func (h *Hub) Run() {
    log.Println("Awaiting client registrations...")
    for {
        select {
        case client := <-h.RegisterChan:
            client.Initialize(h.Clients.Add(client))
        case client := <-h.UnregisterChan:
            h.Clients.Remove(client.Id())
        case packet := <-h.BroadcastChan:
            h.Clients.ForEach(func(clientId uint64, client ClientInterfacer) {
                if clientId != packet.SenderId {
                    client.ProcessMessage(packet.SenderId, packet.Msg)
                }
            })
        }
    }
}
```

You can see we are taking advantage of the fact that the `Add` method returns the ID of the object added, so we can pass this directly to the `Initialize` method of the client. You can also see how the `ForEach` method works here, notice the syntax is not so different from a regular for loop.

We just have one more simple change to make in `websocket.go`, and that is to change the way we are obtaining the client interfacer from the hub in the `PassToPeer` method:
```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) PassToPeer(message packets.Msg, peerId uint64) {
    if peer, exists := c.hub.Clients.Get(peerId); exists {
        peer.ProcessMessage(c.id, message)
    }
}
```

Now, if we restart the server and try to repeat our test of running multiple instances of the game, we should see that the problem with duplicate client IDs is no longer present. The server output should look something like this:

```
2024/11/09 19:28:30 Starting server on :8080
2024/11/09 19:28:30 Awaiting client registrations...
2024/11/09 19:28:43 New client connected from [::1]:56397
2024/11/09 19:28:43 New client connected from [::1]:56396
Client 1: 2024/11/09 19:28:43 Received message: *packets.Packet_Chat from client - echoing back...
Client 2: 2024/11/09 19:28:43 Received message: *packets.Packet_Chat from client - echoing back...
```

That's much better! Now that we got that out the way, let's get back to the client and start building an interface for our chatroom.

## Building a custom log scene in Godot

We will create a "Log" class which will be a rich text label with helper functions. This will be the place where events, messages from the server, or chat messages can be logged, and it will make an appearance in quite a few places in the final game.

1. Create a new folder in the Godot FileSystem at `res://classes/log/`
2. Right-click the new `log` folder and select **Create new...** and then **Scene**
3. Enter **log** as the name of the scene
4. Choose **RichTextLabel** as the root node
5. Click **OK**
{% include img.html src="posts/2024/11/09/log_scene.png" alt="Godot Log Scene" %}

We will set the rich text label to take up the scene's entire area, but when we add it to other scenes, we can resize it as needed. To do this, simply use the handy anchor presets at the top of the editor and choose the **Full Rect** preset. 
{% include img.html src="posts/2024/11/09/full_rect_anchor.png" alt="Godot Full Rect Anchor" %}

Also be sure to enable **BBCode** in the **Inspector** panel on the right-hand side of the editor. This allows us to use BBCode tags in the text, so we can easily control the color of certain lines we add to the log.

Also enable **Scroll Active** and **Scroll Following** in the **Inspector** panel. This will ensure that the log will always scroll to the bottom when new messages are added.

Now we need to add some functionality to this scene. Attach a new script at `res://classes/log/log.gd` to the root `Log` node and paste the following code:

```directory
/client/classes/log/log.gd
```
```gd
class_name Log
extends RichTextLabel

func _message(message: String, color: Color = Color.WHITE) -> void:
    append_text("[color=#%s]%s[/color]\n" % [color.to_html(false), str(message)])

func info(message: String) -> void:
    _message(message, Color.WHITE)

func warning(message: String) -> void:
    _message(message, Color.YELLOW)

func error(message: String) -> void:
    _message(message, Color.ORANGE_RED)

func success(message: String) -> void:
    _message(message, Color.LAWN_GREEN)
    
func chat(sender_name: String, message: String) -> void:
    _message("[color=#%s]%s:[/color] [i]%s[/i]" % [Color.CORNFLOWER_BLUE.to_html(false), sender_name, message])
```

Note we are creating a new class out of this scene, so it's easy to find in the list of nodes when we want to add it to a scene, which we will see in the very next section.

The script is very simple, we are basically just adding helper functions to take advantage of the BBCode tags we enabled earlier. The `chat` function is a little more complex, as it will format the chat message in a way that makes it clear who sent the message.

Feel free to adjust the colors to your liking!

## Adding the log to the main scene
Back to the main scene, we can now add a new Log node under the root node. Simply right-click the root node and select **Add Child Node** and then **Log**. 
{% include img.html src="posts/2024/11/09/add_log_node.png" alt="Godot Add Log Node" %}

Using the anchor presets again, we can set the log to take up the bottom half of the screen by choosing **Bottom Wide** and then dragging the top of the log node to the middle of the screen. Don't worry if it's not perfect, this is just a prototype which will be replaced with a more sophisticated UI later on.

Now we can use the log in the main script to log messages from the server. Edit `main.gd` and replace every occurrence of `print` with the relevant log function:

```directory
/client/main.gd
```
```gd
extends Node

const packets := preload("res://packets.gd")

@onready var _log := $Log as Log

func _ready() -> void:
    WS.connected_to_server.connect(_on_ws_connected_to_server)
    WS.connection_closed.connect(_on_ws_connection_closed)
    WS.packet_received.connect(_on_ws_packet_received)
    
    _log.info("Connecting to server...")
    WS.connect_to_url("ws://127.0.0.1:8080/ws")

func _on_ws_connected_to_server() -> void:
    var packet := packets.Packet.new()
    var chat_msg := packet.new_chat()
    chat_msg.set_msg("Hello, Golang!")
    
    var err := WS.send(packet)
    if err:
        _log.error("Error sending packet")
    else:
        _log.success("Sent packet")
    
func _on_ws_connection_closed() -> void:
    _log.error("Connection closed")
    
func _on_ws_packet_received(packet: packets.Packet) -> void:
    _log.info("Received packet from the server: %s" % packet)
```

If you run the game now, you should conveniently see the messages in the actual game window, rather than having to check the output console.
{% include img.html src="posts/2024/11/09/log_messages.png" alt="Godot Log Messages" %}
<small>*the message received looks a little silly since we are Godot, not Golang, but **we** know it's just echoing back what we sent!*</small>

## Finishing out the chatroom

Believe it or not, we are actually very close to having a working chatroom. All we really need to do is add some packet handling logic to the server and client, and we can start chatting, at least to an extremely limited extent. Let's handle the server side first.

### Server side logic

The first thing to happen when a new client connects is that they should be sent their client ID. This will be the foundation for all future packet handling. Edit `websocket.go` and add two lines to the end of the `Initialize` method, so it looks like this:

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) Initialize(id uint64) {
    c.id = id
    c.logger.SetPrefix(fmt.Sprintf("Client %d: ", c.id))
    c.SocketSend(packets.NewId(c.id))
    c.logger.Printf("Sent ID to client")
}
```

We are using the helper function we wrote in part 1 to easily craft the ID message. This is defined in `/server/pkg/packets/util.go`.

Now, in the `ProcessMessage` method, we need to handle the chat message. Let's remove the echo functionality and {% include highlight.html anchor="add-chat-logic" text="add some logic to handle chat messages:" %}

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) ProcessMessage(senderId uint64, message packets.Msg) {
    if senderId == c.id {
        // This message was sent by our own client, so broadcast it to everyone else
        c.Broadcast(message)
    } else {
        // Another client interfacer passed this onto us, or it was broadcast from the hub,
        // so forward it directly to our own client
        c.SocketSendAs(message, senderId)
    }
}
```

Ignoring the fact that we don't check the type of the message or validate it in any way, this is all we need to do on the server side. We simply have two cases: the message came from our own client, or from someone else. In the first case, we know the message is intended for everyone else, so we broadcast it. In the second case, we know the message is intended for our client, so we send it directly.

Let's finish up the client side now.

### Client side logic

Before we can handle any packet logic, we need to create a way for the user to type and send messages. We will add a `LineEdit` node to the main scene, which will be used for this purpose. Right-click the root node and select **Add Child Node** and then **LineEdit**. Position it anywhere you like, but I chose to use the **Top Wide** anchor preset and placed it at the top of the screen.

So the main scene should now look something like this:
* **Main** (Node)
  * **Log** (custom `log.tscn`)
  * **LineEdit** (LineEdit)

Now we can add some logic to the main script to handle the user input. Edit `main.gd` and ensure to add a reference to our `LineEdit` node, and our client ID at the top of the script:
    
```directory
/client/main.gd
```
```gd
var client_id: int
@onready var _line_edit := $LineEdit as LineEdit
```

You can remove the test message we were sending to the server in the `_on_ws_connected_to_server` method, and replace it with a simple log message to indicate the connection was successful:

```directory
/client/main.gd
```
```gd
func _on_ws_connected_to_server() -> void:
    _log.success("Connected successfully")
```

Now, let's replace the `_on_ws_packet_received` method, to use some logic to handle the two kinds of messages we might receive: the ID message, and chat messages.

```directory
/client/main.gd
```
```gd
func _on_ws_packet_received(packet: packets.Packet) -> void:
    var sender_id := packet.get_sender_id()
    if packet.has_id():
        _handle_id_msg(sender_id, packet.get_id())
    elif packet.has_chat():
        _handle_chat_msg(sender_id, packet.get_chat())
```

We need to define the two helper functions `_handle_id_msg` and `_handle_chat_msg` now. The first one is simple, we just store the client ID in the `client_id` variable we defined at the top of the script:

```directory
/client/main.gd
```
```gd
func _handle_id_msg(sender_id: int, id_msg: packets.IdMessage) -> void:
    var client_id := id_msg.get_id()
    _log.info("Received client ID: %d" % client_id)
```

The second one is just as simple: we just log the message using the `chat` function we already defined!

```directory
/client/main.gd
```
```gd
func _handle_chat_msg(sender_id: int, chat_msg: packets.ChatMessage) -> void:
    _log.chat("Client %d" % sender_id, chat_msg.get_msg())
```

Finally, we just need a way to send messages. We can connect to our `LineEdit` node's `text_submitted` signal to a new method called `_on_line_edit_text_submitted`. Add the following line to the `_ready` method, just under where we connect the signals for the WebSocket client:

```directory
/client/main.gd
```
```gd
_line_edit.text_submitted.connect(_on_line_edit_text_submitted)
```

The `text_submitted` signal takes a single argument: the new text as a string (you can verify this by holding `Ctrl` and clicking on the signal's name in the script editor). We now know the signature of the method we need to create:

```directory
/client/main.gd
```
```gd
func _on_line_edit_text_submitted(text: String) -> void:
    var packet := packets.Packet.new()
    var chat_msg := packet.new_chat()
    chat_msg.set_msg(text)
    
    var err := WS.send(packet)
    if err:
        _log.error("Error sending chat message")
    else:
        _log.chat("You", text)
    _line_edit.text = ""
```

This method is very similar to the one we used to send the test message to the server, but we are now using the text entered by the user. We also clear the text in the `LineEdit` node after sending the message, so the user can easily type a new message.

Notice that we are not setting the `sender_id` on the packet here, and instead we are setting it as zero on `websocket_client.gd`. It is technically not necessary to set our own sender ID when sending a message, as the server will always know who the message is coming from. In fact, we did add some functionality on the server side to know that if the sender ID is zero, it should be replaced with the client ID of the client interfacer that passed the message to the server. We have done this simply out of convenience, as it means we don't have to pass the client ID to the client every time we want to send a message.

For reference, here is the full `main.gd` script in its entirety:

<details markdown="1">

<summary>Click to expand</summary>

```directory
/client/main.gd
```

```gd
extends Node

const packets := preload("res://packets.gd")

@onready var _log := $Log as Log
@onready var _line_edit := $LineEdit as LineEdit

func _ready() -> void:
	WS.connected_to_server.connect(_on_ws_connected_to_server)
	WS.connection_closed.connect(_on_ws_connection_closed)
	WS.packet_received.connect(_on_ws_packet_received)
	
	_line_edit.text_submitted.connect(_on_line_edit_text_submitted)
	
	_log.info("Connecting to server...")
	WS.connect_to_url("ws://localhost:8080/ws")
	
func _on_ws_connected_to_server() -> void:
	_log.success("Connected successfully")
	
func _on_ws_connection_closed() -> void:
	_log.warning("Connection closed")
	
func _on_ws_packet_received(packet: packets.Packet) -> void:
	var sender_id := packet.get_sender_id()
	if packet.has_id():
		_handle_id_msg(sender_id, packet.get_id())
	elif packet.has_chat():
		_handle_chat_msg(sender_id, packet.get_chat())

func _handle_id_msg(sender_id: int, id_msg: packets.IdMessage) -> void:
	var client_id := id_msg.get_id()
	_log.info("Received client ID: %d" % client_id)
	
func _handle_chat_msg(sender_id: int, chat_msg: packets.ChatMessage) -> void:
    _log.chat("Client %d" % sender_id, chat_msg.get_msg())
	
func _on_line_edit_text_submitted(text: String) -> void:
    var packet := packets.Packet.new()
    var chat_msg := packet.new_chat()
    chat_msg.set_msg(text)
    
    var err := WS.send(packet)
    if err:
        _log.error("Error sending chat message")
    else:
        _log.chat("You", text)
    _line_edit.text = ""
```

</details>

And just in case you need it, this is what the entire project structure should look like now:

<details markdown="1">
<summary>Project structure</summary>
```
/
├───.vscode/
│       launch.json
│       
├───client/
│   │   main.gd
│   │   main.tscn
│   │   packets.gd
│   │   websocket_client.gd
│   │
│   ├───addons/
│   │   └───protobuf/
│   │
│   ├───classes/
│   │   └───log/
│   │           log.gd
│   │           log.tscn
│   │
├───server/
│   │   go.mod
│   │   go.sum
│   │
│   ├───cmd/
│   │       debug_executable.exe
│   │       main.go
│   │
│   ├───internal/
│   │   └───server/
│   │       │   hub.go
│   │       │
│   │       ├───clients/
│   │       │       websocket.go
│   │       │
│   │       └───objects/
│   │               sharedCollection.go
│   │
│   └───pkg/
│       └───packets/
│               packets.pb.go
│               util.go
│
└───shared/
        packets.proto
```
</details>

Now, if you restart the server and run the game, you should be able to type messages into the `LineEdit` node and see them appear in the log. If you run multiple instances of the game, you should see the messages appear in the logs of all the clients. You can now chat with yourself!
{% include img.html src="posts/2024/11/09/chatroom.png" alt="Godot Chatroom" %}

## Conclusion

We've made great progress in building a functional chatroom for our MMO. Not only have we set up a real-time messaging system between the client and server, but we have also fixed a major issue with our server, created a custom data structure to handle client interfacer objects, and made our own custom log in Godot, which will be a useful tool for debugging and logging in the future.


In <strong><a href="/2024/11/10/godot-golang-mmo-part-4" class="sparkle-less">the next post</a></strong>, enhance the message handling logic on both the server and client sides by implementing state machines. This will set the stage for more complex game mechanics and help us build a more immersive and scalable game world. Don’t miss it – see you there!

---

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.
