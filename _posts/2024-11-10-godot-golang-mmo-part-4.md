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
│       │       websocketclient.go
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

You should see errors comaplining that our `WebSocketClient` type doesn't implement `ClientInterfacer` because it doesn't have a `SetState` method. Let's fix that by adding a `state` field to our `WebSocketClient` struct:

```directory
/server/internal/server/clients/websocketclient.go
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
/server/internal/server/clients/websocketclient.go
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
/server/internal/server/clients/websocketclient.go
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
/server/internal/server/clients/websocketclient.go
```
```go
func (c *WebSocketClient) ProcessMessage(senderId uint64, message packets.Msg) {
    c.state.HandleMessage(senderId, message)
}
```

The last thing we should do is ensure we set the client's state to `nil` when the client connection is closed. This is important because we don't want to keep a reference to the client's state after the client has disconnected. We can do this by adding a call to `SetState(nil)` in the `Close` method of the `WebSocketClient`:

```directory
/server/internal/server/clients/websocketclient.go
```
```go
func (c *WebSocketClient) Close(reason string) {
    // ...
    c.SetState(nil)
    // ...
}
```

Yet again, we've made a lot of changes, so it's a good idea to restart the server and make sure everything is still working as expected. If it is, congratulations! You've successfully implemented a basic state machine system for the server side of our MMO project. 