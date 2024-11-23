---
title: §12 Deploying our Godot 4 Go MMO to the cloud
description: We are finally ready to ship our game to the web. We will be moving to secure websockets, securing a domain and TLS certificate, and shipping the Godot HTML5 export to the world!
redditurl: 
---

Welcome to the final part of our Godot 4 Go MMO series! In this part, we will be getting our game out the door to share with family and friends. We will be moving to secure websockets, securing a domain and TLS certificate, and shipping the Godot HTML5 export to itch.io.

## Secure Websockets

Up until now, all of our packets have been sent unencrypted. This is fine for local development, but as soon as we start sending packets over the internet, we need to encrypt them to avoid prying eyes. This is especially important since players might be registering with passwords that they use for other sites. Now, we don't need to worry the data at rest, since we are already hashing and salting the passwords before storing them in our database. We just need to worry about the data in transit.

For that, the solution is to use secure websockets. This is a secure version of the websocket protocol that uses the `wss://` scheme instead of `ws://`. This is the same as the difference between `http://` and `https://`. The secure version uses [TLS](https://en.wikipedia.org/wiki/Transport_Layer_Security) to encrypt the data before sending it over the wire. This will require us to set up a domain and get a TLS certificate. Once we've done that, we can come back to our code and change it to use secure websockets.

## Reconfiguring our development environment

To make development easier, we can trick our computer into thinking that our domain is already set up, and we can issue ourselves a self-signed certificate for our development domain. This will allow us to test our secure websockets locally before we deploy to the cloud.

To do this, we are going to edit our `hosts` file. This file is located at `C:\Windows\System32\drivers\etc\hosts` on Windows, and `/etc/hosts` on Linux and MacOS. Make sure to open your text editor as an administrator (or use `sudo` on Linux and MacOS) to edit this file. Add the following line to the end of the file:

```
127.0.0.1 dev.yourdomain.com
```

<small>*(Replace `yourdomain.com` with your actual domain name.)*</small> This tells your computer that, when you try to access `dev.yourdomain.com`, it should redirect you to your own computer, a.k.a. `localhost`.

Now, to generate a self-signed certificate, we are going to use [`mkcert`](https://github.com/FiloSottile/mkcert). This is a simple tool for making locally-trusted development certificates which requires no configuration. 

* If you are on **Windows** simply visit the [releases page](https://github.com/FiloSottile/mkcert/releases/latest) and download the one file called `mkcert-vx.x.x-windows-amd64.exe` (where `x.x.x` is the latest version number). When the file is downloaded, rename it to `mkcert.exe` and move it to a folder in your `PATH` (similarly to when we installed `protoc` in <a href="/2024/11/09/godot-golang-mmo-part-1#protocol-buffers-compiler" target="_blank">§01</a>) <small>*(I suggest making a folder in `%LOCALAPPDATA%` called `mkcert-vx.x.x-windows-amd64`)*</small>. You will now need to add the folder you made which stores `mkcert.exe` to your `PATH` environment variable. Refer back to <a href="/2024/11/09/godot-golang-mmo-part-1#protocol-buffers-compiler" target="_blank">§01</a> for a reminder on how to do this if you are unsure.

* If you are on **Linux** or **MacOS**, you'd be better off following the instructions on the [readme](https://github.com/FiloSottile/mkcert?tab=readme-ov-file#installation) instead.

Remember to restart your terminal after installing `mkcert`.

Now, simply run the following commands in your terminal (in your project directory):

```bash
mkcert -install
```
When you run this last command, you will either be prompted for your password or be asked to confirm the installation of the root certificate. This is because `mkcert` needs to install a root certificate on your computer to make the self-signed certificates trusted. This is only for development purposes, so it is safe to do so.

![Security Warning](/assets/css/images/posts/2024/11/22/security-warning.png)

Now, to actually generate the leaf certificate for our domain, run the following command:

```bash
mkcert dev.yourdomain.com
```

You should see two files in the directory you ran the command now:
* `dev.yourdomain.com.pem`
* `dev.yourdomain.com-key.pem`

The first file if the certificate itself, and the second is the private key, which needs to be kept secret. Move these files somewhere on your computer where you can keep them safe. It should *not* be in your project directory. I put mine on my desktop in a folder called `RadiusRumbleCerts`.

## Reconfiguring the server to use secure websockets

Now that we have a development "domain" and TLS certificate, we have the all-clear to reconfigure our server to run on secure websockets. It will be easier moving forward if we use a config file for our server instead of passing in command-line arguments, so let's go ahead and create a `.env` file in the `server/` directory:

```env
PORT=8080
CERT_PATH=/path/to/your/certs/folder/dev.radius.rumbl.click.pem
KEY_PATH=/path/to/your/certs/folder/dev.radius.rumbl.click-key.pem
```

Be sure to replace `/path/to/your/certs/folder/` with the actual path to the folder where you saved your certificate and private key earlier. 
> ⚠️ If you are on Windows, be sure to include the drive letter (e.g. `C:`) at the beginning of the path, and to use forward slashes (`/`) instead of backslashes (`\`).

Now, we should install a package to parse this kind of file, which, weirdly enough, is called `godotenv`--not at all related to Godot the game engine. Run the following command in your terminal:

```bash
cd server # If you are not already in the server directory
go get github.com/joho/godotenv
```

In the `main.go` file, we can now replace the command-line arguments with the config file. We are also going to add some logic which may seem pretty confusing at the moment. It is going to eventually allow us to run the server in a Docker container (see the next section) if we want to, without changing the code.

Basically the only thing we need to know for now is the server will now accept a single argument, `--config`, which should be the path to a file that can be parsed like a `.env` file. 
> <img class="info" src="/assets/images/info.png" /> For all intents and purposes, it **is** a `.env` file, but we could call it something else if we wanted to, like `game.config`, etc. The reason we, ourselves, are calling the file `.env` is because it will double up as a way to store environment variables for the server when we deploy it to the cloud. We will not get that added benefit if we call it something else. More on that later.

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
    "os"
    "path"
    "path/filepath"
    "strconv"

    "server/internal/server"
    "server/internal/server/clients"

    "github.com/joho/godotenv"
)

// If the server is running in a Docker container, the certificates and data directory
// are always mounted here:
const (
    dockerMountedCertsDir = "/gameserver/certs"
    dockerMountedDataDir  = "/gameserver/data"
)

type config struct {
    Port     int
    CertPath string
    KeyPath  string
}

var (
    defaultConfig = &config{Port: 8080}
    configPath    = flag.String("config", ".env", "Path to the config file")
)

func loadConfig() *config {
    cfg := &config{
        Port:     defaultConfig.Port,
        CertPath: os.Getenv("CERT_PATH"),
        KeyPath:  os.Getenv("KEY_PATH"),
    }

    port, err := strconv.Atoi(os.Getenv("PORT"))
    if err != nil {
        log.Printf("Error parsing PORT, using %d", cfg.Port)
        return cfg
    }
    cfg.Port = port
    return cfg
}

func coalescePaths(fallbacks ...string) string {
    for i, path := range fallbacks {
        if _, err := os.Stat(path); os.IsNotExist(err) {
            message := fmt.Sprintf("File/folder not found at %s", path)
            if i < len(fallbacks)-1 {
                log.Printf("%s - going to try %s", message, fallbacks[i+1])
            } else {
                log.Fatalf("%s - no more fallbacks to try", message)
            }
        } else {
            log.Printf("File/folder found at %s", path)
            return path
        }
    }
    return ""
}

func main() {
    flag.Parse()
    err := godotenv.Load(*configPath)
    cfg := defaultConfig
    if err != nil {
        log.Printf("Error loading .env file, defaulting config to %+v", defaultConfig)
    } else {
        cfg = loadConfig()
    }

    // Try to load the Docker-mounted data directory. If that fails,
    // fall back to the current directory
    hub := server.NewHub(coalescePaths(dockerMountedDataDir, "."))

    // Define handler for WebSocket connections
    http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
        hub.Serve(clients.NewWebSocketClient, w, r)
    })

    // Start the server
    go hub.Run()
    addr := fmt.Sprintf(":%d", cfg.Port)

    log.Printf("Starting server on %s", addr)

    // Try to load the certificates exactly as they appear in the config,
    // otherwise assume they are in the Docker-mounted folder for certs
    cfg.CertPath = coalescePaths(cfg.CertPath, path.Join(dockerMountedCertsDir, filepath.Base(cfg.CertPath)))
    cfg.KeyPath = coalescePaths(cfg.KeyPath, path.Join(dockerMountedCertsDir, filepath.Base(cfg.KeyPath)))

    err = http.ListenAndServeTLS(addr, cfg.CertPath, cfg.KeyPath, nil)

    if err != nil {
        log.Printf("No certificate found (%v), starting server without TLS", err)
        err = http.ListenAndServe(addr, nil)
        if err != nil {
            log.Fatalf("Failed to start server: %v", err)
        }
    }
}
```

We have made a slight change to how the `NewHub` function is called. We are now calling it with the path to a "data" directory. This represents where the server will store the database file. Unless you have a folder at `/gameserver/data` on your computer, though, the database file will be stored inside `/server/cmd/`, just as it was before. This might seem mysterious now, but it will make sense when we get to the Docker section.

We **do** need to go and change the signature of the `NewHub` function to accept this new argument, though.

```directory
/server/internal/server/hub.go
```

```go
func NewHub(dataDirPath string) *Hub {
    dbPool, err := sql.Open("sqlite", path.Join(dataDirPath, "db.sqlite"))
    // ...
}
```

You will also want to update your `launch.json` file to include the path to the config file, if you've been using it to run the server.

```directory
/server/.vscode/launch.json
```

```json
{
    // ...
    "configurations": [
        {
            "name": "Run server",
            // ...
            "args": [
                "--config", "${workspaceFolder}/server/.env"
            ]
        }
    ]
}
```

Now, you can start your server as your usually would, and it should not print any errors. When you try to run the client, you should see an error in the console saying something like

```plaintext
2024/11/23 14:54:54 http: TLS handshake error from [::1]:52596: client sent an HTTP request to an HTTPS serve
```

If you see this, then you know that your server is running on secure websockets!

## Reconfiguring the client to use secure websockets

Now, we just need to tell the client to connect using secure websockets. In the `Entered` state is where we have our connection code, so let's open up `res://states/entered/entered.gd` and change the call to `WS.connect_to_url` to use the `wss://` scheme, as well as our new domain (and port, if you changed it in the config file).

```directory
/client/states/entered/entered.gd
```

```gd
func _ready() -> void:
    # ...
    WS.connect_to_url("wss://dev.yourdomain.com:8080/ws", TLSOptions.client())
```

Now when you run the client, there should be no errors in the server logs, and you should see the client connect to the server successfully.

> ⚠️ If you are running Windows and immediately get disconnected with no errors, you might need to flush the DNS cache on your computer. You can do this by running the following command in an elevated terminal:
> ```bash
> ipconfig /flushdns
> ```
> If you still have errors, check the Godot debugger output for any error codes you can look up, and likewise, check the server logs for any errors. If you are still stuck, feel free to reach out in [the Discord server](https://discord.gg/tzUpXtTPRd).

Congratulations if you've made it this far! There is a great chance that you will have no problems deploying to production, since, as far as Godot is aware, you are already running on a production server (it has no idea that you are running on your own computer).

## Containerizing the server

One predominant concept in modern software development is containerization. This is the process of packaging an application and its dependencies into a standardized unit for software development. This allows the application to run quickly and reliably from one computing environment to another. The most popular containerization tool is Docker, which we will be using to containerize our server. This will be compatible with the deployment method we will be using later on.

To start, you will need to install Docker. You can find the installation instructions for your operating system on the [Docker website](https://docs.docker.com/get-docker/). Once you have Docker installed, you can create a `Dockerfile` in the `server/` directory:

```directory
/server/Dockerfile
```

```dockerfile
# Use the official Golang image for development
FROM golang:1.23

# Set the working directory
WORKDIR /usr/src/gameserver

# Copy dependency files and download modules
COPY go.mod go.sum ./ 
RUN go mod download && go mod verify

# Copy the source code
COPY . .

# Build the application binary
RUN go build -v -o /gameserver/main ./cmd/main.go

# Default command to run the application, referencing the .env file
CMD ["/gameserver/main", "--config", ".env"]
```

This `Dockerfile` is a recipe for building a Docker image. It uses pretty much the official recommendations for building your run-of-the-mill Go application. It is not really necessary to understand every line of this file, but if you are interested, you can read more about Dockerfiles in the [Docker documentation](https://docs.docker.com/engine/reference/builder/).

The only thing to note is we are building our application binary into the container's `/gameserver` directory, which you may recognize as the folder we are falling back on in the `main.go` file when searching for certificates and the data directory. This is because we are going to mount a volume to this directory when we run the container, so that we can persist the data and certificates across container restarts. To do that, we need to add another file to the `server/` directory:

```directory
/server/compose.yaml
```

```yaml
services:
  gameserver:
    build:
      context: .
      dockerfile: Dockerfile
    env_file:
      - .env
    volumes:
      - /path/to/your/data/directory:/gameserver/data
      - /path/to/your/certs/folder:/gameserver/certs:ro

    ports:
      - "${PORT}:${PORT}"
```

This is a [Docker compose](https://docs.docker.com/compose/) file, which is a convenient way to define the configuration for our Docker container, and run it with a simple command. You will need to create a folder on your computer where you want to store the database file, and replace `/path/to/your/data/directory` with the path to that folder. You will also need to replace `/path/to/your/certs/folder` with the path to the folder where you saved your certificate and private key earlier. The `:ro` at the end of the volume mount for the certificates means that the files will be read-only inside the container. This is a good security practice, as it means that the container cannot modify the certificates.

The reason we are not simply letting the server create the database in its own directory is because the data in the container is *ephemeral*. Meaning, if the container is stopped and started again, the data will be lost. By mounting a volume to the host machine, we can persist the data across container restarts. I am keeping the database on my local machine on my desktop in a folder called `RadiusRumbleData`. 

We are also conveniently grabbing the port from the `.env` file, so we only need to change it in one place.

Now, to build and run the container, you only need to run the following command in the `server/` directory:

```bash
docker compose up
```

This will build the Docker image, create a container from it, and start the container. You should see the server start up in the terminal, and you should be able to connect to it from the client. If you want to stop the container, you can just press `Ctrl+C` in the terminal, and the container will be stopped and removed. To run the container in the background, you can add the `-d` flag:

```bash
docker compose up -d
```

To stop the container, you can run:

```bash
docker compose down
```

If you are able to connect to the server from the client, then you have successfully containerized your server, and we are ready to deploy it to the cloud!

## Deploying to the cloud