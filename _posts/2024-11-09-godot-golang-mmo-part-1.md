---
title: Godot 4 Golang MMO Part 1
description: How to setup everything you need to get started with a Godot 4 MMO using Golang as the backend.
redditurl: 
---

Ready to get started? In [the last post](/2024/11/08/godot-golang-mmo-intro), we had some explaining to do. In this post, we will install some tools we need to get started, setup our packet system, and create an extremely simple means of communicating these packets between the server and the client.

## Installing essential tools

Let's quickly install Golang and Godot, and then we will get to the fun stuff!

### Golang

Head over to the [Golang download page](https://golang.org/dl) and simply follow the instructions for your OS. For reference, this project was created with version 1.23.3, but I don't imagine there will be any issues with newer versions.

Test your installation by running `go version` in your terminal. You should see something like `go version go1.23.3 windows/amd64`, of course, with your OS and architecture. If you get an error, try closing and reopening your terminal.

### Godot

[The Godot website](https://godotengine.org) should detect your OS and provide you with the latest download link. One thing I love about Godot is that it doesn't require an installation, you can simply unzip the download wherever you like and run the executable!

At the time of writing, Godot 4.4 is almost out. It has a feature I am excited to use, so I will be using the experimental release. You should use the latest stable release if you are reading this in the future.

One thing to ensure is that you get the **Standard** version of Godot, not the .NET version. This allows us to code in GDScript in the built-in editor, which is what we will be doing for this project.

### Protocol buffers compiler

Since we are using Protocol Buffers to generate code for our packets, we need to install the compiler, `protoc`. This is the tool that will take our `.proto` file (a simplistic way to define our packets) and turn them into code we can use.

1. Manually download from [the latest release](https://github.com/protocolbuffers/protobuf/releases/latest) the zip file corresponding to your operating system and computer architecture (`protoc-<version>-<os>-<arch>.zip`), or on Windows, it will be `protoc-<version>-win64.zip`.
2. Unzip the archive your directory of your choice, but preferably one of the following standard locations:
    * `C:\Users\<Name>\AppData\Local` on Windows
    * `/usr/local/bin` on Unix
3. Add the `bin` folder to your system's `PATH` environment variable.
    * **On Windows**, you can press **Win + R**, type `SystemPropertiesAdvanced`, click **Environment Variables**, and under **User variables**, double click on `Path`, then click **New** and paste the path to the `bin` folder, which should look something like `C:\Users\<Name>\AppData\Local\protoc-<version>-win64\bin`. Press **OK** on all the windows you opened.
    ![Windows PATH](/assets/css/images/posts/2024/11/09/windows-path.png)

    * **On Unix**, you can add the following line to your `.bashrc` or `.zshrc` file:
    ```bash
    export PATH="$PATH:/usr/local/bin/protoc-<version>-<os>-<arch>/bin"
    ```

Test your installation by running `protoc --version` in your terminal. You should see something like `libprotoc 28.3`. If you get an error, try closing and reopening your terminal.


That's it for now! We will grab the other tools as we need them.

## Hello, world!

To make sure we can at least get something running, let's create our main Go file.

Create a new folder for your project (I will call mine `RadiusRumble`, but will often refer to it just as `/`). Create the following structure, which is a common Go project layout. If you are interested, you can read more about it [here](https://github.com/golang-standards/project-layout?tab=readme-ov-file#go-directories).
```
/
└───server/
    └───cmd/
            main.go
```

Inside `main.go`, add the following code:

```directory
/server/cmd/main.go
```
```go
package main

import "fmt"

func main() {
    fmt.Println("Hello, world!")
}
```

Now, open your terminal, navigate to your folder, and run the application: 
```bash
go run server/cmd/main.go
```
You should see `Hello, World!` printed to the console. If you see an error, check your system's `PATH` variable and double-check your Go installation.

## Quality of life

I am willing to bet a good majority of you are using Visual Studio Code. If you already have your own preferred setup, feel free to skip this section.

We should really take a moment to install the [Go for VS Code](https://marketplace.visualstudio.com/items?itemName=golang.go) extension. It is kind of a must.

Now, let's create our debug configuration and install the debugger.
1. Open the debug tab on the left sidebar, or with **Ctrl + Shift + D**
2. Click on **create a launch.json file**
3. Choose **Go: Launch package** from the dropdown list
4. A folder called `.vscode` will be created in your project root, with a file called `launch.json`. Replace its contents with the following:

```directory
/.vscode/launch.json
```
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Launch Package",
            "type": "go",
            "request": "launch",
            "mode": "auto",
            "program": "${workspaceFolder}/server/cmd/main.go"
        }
    ]
}
```

Now you should be able to simply press **F5** to run your program, and look at the output in the **Debug console** tab at the bottom.

If you see an error saying `dlv` is not installed, you can simply press the **Install** button that appears in the error message. If you don't see this, you can install it manually: 
```bash
go get -u github.com/go-delve/delve/cmd/dlv
```

## Defining our packets

The heart of our project will be how we decide to communicate between the server and the client. Over the wel, this might be done with JSON or XML, but we have the freedom to do whatever we want. We could even use a packed binary format for maximum efficiency, but to keep things semi-readable and reduce the chance of errors and writing the same code twice (once for the server and once for the client), we will use Protobuf.

Create a new folder called `shared` in your project root, and inside it, create a new file called `packets.proto`. Your project structure should now look like this:
```
/
├───.vscode/
│       launch.json
│
├───server/
│   └───cmd/
│           main.go
│
└───shared/
        packets.proto
```

Inside `packets.proto`, add the following code:

```directory
/shared/packets.proto
```
```protobuf
syntax = "proto3";
package packets;
option go_package = "pkg/packets";

// Define your messages
message ChatMessage { string msg = 1; }
message DenyMessage { string reason = 1; }
message IdMessage { uint64 id = 1; }

// Define the main Packet message
message Packet {
    uint64 sender_id = 1;
    oneof msg {
        ChatMessage chat = 2;
        DenyMessage deny = 3;
        IdMessage id = 4;
    }
}
```

The way we are defining our packets is pretty useful. We have a wrapper called `Packet`, which encapsulates a *message* being anything we want to send, together with an ID to identify the sender. This way, we can easily add new messages, send/receive them, and know who they are from. Surprisingly, a **lot** can be done with just this basic structure.

As for the messages we have defined to start with, we have a `ChatMessage` for sending chat messages, a `DenyMessage` for when the server denies a request, and an `IdMessage` for when the server sends a client its ID.

Before we can use these messages, we need to compile them into Go code. Before we can do that, we need to install the Go protocol buffers plugin:
```bash
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
```

Now we're free to go ahead and compile our `.proto` file. Run the following command in your terminal:
```bash
protoc -I="shared" --go_out="server" "shared/packets.proto"
```

You should see some new files appear in your `server` folder under `pkg/`:
```
/server/
├───cmd/
└───pkg/
    └───packets/
            packets.pb.go
```

This is where our generated code will live. We don't even have to look at it, but feel free to take a peek if you're curious. The important thing is that we can now use it by importing the `packets` package. Let's try it out in our `main.go` file.

## Making packets in Go

In order to import our new package, we need to initialize a Go module inside our `server` folder. It's pretty common to name your module after your GitHub repository, but you can realistically name it whatever you want:
```bash
cd server
go mod init server
go mod tidy
```

You should see the creation of a `go.mod` and `go.sum` file in your `server` folder. Now we can import our `packets` package in `main.go`:

```go
package main

import (
    "fmt"
    "server/pkg/packets"
)

func main() {
    packet := &packets.Packet{
        SenderId: 69,
        Msg: &packets.Packet_Chat{
            Chat: &packets.ChatMessage{
                Msg: "Hello, world!",
            },
        },
    }

    fmt.Println(packet)

}

```

When you run your program, you should see the following output:
```
sender_id:69 chat:{msg:"Hello, world!"}
```

So, I'll be the first to admit: this looks like a lot of work for a simple message, so I create helper functions to make it easier to create packets. I define that in a new file called `util.go` under `/server/pkg/packets/`:

```directory
/server/pkg/packets/util.go
```
```go
package packets

type Msg = isPacket_Msg

func NewChat(msg string) Msg {
    return &Packet_Chat{
        Chat: &ChatMessage{
            Msg: msg,
        },
    }
}

func NewDeny(reason string) Msg {
    return &Packet_Deny{
        Deny: &DenyMessage{
            Reason: reason,
        },
    }
}

func NewId(id uint64) Msg {
    return &Packet_Id{
        Id: &IdMessage{
            Id: id,
        },
    }
}
```

Now we can simplify our `main.go` file:

```directory
/server/cmd/main.go
```
```go
// ...
packet := &packets.Packet{
    SenderId: 69,
    Msg:      packets.NewChat("Hello, world!"),
}
fmt.Println(packet)

```

We can even serialize our packet to see what it will look like over the wire:
```directory
/server/cmd/main.go
```
```go
package main

import (
    "fmt"
    "server/pkg/packets"

    "google.golang.org/protobuf/proto"
)

func main() {
    packet := &packets.Packet{
        SenderId: 69,
        Msg:      packets.NewChat("Hello, world!"),
    }

    data, _ := proto.Marshal(packet)
    fmt.Println(data)
}
```

When you run your program, you should see the following output:
```
[8 69 18 15 10 13 72 101 108 108 111 44 32 119 111 114 108 100 33]
```

Those are the bytes that represent our packet. It's not very human-readable, but it verifies that we are easily able to send this between the server and the client. We can even deserialize it back like this:
```directory
/server/cmd/main.go
```
```go
package main

import (
    "fmt"
    "server/pkg/packets"

    "google.golang.org/protobuf/proto"
)

func main() {
    data := []byte{8, 69, 18, 15, 10, 13, 72, 101, 108, 108, 111, 44, 32, 119, 111, 114, 108, 100, 33}
    packet := &packets.Packet{}
    proto.Unmarshal(data, packet)
    fmt.Println(packet)
}
```

```
sender_id:69  chat:{msg:"Hello, world!"}
```

## Setting up the Godot project

I do suppose we'd better see how this all looks from the client perspective. Create a new Godot project in the same root folder as your server project. I will call mine simply `client`. Make sure to select the **Compatibility** renderer if you want to export to the web, but you can always change this later.
![Godot new project](/assets/css/images/posts/2024/11/09/godot-new-project.png)

First, let's install the Godobuf plugin.
1. Download the [latest release](https://github.com/oniksan/godobuf/releases/latest). It should be called **Source code (zip)**
2. Unzip the archive somewhere on your computer
3. Copy the `addons` folder to your `client` project folder. Your project structure should look like this:
    ```
    /
    ├───.vscode/
    ├───client/
    ├───addons/
    │   └───protobuf/
    ├───server/
    └───shared/
    ```
4. Open your Godot project and enable the addon by going to **Project > Project Settings > Plugins** and enabling the **Protobuf** plugin.
    ![Godot plugins](/assets/css/images/posts/2024/11/09/godot-plugins.png)

You should see a new **Godobuf** tab appear in the bottom left panel, underneath the scene tree, adjacent to the **FileSystem** tab. This is where we can input our `.proto` file and generate our code.

1. Click on the **Godot** tab
2. Click on the **...** button under **Input protobuf file** and navigate up a level to your `shared/packets.proto` file. For some reason, it shows a warning that you will "overwrite" the file, but this is not the case. Just choose **OK**
3. Click on the **...** button under **Output GDScript file**, enter simply `packets.gd` and click **OK**
   ![Godobuf output](/assets/css/images/posts/2024/11/09/godobuf-output.png)
4. Click on **Compile** and you should see a popup appear saying **Compile success done** if it worked correctly
    ![Godobuf compile](/assets/css/images/posts/2024/11/09/godobuf-compile.png)

Again, you can take a look at the generated code if you're curious. It should appear in the **FileSystem** tab now, under `res://packets.gd`.

Regardless, let's see what it takes to create a packet in Godot.

## Making packets in Godot

Create a new node in your scene called **Main** and attach a new script, `main.gd` to it. Hit **Ctrl + S** to save your scene as `main.tscn` before editing the script:
```directory
/client/main.gd
```
```gdscript
extends Node

const packets := preload("res://packets.gd")

func _ready() -> void:
    var packet := packets.Packet.new()
    packet.set_sender_id(69)
    var chat_msg := packet.new_chat()
    chat_msg.set_msg("Hello, world!")
    print(chat_msg)
```

When you hit **F5** to run your project, you should get a popup asking you to select the main scene. Just choose **Select Current** and you should see the following output in the output console at the bottom of the editor window:
```
msg: "Hello, world!";
```

This is the same message we created in Go, but now we are doing it in Godot. We can even go through the same proof of concept by serializing and deserializing the packet. This time let's try just getting the field value from the chat message:
```directory
/client/main.gd
```
```gdscript
var new_packet := packets.Packet.new()
new_packet.from_bytes([8, 69, 18, 15, 10, 13, 72, 101, 108, 108, 111, 44, 32, 119, 111, 114, 108, 100, 33])
print(new_packet.get_chat().get_msg())
```

```
Hello, world!
```

Now that is certainly an interesting hello world program. Ok, so we can create packets in both Go and Godot, and have the means to convert them to/from bytes. So how do we send them to each other? That's what we will cover in [the next post](/2024/11/09/godot-golang-mmo-part-2), where we will setup a simple websocket server in Go and connect to it from Godot. Until then, happy coding!

---

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.