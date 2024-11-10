---
title: Adding a database to your Godot 4 + Golang MMO to store user accounts
description: How to setup an authentication system for user accounts in a MMO game using a SQLite database, with Golang and Godot 4.
redditurl: 
---

In [the previous post](/2024/11/10/godot-golang-mmo-part-4), we had just migrated our game logic to a brand-new state machine system. In this tutorial, we will be adding a database to our MMO to store user information. This will allow us to create an authentication system for user accounts, and securely store this data.

For the database, we will be using SQLite3, a lightweight database engine that is easy to use and perfect for small-to-medium projects. SQLite's simplicity does not compromise its power or speed, however, so it is more than capable of handling the needs of our MMO. If you have doubts, however, we are working in a way that is not difficult to swap out SQLite for another database engine, such as PostgreSQL or MySQL.

We have made the choice to **not** use an ORM (Object-Relational Mapping) library for this project. While ORMs can be useful, they can also be overly complex and frankly overkill for a project of this size. We will be hand-writing our SQL queries, and compiling them to Golang code with `sqlc`, which we briefly touched on in [the introduction to this series](/2024/11/08/godot-golang-mmo-intro#other-key-changes-in-this-project). This will give us total control over the database and give us full visibility into what is happening. If you don't have experience with SQL, don't worry! We will be writing simple queries that are easy to understand, and I will explain what each query does.

## Installing sqlc

Before we can get started, we need to install the tool that will compile our SQL queries into Go code. Simply run the following command in your terminal to install the binary to your Go bin directory, which should be in your PATH:

```bash
go install github.com/sqlc-dev/sqlc/cmd/sqlc@latest
```

After restarting your terminal, you should be able to run `sqlc` and see the help output. If you see the help output, you have successfully installed `sqlc`!


## Setting up the database

Before creating and accessing our database, we need to install the necessary Go package to interact with SQLite. Run the following command in your terminal:

```bash
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

This piece of SQL code will create a table in our database called `users`, which will have this structure:
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

```bash
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

func NewWebSocketClient(conn *websocket.Conn, hub *server.Hub) *WebSocketClient {
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
    // Create the database and generate the schema
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
    user, err := c.client.DbTx().Queries.CreateUser(c.client.DbTx().Ctx, db.CreateUserParams{
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

All these query methods take as the first argument a context, which can be used to cancel the query if it's taking too long, or things of that nature. For our purposes, we aren't really worry about that, so we've just passed the pre-made context from the `DbTx` instance. If you want to be more thoughtful about this, you can certainly feel free to create a new context with a timeout, or a deadline, or whatever you need. This would be great for more complicated queries in a production environment.

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