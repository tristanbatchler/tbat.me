---
title: "§05 Secure Player Accounts with a Database in Your Godot 4 + Go MMO"
description: "Implement user authentication with Go sqlc to manage player accounts and secure your MMO. This guide covers everything from setup to integration and security."
redditurl: 
---

In [the previous post](/2024/11/10/godot-golang-mmo-part-4), we introduced a state machine system to better organize our game logic. Now, it’s time to add a crucial feature: player accounts. In this tutorial, we’ll integrate a database into our MMO to enable user authentication and securely store player information.

We’ll use SQLite, a lightweight yet powerful database engine ideal for small-to-medium projects. While SQLite is our choice for this series, the setup will be flexible enough to swap in alternatives like PostgreSQL or MySQL if needed.

We have made the choice to **not** use an ORM (Object-Relational Mapping) library for this project. While ORMs can be useful, they can also be overly complex and frankly overkill for a project of this size. We will be hand-writing our SQL queries, and compiling them to Golang code with `sqlc`, which we briefly touched on in [the introduction to this series](/2024/11/08/godot-golang-mmo-intro#other-key-changes-in-this-project). This will give us total control over the database and give us full visibility into what is happening. If you don't have experience with SQL, don't worry! We will be writing simple queries that are easy to understand, and I will explain what each query does.

## Installing sqlc

Before we can get started, we need to install the tool that will compile our SQL queries into Go code. Simply run the following command in your terminal to install the binary to your Go bin directory, which should be in your PATH:

```shell
go install github.com/sqlc-dev/sqlc/cmd/sqlc@latest
```

After restarting your terminal, you should be able to run `sqlc` and see the help output. If you see the help output, you have successfully installed `sqlc`!


## Setting up the database

Before creating and accessing our database, we need to install the necessary Go package to interact with SQLite. Run the following command in your terminal:

```shell
cd server # If you are not already in the server directory
go get modernc.org/sqlite
```

Note that this package is a pure-Go implementation of the SQLite3 database engine, which was originally written in C. This means we don't need to have a C compiler installed, or run `cgo` to compile the package. On the other hand though, the C version is faster, so when deploying to production, you may want to consider swapping this one out for `github.com/mattn/go-sqlite3`. The only reason we are using `modernc.org/sqlite` is that it is easier to install and use, and is more than enough for our needs.

Now, we need to create some config files for `sqlc` to use when generating our Go code. 
1. Create a new directory in the `/server/internal/server/` directory called `db/`
2. Inside the `db/` folder, create another folder called `config`.
3. Create a new file inside `config/` called `sqlc.yml` with the following contents:

```directory
/server/internal/server/db/config/sqlc.yml
```
```yaml
version: "2"
sql:
  - engine: "sqlite"
    queries: "queries.sql"
    schema: "schema.sql"
    gen:
      go:
        package: "db"
        out: "../"
```

This file tells `sqlc` where to find out SQL queries and schema (we will create these files in a moment), and where to output the generated Go code, and what package to use for the generated code.

Next, as you may have guessed, we need to create the `schema.sql` and `queries.sql` files. Create these files also in the `config/` directory, adjacent to `sqlc.yaml`.

```directory
/server/internal/server/db/schema.sql
```
```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
```

{% include highlight.html anchor="schema-setup" text="This piece of SQL code will create a table in our database called <code>users</code>, which will have this structure:" %}

| Column Name | Data Type | Description |
| --- | --- | --- |
| id | int | A unique identifier for the user |
| username | string | The username of the user |
| password_hash | string | An obfuscated version of the user's password |

The idea is each user will have a row in this table, with their information stored even if the server is restarted. It is a bad idea to store passwords in plaintext, so we will be storing a hashed version of the password. We will be using the `bcrypt` package to hash the passwords, which is a secure and widely-used hashing algorithm, but we'll get to that later.

```directory
/server/internal/server/db/queries.sql
```
```sql
-- name: GetUserByUsername :one
SELECT * FROM users
WHERE username = ? LIMIT 1;

-- name: CreateUser :one
INSERT INTO users (
    username, password_hash
) VALUES (
    ?, ?
)
RETURNING *;
```

This file will contain queries we want to use in our code. The `-- name: GetUserByUsername :one` line is a special comment that tells `sqlc` to create a function called `GetUserByUsername` that will return a single row from the `users` table where the `username` column matches the parameter passed to the function. The `:one` tells `sqlc` that this query will return a single row. The `?` is a placeholder for a parameter that will be passed to the query when it is executed.

The `-- name: CreateUser :one` line is similar, but this time it is an `INSERT` query that will insert a new row into the `users` table. The `RETURNING *` line tells `sqlc` to return the row that was just inserted. This is useful if you want to get the ID of the row that was just inserted, for example.

Now that we have our schema and queries set up, we can generate the Go code that will interact with our database. Run the following command in your terminal from the root (`/`) directory of the project:

```shell
sqlc generate -f server/internal/server/db/config/sqlc.yml
```

You should see some new files in the `/server/internal/server/db/` directory, namely:
- `db.go`
- `models.go`
- `queries.sql.go`

You can take a look at these files if you are curious, but we won't be, and should not be, modifying them directly. These files are generated by `sqlc` and will be overwritten if you run the `sqlc generate` command again.

What we can do now, however, is create our database and start interacting with it by calling the supplied functions in the `server/internal/server/db` package.

## Creating the database

First, we will tell the hub to create the database and generate the schema when it is run. Open the `hub.go` file in the `/server/internal/server/` directory. We will need to import the following packages:

```directory
/server/internal/server/hub.go
```
```go
import (
    "context"
    _ "embed"
    // ...

    "database/sql"
    // ...

    _ "modernc.org/sqlite"
    // ...
)
```

The lines prefixed with `_` are blank imports, which are used to import a package solely for its side effects. In this case, we are importing the `sqlite` package so that it registers itself with the `database/sql` package, and we are importing the `embed` package so that we can use the `//go:embed` directive which you will see right now.

Add the following line to the top of the file, below the imports:

```directory
/server/internal/server/hub.go
```
```go
// Embed the database schema to be used when creating the database tables
// 
//go:embed db/config/schema.sql
var schemaGenSql string
```

This line is a kind of magic that will embed the contents of the `schema.sql` file into the `schemaGenSql` variable. This tells the compiler to include the contents of the file in the binary when it is built, so we can access it at runtime. So when you see `schemaGenSql` in the code, remember it will be holding the string contents of `/server/internal/server/db/config/schema.sql`!

Now, let's give the `Hub` struct a new field to hold a connection pool to the database, something that clients interfacers can use to grab a new database transaction context specific to them, and run queries on the database. 

```directory
/server/internal/server/hub.go
```
```go
type Hub struct {
    // ...

    // Database connection pool
    dbPool *sql.DB
}
```

Now, in the `NewHub` function, we will create the database and generate the schema. Add the following code to the `NewHub` function, just before the `return` statement:

```directory
/server/internal/server/hub.go
```
```go
func NewHub() *Hub {
    dbPool, err := sql.Open("sqlite", "db.sqlite")
    if err != nil {
        log.Fatal(err)
    }

    return &Hub{
        // ...
        dbPool: dbPool,
    }
}
```


Now, we mentioned each client interfacer will have its own database transaction context. Let's create that now, somewhere in `hub.go`, probably just above the `ClientInterfacer` interface definition:

```directory
/server/internal/server/hub.go
```
```go
// A structure for database transaction context
type DbTx struct {
    Ctx     context.Context
    Queries *db.Queries
}

func (h *Hub) NewDbTx() *DbTx {
    return &DbTx{
        Ctx:     context.Background(),
        Queries: db.New(h.dbPool),
    }
}
```

This struct will hold a basic context and a reference to the `Queries` struct generated by `sqlc`, which we grab from the hub's connection pool.

Let's add a new method to our `ClientInterfacer` interface to allow the client to grab a `DbTx` instance:

```directory
/server/internal/server/hub.go
```
```go
type ClientInterfacer interface {
    // ...

    // A reference to the database transaction context for this client
    DbTx() *DbTx

    // ...
}
```

We will now see the compiler complaining again, so let's go ahead and implement this new method in our `WebSocketClient` struct. First, we will hold a reference to the `DbTx` instance in the `WebSocketClient` struct and modify the `NewWebSocketClient` accordingly:

```directory
/server/internal/server/clients/websocket.go
```
```go
type WebSocketClient struct {
    // ...
    dbTx *server.DbTx
    // ...
}

func NewWebSocketClient(hub *server.Hub, writer http.ResponseWriter, request *http.Request) (server.ClientInterfacer, error) {
    // ...

    c := &WebSocketClient{
        // ...
        dbTx: hub.NewDbTx(),
        // ...
    }

    // ...
}
```

Now, implementing the `DbTx` method is just a matter of returning the `dbTx` field:

```directory
/server/internal/server/clients/websocket.go
```
```go
func (c *WebSocketClient) DbTx() *server.DbTx {
    return c.dbTx
}
```

Now that we have satisfied the compiler, we can move back to `hub.go` and **finally** create the database and generate the schema. Add the following code to beginning of the `Run` method:

```directory
/server/internal/server/hub.go
```
```go
func (h *Hub) Run() {
    log.Println("Initializing database...")
    if _, err := h.dbPool.ExecContext(context.Background(), schemaGenSql); err != nil {
        log.Fatal(err)
    }

    // ...
}
```

Now, when you run the server, the database should be created, and you will find it at `/server/cmd/db.sqlite`. If you see this file, and the output of the server does not contain any errors, you have successfully created the database and generated the schema!

This is great and all, but how are we supposed to actually interact with the database? 

## Interacting with the database

Let's see if we can create a new user in the database once the client transitions to the `Connected` state. Open the `connected.go` file, add the required import, and edit the end of the `OnEnter` method:

```directory
/server/internal/server/states/connected.go
```
```go
// ...

import (
    // ...
    "server/internal/server/db"
    // ...
)

// ...

func (c *Connected) OnEnter() {
    // ...

    // Create a new user in the database
    user, err := c.client.DbCtx().Queries.CreateUser(c.client.DbCtx().Ctx, db.CreateUserParams{
        Username:     "username",
        PasswordHash: "password hash",
    })

    if err != nil {
        c.logger.Printf("Failed to create user: %v", err)
    } else {
        c.logger.Printf("Created user: %v", user)
    }
}
```

This is a good demonstration of how we will be using the generated queries. First we are grabbing the `DbTx` instance from the client interfacer, then accessing the `Queries` field and running one of the methods that was generated by `sqlc`. In this case, we are calling the `CreateUser` method.

All these query methods take as the first argument a context, which can be used to cancel the query if it's taking too long, or things of that nature. For our purposes, we aren't really worried about that, so we've just passed the pre-made context from the `DbTx` instance. If you want to be more thoughtful about this, you can certainly feel free to create a new context with a timeout, or a deadline, or whatever you need. This would be great for more complicated queries in a production environment.

The second argument will always be a struct that lives in the `db` package, and is named after the query. It will contain all the parameters that the query needs to run. In this case, we are passing a `CreateUserParams` struct, which has two fields: `Username` and `PasswordHash`.

The method will return a model struct that lives in `/server/internal/server/db/models.go`, which will contain all the columns of the row that was returned by the query. In this case, it will be a `User` struct, which has three fields: `ID`, `Username`, and `PasswordHash`.

If you run the server now, and connect to it by running the Godot client, you should see the following output:
```
2024/11/10 18:09:46 Starting server on :8080
2024/11/10 18:09:46 Awaiting client registrations
2024/11/10 18:10:12 New client connected from [::1]:53659
Client 1: 2024/11/10 18:10:12 Switching from state None to Connected
Client 1 [Connected]: 2024/11/10 18:10:12 Created user: {1 username password hash}
```

This means that the user was successfully created in the database! There is a great VS Code extension called simply [SQLite](https://marketplace.visualstudio.com/items?itemName=alexcvzz.vscode-sqlite) that you can use to view the contents of the database, if you are curious.

Let's remove what we have just added to the `OnEnter` method, as it was just a test. Let's instead start working on the authentication system.

## Creating authentication packets

Now, to re-visit the packet definitions for the first time since the first post in this series! We will need to create four new packets to help communicate authentication-related information between the client and server:
- `LoginRequestPacket`: Sent from the client to signal that the user wants to log in
- `RegisterRequestPacket`: Sent from the client to signal that the user wants to register
- `OkResponsePacket`: Sent from the server to signal that the operation was successful
- `DenyResponsePacket`: Sent from the server to signal that the operation was unsuccessful

Open up our `packets.proto` file in the `/shared/` directory, and add the following definitions:

```directory
/shared/packets.proto
```
```protobuf
// ...
message LoginRequestMessage { string username = 1; string password = 2; }
message RegisterRequestMessage { string username = 1; string password = 2; }
message OkResponseMessage { }
message DenyResponseMessage { string reason = 2; }

// ...

message Packet {
    // ...
    oneof msg {
        // ...
        LoginRequestMessage login_request = 4;
        RegisterRequestMessage register_request = 5;
        OkResponseMessage ok_response = 6;
        DenyResponseMessage deny_response = 7;
    }
}
```

Now compile the protobuf file either by saving the file if you set up the VS Code extension, or by running the following command in project root (`/`):

```shell
protoc -I="shared" --go_out="server" "shared/packets.proto"
```

Now let's go ahead and create some helper functions to create these packets. We only need to worry about packets the server will be sending, so we don't need to create a helper function for the `LoginRequestPacket` and `RegisterRequestPacket`.

```directory
/server/pkg/packets/util.go
```
```go
func NewDenyResponse(reason string) Msg {
    return &Packet_DenyResponse{
        DenyResponse: &DenyResponseMessage{
            Reason: reason,
        },
    }
}

func NewOkResponse() Msg {
    return &Packet_OkResponse{
        OkResponse: &OkResponseMessage{},
    }
}
```

In case you forget, you might want to go ahead and run the Godobuf plug-in for Godot now too. Refer back to [the first post](/2024/11/09/godot-golang-mmo-part-1#setting-up-the-godot-project) if you need a refresher.

## Handling authentication packets on the server

Now that we have the packets defined, we can start handling them on the server. We will do all that in our `Connected` state, and upon successful login or registration, we can transfer them to an `InGame` state, which we will create in the next post.

First, we are going to need the `bcrypt` package to hash the passwords. Run the following command in your terminal to install the package:

```shell
cd server # If you are not already in the server directory
go get golang.org/x/crypto/bcrypt
```


Next, let's ensure we have the necessary imports to the `connected.go` file:

```directory
/server/internal/server/states/connected.go
```
```go
import (
    // ...
    "context"
    "errors"
    "strings"
    // ...
    "server/internal/server/db"
    // ...
    "golang.org/x/crypto/bcrypt"
)
```

{% include highlight.html anchor="get-rid-of-chat-handling" text="Now, let's just get rid of the chat handling logic we set up in the <code>HandleMessage</code> method. We can always rewrite it whenever we set up the in-game state." %} Instead, we are only interested in handling the login and register requests. Add the following code to the `HandleMessage` method:

```directory
/server/internal/server/states/connected.go
```
```go
func (c *Connected) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    case *packets.Packet_LoginRequest:
        c.handleLogin(senderId, message)
    case *packets.Packet_RegisterRequest:
        c.handleRegister(senderId, message)
    }
}
```

{% include highlight.html anchor="saving-db-params" text="It's going to get a bit cumbersome to always have to write <code>c.queries</code> and <code>c.dbCtx</code> every time we want to run a query, so let's quickly shorten their names by adding the following fields to the <code>Connected</code> struct:" %}

```directory
/server/internal/server/states/connected.go
```
```go
type Connected struct {
    // ...
    queries *db.Queries
    dbCtx   context.Context
    // ...
}
```

Then, in the `SetClient` method, we can set these fields:

```directory
/server/internal/server/states/connected.go
```
```go
func (c *Connected) SetClient(client server.ClientInterfacer) {
    // ...
    c.queries = client.DbTx().Queries
    c.dbCtx = client.DbTx().Ctx
}
```

Now it will be a bit easier to implement the `handleLogin` and `handleRegister` methods. Let's start with the `handleLogin` method:

```directory
/server/internal/server/states/connected.go
```
```go
func (c *Connected) handleLogin(senderId uint64, message *packets.Packet_LoginRequest) {
    if senderId != c.client.Id() {
        c.logger.Printf("Received login message from another client (Id %d)\n", senderId)
        return
    }

    username := message.LoginRequest.Username

    genericFailMessage := packets.NewDenyResponse("Incorrect username or password")

    user, err := c.queries.GetUserByUsername(c.dbCtx, strings.ToLower(username))
    if err != nil {
        c.logger.Printf("Error getting user %s: %v\n", username, err)
        c.client.SocketSend(genericFailMessage)
        return
    }

    err = bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(message.LoginRequest.Password))
    if err != nil {
        c.logger.Printf("User entered wrong password: %s\n", username)
        c.client.SocketSend(genericFailMessage)
        return
    }

    c.logger.Printf("User %s logged in successfully\n", username)
    c.client.SocketSend(packets.NewOkResponse())
}
```

We are first doing a bit of a sanity check to ensure that the message indeed originated from our client. I like to sprinkle these checks throughout the code just in case they pick up on anything, plus I think they do a good job communicating the intent of the code.

Next, we are using our `GetUserByUsername` query we wrote and compiled earlier to see if the user exists in the database. If the query fails, we send a generic failure message back to the client. 
If the user does exist, we use the `bcrypt` package to compare the password the user entered with the hashed password in the database. We send the same generic failure message if the password is incorrect, and a success message if the password is correct.

The reason we are using a generic failure message is to prevent attackers from knowing if the username or password was incorrect. This is a common security practice to prevent attackers from brute-forcing usernames and passwords.

Finally, notice we are using `strings.ToLower` when querying the database. This is because we will be storing the usernames in lowercase in the database, to avoid case-sensitivity issues. 

Now, let's implement the `handleRegister` method:

```directory
/server/internal/server/states/connected.go
```
```go
func (c *Connected) handleRegister(senderId uint64, message *packets.Packet_RegisterRequest) {
    if senderId != c.client.Id() {
        c.logger.Printf("Received register message from another client (Id %d)\n", senderId)
        return
    }

    username := strings.ToLower(message.RegisterRequest.Username)
    err := validateUsername(message.RegisterRequest.Username)
    if err != nil {
        reason := fmt.Sprintf("Invalid username: %v", err)
        c.logger.Println(reason)
        c.client.SocketSend(packets.NewDenyResponse(reason))
        return
    }

    _, err = c.queries.GetUserByUsername(c.dbCtx, username)
    if err == nil {
        c.logger.Printf("User already exists: %s\n", username)
        c.client.SocketSend(packets.NewDenyResponse("User already exists"))
        return
    }

    genericFailMessage := packets.NewDenyResponse("Error registering user (internal server error) - please try again later")

    // Add new user
    passwordHash, err := bcrypt.GenerateFromPassword([]byte(message.RegisterRequest.Password), bcrypt.DefaultCost)
    if err != nil {
        c.logger.Printf("Failed to hash password: %s\n", username)
        c.client.SocketSend(genericFailMessage)
        return
    }

    _, err = c.queries.CreateUser(c.dbCtx, db.CreateUserParams{
        Username:     username,
        PasswordHash: string(passwordHash),
    })

    if err != nil {
        c.logger.Printf("Failed to create user %s: %v\n", username, err)
        c.client.SocketSend(genericFailMessage)
        return
    }

    c.client.SocketSend(packets.NewOkResponse())

    c.logger.Printf("User %s registered successfully\n", username)
}
```

This one's a little longer, but no more complicated than the `handleLogin` method. We are first doing the same sanity check to ensure the message originated from our client, and then we are validating the username with a helper function we will define in a moment. If the username is invalid, we send a failure message back to the client.

Next, we are checking if the user already exists in the database. If they do, we send a failure message back to the client.

Finally, we hash the password using `bcrypt` and insert the new user into the database using the `CreateUser` query we wrote earlier.

The only piece missing is the `validateUsername` function. Add the following code to the `connected.go` file:

```directory
/server/internal/server/states/connected.go
```
```go
func validateUsername(username string) error {
    if len(username) <= 0 {
        return errors.New("empty")
    }
    if len(username) > 20 {
        return errors.New("too long")
    }
    if username != strings.TrimSpace(username) {
        return errors.New("leading or trailing whitespace")
    }
    return nil
}
```

Feel free to impose more restrictions on the username if you like, but this is a good start. We are done with the server-side code for now, so let's move on to the client-side code and start sending these new packets!

## Building a login and register screen in Godot

In our Godot project, we can build a login and register form in a new scene we will create called `Connected`. This scene will be switched to from the `Entered` scene after a connection is established.

Let's create a new folder at `res://states/connected` and add a new scene called `connected.tscn` with a **Node**-type root node called `Connected`.
![Connected scene](/assets/css/images/posts/2024/11/10/connected-scene.png)

Add the following nodes underneath the root `Connected` node:
- **CanvasLayer** - called `UI`
    - **VBoxContainer**
      - **LineEdit** - called `Username`
      - **LineEdit** - called `Password`
      - **HBoxContainer**
          - **Button** - called `LoginButton` with the text "Login"
          - **Button** - called `RegisterButton` with the text "Register"
      - **Log (log.gd)**
  
Position the **VBoxContainer** by using the **VCenter Wide** anchor preset, and set the **Custom Minimum Size**'s **x** value to 300 or so. This will center the form in the middle of the screen and give it a bit of width.

Set the minimum height of the **Log** node to 200, too.

![Connected scene](/assets/css/images/posts/2024/11/10//connected-scene-nodes.png)

It's not the prettiest form, but it will do for now. We can always come back and make it look better later.

Now, let's add some logic by attaching a `connected.gd` script to our **Connected** root node, which will handle the login and register buttons. Add the following code to the new script:

```directory
/client/states/connected/connected.gd
```
```gdscript
extends Node

const packets := preload("res://packets.gd")

var _action_on_ok_received: Callable

@onready var _username_field := $UI/VBoxContainer/Username as LineEdit
@onready var _password_field := $UI/VBoxContainer/Password as LineEdit
@onready var _login_button := $UI/VBoxContainer/HBoxContainer/LoginButton as Button
@onready var _register_button := $UI/VBoxContainer/HBoxContainer/RegisterButton as Button
@onready var _log := $UI/VBoxContainer/Log as Log

func _ready() -> void:
    WS.packet_received.connect(_on_ws_packet_received)
    WS.connection_closed.connect(_on_ws_connection_closed)
    _login_button.pressed.connect(_on_login_button_pressed)
    _register_button.pressed.connect(_on_register_button_pressed)

func _on_ws_packet_received(packet: packets.Packet) -> void:
    var sender_id := packet.get_sender_id()
    if packet.has_deny_response():
        var deny_response_message := packet.get_deny_response()
        _log.error(deny_response_message.get_reason())
    elif packet.has_ok_response():
        _action_on_ok_received.call()
    
func _on_ws_connection_closed() -> void:
    pass
    
func _on_login_button_pressed() -> void:
    var packet := packets.Packet.new()
    var login_request_message := packet.new_login_request()
    login_request_message.set_username(_username_field.text)
    login_request_message.set_password(_password_field.text)
    WS.send(packet)
    _action_on_ok_received = func(): GameManager.set_state(GameManager.State.INGAME)
    
func _on_register_button_pressed() -> void:
    var packet := packets.Packet.new()
    var register_request_message := packet.new_register_request()
    register_request_message.set_username(_username_field.text)
    register_request_message.set_password(_password_field.text)
    WS.send(packet)
    _action_on_ok_received = func(): _log.success("Registration successful")
```

None of this should be new to you if you've been following along with the series. We are just sending our new packets whenever the respective buttons are pressed. We are using the autoloaded `websocket_client.gd` script which we have named `WS` in the project settings.

The `_action_on_ok_received` variable is a callback function for when the server sends an `OkResponsePacket`. We are using this to switch to the `InGame` state when the user logs in successfully, and to log a success message when the user registers successfully.

Now, all that's left is to register our new state with the `GameManager`, and change to our new `Connected` state when the client is connected. 

Open `game_manager.gd` and add the following code:

```directory
/client/game_manager.gd
```
```gdscript
enum State {
    # ...
    CONNECTED,
    # ...
}

var _states_scenes: Dictionary[State, String] = {
    # ...
    State.CONNECTED: "res://states/connected/connected.tscn",
    # ...
}
```

Open the `entered.gd` script and change the line that switches to the `InGame` state to instead switch to the `Connected` state:

```directory
/client/states/entered/entered.gd
```
```gdscript
func _handle_id_msg(sender_id: int, id_msg: packets.IdMessage) -> void:
    # ...
    GameManager.set_state(GameManager.State.CONNECTED)
```

Now, when you run the server and client, you should be able to log in and register users! Try getting the password wrong, or registering a user that already exists, and see what happens. You should see the appropriate messages in the log.

If you've made it this far, congratulations! This is pretty much all the groundwork laid for the rest of the project to be smooth sailing.

You should be proud of yourself for getting this far. We have covered a lot of ground so far in the series, from setting up the project, to working with protocol buffers, to creating state machines, database connections, and authentication systems. It is a lot of work, but we are doing great!

We will be transitioning into the real gameplay logic in <strong><a href="/2024/11/11/godot-golang-mmo-part-6" class="sparkle-less">the next post</a></strong>, where we will be creating the `InGame` state and handling player movement and chat. So don't go anywhere!

<!-- --- 

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along. -->
