---
title: Godot 4 Golang MMO Part 3
description: How to make an online chatroom with Godot 4 and Go
redditurl: 
---

We've been neglecting the client side until now... In [the last post](/2024/11/09/godot-golang-mmo-part-2), we built a websocket server in Go that is ready to start receiving our protocol buffer messages. In this post, we can finally start building the Godot and get a basic chatroom working.

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

The purpose of this script is to simply wrap the built-in `WebSocketPeer` class, provide convenience methods for connecting, sending packets, and receiving packets. Then it is used as a means to emit signals everytime activity occurs on the socket, which any other script can listen to. Because it is so self-contained, and only should be used for networking, it is a good candidate for a [singleton/autoload](https://docs.godotengine.org/en/stable/tutorials/scripting/singletons_autoload.html). 
1. Go to **Project > Project Settings > Globals**
2. Select the **AutoLoad** tab
3. Enter `res://websocket_client.gd` in the **Path** field
4. Enter `WS` in the **Node Name** field. This is what will allow us to access the WebSocket client instance from any script, e.g. `WS.connect_to_url("ws://localhost:8080")`
5. Click **Add** to save the settings and close the window
![Godot Autoload WebSocket Client](/assets/css/images/posts/2024/11/09/autoload.png)

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
    WS.connect_to_url("ws://localhost:8080/ws")

func _on_ws_connected_to_server() -> void:
    var packet := packets.Packet.new()
    packet.set_sender_id(69)
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
2024/11/09 16:40:54 Awaiting client registrations
2024/11/09 16:42:24 New client connected from [::1]:53684
```

Congratulations! You have successfully connected to the server and sent a message. We can edit the server to handle this message and send something back to prove the communication can work both ways. To do this, simply add some code to our up-until-now empty `ProcessMessage` function in `websocketclient.go`:

```directory
/server/internal/server/clients/websocketclient.go
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
2024/11/09 16:54:59 Awaiting client registrations
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
![Godot Multiple Instances](/assets/css/images/posts/2024/11/09/multiple_instances.png)

Now, if you run the game, you should see two windows pop up and connect to the server. If you look at the server output, you should see something like this:

```
2024/11/09 18:51:52 Starting server on :8080
2024/11/09 18:51:52 Awaiting client registrations
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
// The reason this is approximate is because the map is locked while counting.
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

Also change the `NewHub` function to initialise the `Clients` field with a new `SharedCollection`:

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
    log.Println("Awaiting client registrations")
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

You can see we are taking advantage of the fast that the `Add` method returns the ID of the object added, so we can pass this directly to the `Initialize` method of the client. You can also see how the `ForEach` method works here, notice the syntax is not so different from a regular for loop.

We just have one more simple change to make in `websocketclient.go`, and that is to change the way we are obtaining the client interfacer from the hub in the `PassToPeer` method:
```directory
/server/internal/server/clients/websocketclient.go
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
2024/11/09 19:28:30 Awaiting client registrations
2024/11/09 19:28:43 New client connected from [::1]:56397
2024/11/09 19:28:43 New client connected from [::1]:56396
Client 1: 2024/11/09 19:28:43 Received message: *packets.Packet_Chat from client - echoing back...
Client 2: 2024/11/09 19:28:43 Received message: *packets.Packet_Chat from client - echoing back...
```

That's much better! Now that we got that out the way way, let's get back to the client and start building an interface for our chatroom.

## Building the chatroom interface