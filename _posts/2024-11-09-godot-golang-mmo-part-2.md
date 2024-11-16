---
title: §02 Building a WebSocket game server in Go for a Godot 4 MMO
description: Learn how to set up a WebSocket server in Go to power multiplayer functionality in your Godot 4 MMO.
redditurl: 
---

Let's send some packets! In [the last post](/2024/11/09/godot-golang-mmo-part-1), we laid the foundation for our Godot 4 MMO project: we set up our project, installed dependencies, and created our first packets. Now we will set up a simple WebSocket server in Go that can await connections and process them in a websockets hub.

## Introducing the server architecture

### WebSockets
For our goal of creating a cross-platform MMO, it is important to consider the technologies and architecture we will use. WebSockets are a great choice for us, as they are simple to use and well-supported across all platforms, including the web. The only downside is that they are not well-suited for very fast-pasted games, because the protocol relies on a TCP connection and will ensure that packets are delivered in order. Contrast this with UDP, which is used in most fast-paced games, and will drop packets if they are not delivered in time. However, you will find that even for a mildly fast-paced game like what we are building, and what most online RPG games are like, WebSockets are more than adequate. The only other viable choice for us would be WebRTC, but it is so complex that this series would be pretty much inaccessible to most people.

### Hub and spoke architecture
The server will deal with two types: those implementing the `ClientInterfacer` (in our case, we will create a `WebSocketClient` type), and `Hub`. The client interfacer is a flexible type that standardizes how each client connects and communicates with the hub, enabling us to implement other client types in the future if needed. The server passes incoming connections to the hub, which in turn creates a new client interfacer. This is on a per-connection basis. A client interfacer acts as an intermediary between the Godot websocket connection and the hub. The hub maintains a set of registered clients and broadcasts messages to them.

The application runs one goroutine for the hub and two goroutines for each client interfacer. 
> <img class="info" src="/assets/images/info.png" /> A **goroutine** is basically a function that can effortlessly run in a lightweight thread, allowing your main code to flow uninterrupted. The goroutines can safely communicate with each other using **channels**: a way to synchronize data between goroutines without the need for locks or mutexes.

The hub has channels for registering and unregistering client interfacers, and broadcasting messages. A client interfacer has a channel of outbound messages, as well as two goroutines:
1. one for waiting and reading messages from the outbound messages channel and writing them to the websocket, and
2. another for waiting and reading messages from the websocket and processing them accordingly.

Here is a diagram showing two Godot clients connected to the server.
![Server architecture](/assets/css/images/posts/2024/11/09/architecture.svg)

## Creating the Hub and ClientInterfacer

Let's get this set up! 
1. Create a new folder called `internal` inside your `server` folder. 
2. Inside `internal`, create another folder called `server`
3. Inside `internal/server`, create new file called `hub.go` and add the following:

```directory
/server/internal/server/hub.go
```
```go
package server

import (
    "log"
    "net/http"
    "server/pkg/packets"
)

// A structure for the connected client to interface with the hub
type ClientInterfacer interface {
    Id() uint64
    ProcessMessage(senderId uint64, message packets.Msg)

    // Sets the client's ID and anything else that needs to be initialized
    Initialize(id uint64)

    // Puts data from this client in the write pump
    SocketSend(message packets.Msg)

    // Puts data from another client in the write pump
    SocketSendAs(message packets.Msg, senderId uint64)

    // Forward message to another client for processing
    PassToPeer(message packets.Msg, peerId uint64)

    // Forward message to all other clients for processing
    Broadcast(message packets.Msg)

    // Pump data from the connected socket directly to the client
    ReadPump()

    // Pump data from the client directly to the connected socket
    WritePump()

    // Close the client's connections and cleanup
    Close(reason string)
}

// The hub is the central point of communication between all connected clients
type Hub struct {
    Clients map[uint64]ClientInterfacer

    // Packets in this channel will be processed by all connected clients except the sender
    BroadcastChan chan *packets.Packet

    // Clients in this channel will be registered with the hub
    RegisterChan chan ClientInterfacer

    // Clients in this channel will be unregistered with the hub
    UnregisterChan chan ClientInterfacer
}

func NewHub() *Hub {
    return &Hub{
        Clients:        make(map[uint64]ClientInterfacer),
        BroadcastChan:  make(chan *packets.Packet),
        RegisterChan:   make(chan ClientInterfacer),
        UnregisterChan: make(chan ClientInterfacer),
    }
}

func (h *Hub) Run() {
    log.Println("Awaiting client registrations")
    for {
        select {
        case client := <-h.RegisterChan:
            client.Initialize(uint64(len(h.Clients)))
        case client := <-h.UnregisterChan:
            h.Clients[client.Id()] = nil
        case packet := <-h.BroadcastChan:
            for id, client := range h.Clients {
                if id != packet.SenderId {
                    client.ProcessMessage(packet.SenderId, packet.Msg)
                }
            }
        }
    }
}

// Creates a client for the new connection and begins the concurrent read and write pumps
func (h *Hub) Serve(getNewClient func(*Hub, http.ResponseWriter, *http.Request) (ClientInterfacer, error), writer http.ResponseWriter, request *http.Request) {
    log.Println("New client connected from", request.RemoteAddr)
    client, err := getNewClient(h, writer, request)

    if err != nil {
        log.Printf("Error obtaining client for new connection: %v\n", err)
        return
    }

    h.RegisterChan <- client

    go client.WritePump()
    go client.ReadPump()
}
```

The definitions and logic in this file are just direct translations of the architecture we discussed above. The `Hub` type maintains a map of connected clients, and has channels for registering and unregistering clients, as well as broadcasting messages. The `ClientInterfacer` interface defines the functions that a client must implement to be able to communicate with the hub.

The hub's `Run` function is the main loop of the hub, where it listens for messages on the channels and processes them accordingly. The keen-eyed among you will notice that we are initializing each client with an ID equal to the length of the `Clients` map. This is a naive way to give each client a unique ID, but it has an enormous issue which we will have to address in a future post (since this post will be too long and arduous if we do it now). Try and think about what the issue might be, but for now it can be our little secret.


## Creating the WebSocketClient

Before we can create our websockets implementation of the client interfacer, we need to install a package to help us work with websockets. We will be using the [Gorilla WebSocket](https://github.com/gorilla/websocket) package, which is a popular package for working with websockets in Go. To install it, run the following command in your terminal:

```bash
cd server # If you're not already in the server directory
go get github.com/gorilla/websocket
```

In case we ever want to create more implementations, we will create a `clients` folder inside our `internal/server` folder, and create a new file called `websocket.go` inside there. I am going to show a skeleton of this new file, and then run by the implementation of each function from the `ClientInterfacer` interface in the next steps.

```directory
/server/internal/server/clients/websocket.go
```
```go
package clients

import (
    "fmt"
    "log"
    "net/http"

    "server/internal/server"
    "server/pkg/packets"

    "github.com/gorilla/websocket"
    "google.golang.org/protobuf/proto"
)
```

To be clear, your server structure should look like this now:
```
/server
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
│       └───clients
│               websocket.go
│
└───pkg
    └───packets
            packets.pb.go
            util.go
```

Ok, first let's look at the type definition itself for the `WebSocketClient` type. This will be a struct that contains the necessary fields for the websocket connection to keep its state. The implementation will depend on these fields.

```directory
/server/internal/server/clients/websocket.go
```
```go
type WebSocketClient struct {
    id       uint64
    conn     *websocket.Conn
    hub      *server.Hub
    sendChan chan *packets.Packet
    logger   *log.Logger
}
```

A lot of this is self-explanatory, especially if you compare with the diagram at the beginning of this post. The `hub` field is a reference to the hub which created this client. The `sendChan` is a channel that holds packets to be sent to the client. We are also using the built-in `log` package to log messages to the console, since it can get tricky to keep track of what's happening in the server without it.

```directory
/server/internal/server/clients/websocket.go
```
```go
func NewWebSocketClient(hub *server.Hub, writer http.ResponseWriter, request *http.Request) (server.ClientInterfacer, error) {
    upgrader := websocket.Upgrader{
        ReadBufferSize:  1024,
        WriteBufferSize: 1024,
        CheckOrigin:     func(_ *http.Request) bool { return true },
    }

    conn, err := upgrader.Upgrade(writer, request, nil)

    if err != nil {
        return nil, err
    }

    c := &WebSocketClient{
        hub:      hub,
        conn:     conn,
        sendChan: make(chan *packets.Packet, 256),
        logger:   log.New(log.Writer(), "Client unknown: ", log.LstdFlags),
    }

    return c, nil
}
```

This is a static function, not required by the interface, but makes it easy to create a new websocket client from an HTTP connection (which is what the main server will receive from each new Godot connection). We use the `upgrader` to upgrade the HTTP connection to a websocket connection. We then create a new `WebSocketClient` struct and return it. Note we are using a **buffered channel** for the `sendChan`. This means that the channel can hold up to 256 packets before it blocks. This is a good way to prevent the server from blocking if the client is slow to read packets.

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) Id() uint64 {
    return c.id
}

func (c *WebSocketClient) Initialize(id uint64) {
    c.id = id
    c.logger.SetPrefix(fmt.Sprintf("Client %d: ", c.id))
}

func (c *WebSocketClient) ProcessMessage(senderId uint64, message packets.Msg) {
}
```

These are all pretty straightforward, and I think the code speaks for itself. I will point out that our logger is now prefixed with the client's ID, so we can easily see which client is doing what (invaluable when we have multiple clients connected). We don't know what we want to do with incoming messages yet, so we leave `ProcessMessage` empty for now to satisfy the interface.

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) SocketSend(message packets.Msg) {
    c.SocketSendAs(message, c.id)
}

func (c *WebSocketClient) SocketSendAs(message packets.Msg, senderId uint64) {
    select {
    case c.sendChan <- &packets.Packet{SenderId: senderId, Msg: message}:
    default:
        c.logger.Printf("Client %d send channel full, dropping message: %T", c.id, message)
    }
}
```

These functions are used to queue messages up to be sent to the client. We use a `select` statement to send the message to the channel, but if the channel is full, we drop the message and log a warning.

The difference between `SocketSend` and `SocketSendAs` is that `SocketSendAs` allows us to specify a sender ID. This is useful when we want to forward a message we received from another client, and the Godot client can know who it came from easily.

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) PassToPeer(message packets.Msg, peerId uint64) {
    if peer, exists := c.hub.Clients[peerId]; exists {
        peer.ProcessMessage(c.id, message)
    }
}

func (c *WebSocketClient) Broadcast(message packets.Msg) {
    c.hub.BroadcastChan <- &packets.Packet{SenderId: c.id, Msg: message}
}
```

These functions are used to forward messages to other clients. `PassToPeer` forwards a message to a specific client, while `Broadcast` is just a convenience function to queue a message up to be passed to every client except the sender by the hub.

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) ReadPump() {
    defer func() {
        c.logger.Println("Closing read pump")
        c.Close("read pump closed")
    }()

    for {
        _, data, err := c.conn.ReadMessage()
        if err != nil {
            if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
                c.logger.Printf("error: %v", err)
            }
            break
        }

        packet := &packets.Packet{}
        err = proto.Unmarshal(data, packet)
        if err != nil {
            c.logger.Printf("error unmarshalling data: %v", err)
        }

        // To allow the client to lazily not set the sender ID, we'll assume they want to send it as themselves
        if packet.SenderId == 0 {
            packet.SenderId = c.id
        }

        c.ProcessMessage(packet.SenderId, packet.Msg)
    }
}
```

Here is one of two functions that directly interfaces with the websocket connection from the Godot client. It is responsible for reading messages from the websocket and processing them. We use the `proto` package to convert the raw bytes into a `Packet` struct (we saw this in the last post). We then call `ProcessMessage` with the sender ID and the message. Notice how we defer a closure of the client (we will see the code for this soon) so that we can clean up the connection if an error occurs or the loop breaks.

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) WritePump() {
    defer func() {
        c.logger.Println("Closing write pump")
        c.Close("write pump closed")
    }()

    for packet := range c.sendChan {
        writer, err := c.conn.NextWriter(websocket.BinaryMessage)
        if err != nil {
            c.logger.Printf("error getting writer for %T packet, closing client: %v", packet.Msg, err)
            return
        }

        data, err := proto.Marshal(packet)
        if err != nil {
            c.logger.Printf("error marshalling %T packet, dropping: %v", packet.Msg, err)
            continue
        }

        _, writeErr := writer.Write(data)

        if writeErr != nil {
            c.logger.Printf("error writing %T packet: %v", packet.Msg, err)
            continue
        }

        writer.Write([]byte{'\n'})

        if closeErr := writer.Close(); closeErr != nil {
            c.logger.Printf("error closing writer, dropping %T packet: %v", packet.Msg, err)
            continue
        }
    }
}
```

Here's the other function that talks directly to Godot. It reads off packets we've queued in the send channel, converts them to bytes, and sends them down the wire. It is important to note that we are creating a **binary** message writer, since protobuf messages are binary. We also append a newline character to the end of every message to help prevent messages from "sticking" together.

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) Close(reason string) {
    c.logger.Printf("Closing client connection because: %s", reason)

    c.hub.UnregisterChan <- c
    c.conn.Close()
    if _, closed := <-c.sendChan; !closed {
        close(c.sendChan)
    }
}
```

Finally, we have the `Close` function we deferred in the `ReadPump` and `WritePump` functions. This function is responsible for cleaning up the client's connection, and also unregistering the client from the hub (so that the hub may in turn remove it from its list of clients). We aren't *really* doing anything meaningful with the reason string yet, but it's there for future use.

## Tying it all together

Now that we have our `Hub` and `WebSocketClient` types set up, all that's left on the server side is to tie everything together in our `main.go` file we created in the last post.

```directory
/server/cmd/main.go
```
```go
package main

import (
    "flag"
    "fmt"
    "log"
    "net/http"

    "server/internal/server"
    "server/internal/server/clients"
)

var (
    port = flag.Int("port", 8080, "Port to listen on")
)

func main() {
    flag.Parse()

    // Define the game hub
    hub := server.NewHub()

    // Define handler for WebSocket connections
    http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
        hub.Serve(clients.NewWebSocketClient, w, r)
    })

    // Start the server
    go hub.Run()
    addr := fmt.Sprintf(":%d", *port)

    log.Printf("Starting server on %s", addr)
    err := http.ListenAndServe(addr, nil)

    if err != nil {
        log.Fatalf("Failed to start server: %v", err)
    }

}
```

This is all pretty in-line with the diagram we saw at the beginning of this post. The only thing to note is that this is a generic TCP server, but the handler we have defined for the `/ws` route will upgrade the connection to a websocket connection. This is where we will be sending our Godot clients.

We can now run the server by hitting **F5** in VS Code, or running `go run cmd/main.go` in the terminal. If you see the following output in the debug console, then you're good to go:
```
2024/11/09 12:00:58 Starting server on :8080
2024/11/09 12:00:58 Awaiting client registrations
```

This is a good place to stop for now. In <strong><a href="/2024/11/09/godot-golang-mmo-part-3" class="sparkle-less">the next post</a></strong>, we'll integrate the Godot client with our server, allowing it to establish connections and send packets, bringing us one step closer to a functional multiplayer game. Stay tuned!

---

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.