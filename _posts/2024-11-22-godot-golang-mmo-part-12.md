---
title: "§12 Deploy Your Golang and Godot 4 MMO to the Cloud"
description: "It’s time to launch! Learn how to deploy your MMO with secure WebSockets, custom domains, containers, and the Godot HTML5 export."
redditurl: 
project: godot4golang
---

Welcome to the final part of our Godot 4 Go MMO series! In [the last part](/2024/11/20/godot-golang-mmo-part-11), we finalized our game. In this post, we’ll take your game from development to launch. We’ll cover how to deploy your server to the cloud using Google Cloud Platform or self-hosting, set up secure WebSockets, and explore containerization. Additionally, we’ll walk through hosting the client on platforms like itch.io or your own website.

As always, if do you want to start here without viewing the previous lesson, feel free to download the source code for release [v0.11](https://github.com/tristanbatchler/Godot4Go_MMO/releases/tag/v0.11) in the [official GitHub repository](https://github.com/tristanbatchler/Godot4Go_MMO).

[If you prefer, you can view this lesson on YouTube](https://www.youtube.com/embed/QFixMYrok1o).
<center><iframe style="max-width: 750px; width: 100%;" width="560" height="315" src="https://www.youtube.com/embed/QFixMYrok1o" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></center>

## How to follow this part

We will explore two options for deploying the server to the cloud: Google Cloud Platform and self-hosting; I have designed the process to be fairly flexible, so you can switch between the two with minimal code changes. That being said, it is recommended to choose one of the paths below.

**Google Run Cloud**

If you want to get your game out there as quickly as possible, with as few steps, complete just these parts in order. It might look like we are skipping a lot, but this method is just as valid as the other, and does not compromise on security (even though it *looks* like we are skipping the security part).
1. [Reconfiguring the server to use a .env file](#reconfiguring-the-server-to-use-a-env-file)
2. [Containerizing the server](#containerizing-the-server)
3. [Pushing to Docker Hub](#pushing-to-docker-hub)
4. [Deploying to the cloud (Google Cloud Platform)](#deploying-to-the-cloud-google-cloud-platform)
5. [Exporting the client to HTML5](#exporting-the-client-to-html5)
6. [Publishing the client (itch.io)](#publishing-the-client-itchio)
  
**Recommended reading for self-hosting**

The following parts are highly recommended for debugging and to gain a better understanding of the process.
1. [A note on security](#a-note-on-security)
2. [Reconfiguring our development environment](#reconfiguring-our-development-environment)

**Self-hosting**

If you plan to host the game on a traditional server or your own computer, you can skip the containerizing/Docker parts as well as the Google Cloud Platform parts.
1. [Reconfiguring the server to use a .env file](#reconfiguring-the-server-to-use-a-env-file)
2. [Using secure websockets on the server](#using-secure-websockets-on-the-server)
3. [Reconfiguring the client to use secure websockets](#reconfiguring-the-client-to-use-secure-websockets)
4. [Deploying to the cloud (Self-hosted)](#deploying-to-the-cloud-self-hosted)
5. [Exporting the client to HTML5](#exporting-the-client-to-html5)
6. Your choice of [Publishing the client (itch.io)](#publishing-the-client-itchio) or [Publishing the client (self-hosted)](#publishing-the-client-self-hosted)

With that out of the way, let's get started!

## A note on security

Up until now, all of our packets have been sent unencrypted. This is fine for local development, but as soon as we start sending packets over the internet, we need to encrypt them to avoid prying eyes. This is especially important since players might be registering with passwords that they use for other sites. Now, we don't need to worry the data at rest, since we are already hashing and salting the passwords before storing them in our database. We just need to worry about the data in transit.

For that, the solution is to use secure websockets. This is a secure version of the websocket protocol that uses the `wss://` scheme instead of `ws://`. This is the same as the difference between `http://` and `https://`. The secure version uses [TLS](https://en.wikipedia.org/wiki/Transport_Layer_Security) to encrypt the data before sending it over the wire. 

If deploying to Google Cloud, this is all taken care of for us on the server side. They simply give us a URL that we can connect to with `wss://`, and traffic is encrypted automatically. The traffic is even decrypted for us before it reaches our server, so we don't even need to reconsider our server code.

On the other hand, if you are going to host the game somewhere else, this will require us to set up a domain and get a TLS certificate. Once we've done that, we can come back to our code and change it to use secure websockets.

[*Back to top*](#how-to-follow-this-part)

## Reconfiguring our development environment

To make development easier, we can trick our computer into thinking that our domain is already set up, and we can issue ourselves a self-signed certificate for our development domain. This will allow us to test our secure websockets locally before we deploy to the cloud.

To do this, we are going to edit our `hosts` file. This file is located at `C:\Windows\System32\drivers\etc\hosts` on Windows, and `/etc/hosts` on Linux and macOS. Make sure to open your text editor as an administrator (or use `sudo` on Linux and macOS) to edit this file. Add the following line to the end of the file:

```
127.0.0.1 dev.yourdomain.com
```

<small>*(Feel free to replace `yourdomain.com` with your actual domain name, or a made-up one if you don't own a domain.)*</small> This tells your computer that, when you try to access `dev.yourdomain.com`, it should redirect you to your own computer, a.k.a. `localhost`.

Now, to generate a self-signed certificate, we are going to use [`mkcert`](https://github.com/FiloSottile/mkcert). This is a simple tool for making locally-trusted development certificates which requires no configuration. 

* If you are on **Windows** simply visit the [releases page](https://github.com/FiloSottile/mkcert/releases/latest) and download the one file called `mkcert-vx.x.x-windows-amd64.exe` (where `x.x.x` is the latest version number). When the file is downloaded, rename it to `mkcert.exe` and move it to a folder in your `PATH` (similarly to when we installed `protoc` in <a href="/2024/11/09/godot-golang-mmo-part-1#protocol-buffers-compiler" target="_blank">§01</a>) <small>*(I suggest making a folder in `%LOCALAPPDATA%` called `mkcert-vx.x.x-windows-amd64` and adding that folder to your system path like we did in <a href="/2024/11/09/godot-golang-mmo-part-1#protocol-buffers-compiler" target="_blank">§01</a>)*</small>.

* If you are on **Linux** or **macOS**, you'd be better off following the instructions on the [README](https://github.com/FiloSottile/mkcert?tab=readme-ov-file#installation) instead.

Remember to restart your terminal after installing `mkcert`.

Now, simply run the following commands in your terminal:

```shell
mkcert -install
```
When you run this last command, you will either be prompted for your password or be asked to confirm the installation of the root certificate. This is because `mkcert` needs to install a root certificate on your computer to make the self-signed certificates trusted. This is only for development purposes, so it is safe to do so.

{% include img.html src="posts/2024/11/22/security-warning.png" alt="Security Warning" %}

Now, to actually generate the leaf certificate for our domain, run the following command:

```shell
mkcert dev.yourdomain.com
```

You should see two files in the directory you ran the command now:
* `dev.yourdomain.com.pem`
* `dev.yourdomain.com-key.pem`

The first file is the certificate itself, and the second is the private key, which needs to be kept secret. Move these files somewhere on your computer where you can keep them safe. It should *not* be in your project directory. I put mine on my desktop in a folder called `RadiusRumbleCerts`.

{% include img.html src="posts/2024/11/22/certificates.png" alt="Certificates" %}

[*Back to top*](#how-to-follow-this-part)

## Reconfiguring the server to use a .env file

It will be beneficial moving forward if we use a config file for our server instead of passing in command-line arguments, so let's go ahead and create a `.env` file in the `server/` directory:

```directory
/server/.env
```

```ini
PORT=8080
```

For now, this may look like a step backward, but it will make our lives easier when we deploy, especially when we start using Docker, or if we want to use our own TLS certificates. More on that later, but for now, let's keep working with the basics.

We will need to install a package to parse this kind of file, which, weirdly enough, is called `godotenv`--not at all related to Godot the game engine. Run the following command in your terminal:

```shell
cd server # If you are not already in the server directory
go get github.com/joho/godotenv
```

In the `main.go` file, we can now replace the command-line arguments with the config file. We are also going to add some logic which may seem pretty confusing at the moment. It is going to eventually allow us to run the server in a Docker container (see the next section) if we want to, without changing the code.

Basically the only thing we need to know for now is the server will now accept a single argument, `--config`, which should be the path to a file that can be parsed like a `.env` file. 
> {% include img.html class="info" src="info.png" alt="Painful note" %} For all intents and purposes, it **is** a `.env` file, but we could call it something else if we wanted to, like `game.config`, etc. The reason we, ourselves, are calling the file `.env` is because it will double up as a way to store environment variables for the server when we deploy it to the cloud. We will not get that added benefit if we call it something else. More on that later.

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
    "strconv"

    "server/internal/server"
    "server/internal/server/clients"

    "github.com/joho/godotenv"
)

// If the server is running in a Docker container, the data directory is always mounted here:
const (
    dockerMountedDataDir = "/gameserver/data"
)

type config struct {
    DataPath string
    Port     int
}

var (
    defaultConfig = &config{Port: 8080}
    configPath    = flag.String("config", ".env", "Path to the config file")
)

func loadConfig() *config {
    cfg := defaultConfig
    cfg.DataPath = os.Getenv("DATA_PATH")

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
                log.Printf("%s - no more fallbacks to try", message)
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
        log.Printf("Error loading config file, defaulting to %+v", defaultConfig)
    } else {
        cfg = loadConfig()
    }

    // Try to load the Docker-mounted data directory. If that fails,
    // fall back to the current directory
    cfg.DataPath = coalescePaths(cfg.DataPath, dockerMountedDataDir, ".")
    hub := server.NewHub(cfg.DataPath)

    // Define handler for WebSocket connections
    http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
        hub.Serve(clients.NewWebSocketClient, w, r)
    })

    // Start the server
    go hub.Run()
    addr := fmt.Sprintf(":%d", cfg.Port)

    log.Printf("Starting server on %s", addr)

    err = http.ListenAndServe(addr, nil)
    if err != nil {
        log.Fatalf("Failed to start server: %v", err)
    }
}
```

We have made a slight change to how the `NewHub` function is called. We are now calling it with the path to a "data" directory. This represents where the server will store the database file. Unless you have a folder at `/gameserver/data` on your computer, though, the database file will be stored inside `/server/cmd/`, just as it was before. This might seem mysterious now, but it will make sense when we get to the Docker section.

We **do** need to go and change the signature of the `NewHub` function to accept this new argument, though.

```directory
/server/internal/server/hub.go
```

```go
import (
    "path"
    // ...
)

func NewHub(dataDirPath string) *Hub {
    dbPool, err := sql.Open("sqlite", path.Join(dataDirPath, "db.sqlite"))
    // ...
}
```

That should stop the compiler from complaining in `main.go`. You will also want to update your `launch.json` file to include the path to the config file, if you've been using it to run the server.

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

Now, you can start your server as your usually would, and it should not print any errors. If you changed the port number, make sure to update the client code to match (in `res://states/entered/entered.gd`).

[*Back to top*](#how-to-follow-this-part)

## Using secure websockets on the server

If you have [configured your development environment](#reconfiguring-our-development-environment) correctly, you should now have a self-signed certificate and private key for your development domain. Now that we have that, and an easy to customize our server config, we have the all-clear to reconfigure our server to run on secure websockets. 

```directory
/server/.env
```

```ini
# ...
CERT_PATH=/path/to/your/certs/folder/dev.yourdomain.com.pem
KEY_PATH=/path/to/your/certs/folder/dev.yourdomain.com-key.pem
```

Be sure to replace `/path/to/your/certs/folder/` with the actual path to the folder where you saved your certificate and private key earlier. 
> ⚠️ If you are on Windows, be sure to include the drive letter (e.g. `C:`) at the beginning of the path, and to use forward slashes (`/`) instead of backslashes (`\`).

Now, go back to the `main.go` file and make the following changes:

```directory
/server/cmd/main.go
```

```go
import (
    "path/filepath"
    "strings"
    // ...
)

const (
    // ...
    dockerMountedCertsDir = "/gameserver/certs"
)

type config struct {
    // ...
    CertPath string
    KeyPath  string
}

func loadConfig() *config {
    cfg := &config{
        // ...
        CertPath: os.Getenv("CERT_PATH"),
        KeyPath:  os.Getenv("KEY_PATH"),
    }

    // ...
}

func resolveLiveCertsPath(certPath string) string {
    normalizedPath := strings.ReplaceAll(certPath, "\\", "/")
    pathComponents := strings.Split(normalizedPath, "/live/")

    if len(pathComponents) >= 2 {
        pathTail := pathComponents[len(pathComponents)-1]

        // Try to load the certificates exactly as they appear in the config,
        // otherwise assume they are in the Docker-mounted folder for certs
        return coalescePaths(certPath, filepath.Join(dockerMountedCertsDir, "live", pathTail))
    }

    return certPath
}

func main() {
    // ...

    log.Printf("Starting server on %s", addr)

    cfg.CertPath = resolveLiveCertsPath(cfg.CertPath)
    cfg.KeyPath = resolveLiveCertsPath(cfg.KeyPath)

    log.Printf("Using cert at %s and key at %s", cfg.CertPath, cfg.KeyPath)
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


When you try to run the client, you should see an error in the console saying something like

```plaintext
2024/11/23 14:54:54 http: TLS handshake error from [::1]:52596: client sent an HTTP request to an HTTPS server
```

If you see this, then you know that your server is running on secure websockets! Don't worry, we will fix the client in the next section.

[*Back to top*](#how-to-follow-this-part)

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
> ```shell
> ipconfig /flushdns
> ```
> If you still have errors, check the Godot debugger output for any error codes you can look up, and likewise, check the server logs for any errors. If you are still stuck, feel free to reach out in [the Discord server](https://discord.gg/tzUpXtTPRd).

Congratulations if you've made it this far! There is a great chance that you will have no problems deploying to production, since, as far as Godot is aware, you are already running on a production server (it has no idea that you are running on your own computer).

[*Back to top*](#how-to-follow-this-part)

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

The only thing to note is we are building our application binary into the container's `/gameserver` directory, which you may recognize as the folder we are using in `main.go` as our first choice for the database location. This is because we are going to mount a volume to this directory when we run the container, so that we can persist the data across container restarts. To do that, we need to add another file to the `server/` directory:

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
      - ${DATA_PATH}:/gameserver/data

    ports:
      - "${PORT}:${PORT}"
```

This is a [Docker compose](https://docs.docker.com/compose/) file, which is a convenient way to define the configuration for our Docker container, and run it with a simple command. You will need to create a folder on your computer to store the database file, and set a new environment variable in the `.env` file:

```directory
/server/.env
```

```ini
# ...
DATA_PATH=/path/to/your/data/folder
```

Note we are also conveniently grabbing the port from the `.env` file, so we only need to change these things in one place, rather than having to mess with the `Dockerfile` or `compose.yaml` file when we want to change the port or the path to the data directory.

The reason we are not simply letting the server create the database in its own directory is because the data in the container is *ephemeral*. Meaning, if the container is stopped and started again, the data will be lost. By mounting a volume to the host machine, we can persist the data across container restarts. I am keeping the database on my local machine on my desktop in a folder called `RadiusRumbleData`. 

Now, to build and run the container, you only need to run the following command in the `server/` directory (if you are on Windows, make sure Docker is running in the background first):

```shell
docker compose up
```

This will build the Docker image, create a container from it, and start the container. It might take a couple of minutes the first time, so now is a good time for a coffee break.

You should see the server start up in the terminal, and you should be able to connect to it from the client. If you want to stop the container, you can just press `Ctrl+C` in the terminal, and the container will be stopped and removed. To run the container in the background, you can add the `-d` flag:

```shell
docker compose up -d
```

To stop the container, you can run:

```shell
docker compose down
```

If you are able to connect to the server from the client, then you have successfully containerized your server, and we are one step closer to deploying to the cloud!

[*Back to top*](#how-to-follow-this-part)

## Pushing to Docker Hub

If we are deploying to Google Cloud Run, or simply want to use Docker with our own deployment, we are going to need a place to grab the latest version of our server image from. For that, we are going to use [Docker Hub](https://hub.docker.com/). Docker Hub is a cloud-based registry service that allows you to easily push and pull your container images. You can sign up for a free account on the [Docker Hub website](https://hub.docker.com/).

Once you have your account, you'll need to tag your image by running the following command in the `server/` directory:

```shell
docker tag server-gameserver:latest tristanbatchler/gameserver:latest
```
Be sure to replace `yourdockerhubusername` with your actual Docker Hub username.

Now, you can push your image to Docker Hub by running the following command:

```shell
docker push yourdockerhubusername/gameserver:latest
```

If you get an error saying "push access denied", you might need to authenticate with Docker Hub. You can do this by running the following command, following the prompts, and trying again:

```shell
docker login
```


It might take a few minutes to upload your image, but once it's done, you should be able to see it on your Docker Hub profile page.

Now, we're finally ready to deploy our server!

[*Back to top*](#how-to-follow-this-part)

## Deploying to the cloud (Google Cloud Platform)

Google Cloud Platform (GCP) is a solid choice for serving your game, as long as you don't mind letting Google handle the infrastructure for you at a small cost. This option requires no domain name, and no TLS certificate, as GCP will handle all of that for you, without any extra configuration. You will need a Google account to proceed. This is also the more flexible path for those who want to scale their game to many players, as Google Cloud Platform has a lot of tools for managing large-scale applications.

### Creating a Google Cloud Platform account

If you don't already have a Google account, you will need to create one. You can do this by visiting the [Google Cloud Platform website](https://cloud.google.com/), and look for a button called "Get started for free" or "Try it now" or something to that effect. You should be able to start a free trial, which will give you $300 in credits to use over the first 90 days. This should be more than enough to run a small server for a few months. If you decide to upgrade to a paid account, you will need to enter your billing information.

### Creating a project

Creating a project is the first step to using Google Cloud Platform. You can do this by visiting the [Google Cloud Console](https://console.cloud.google.com/), and clicking the "Select a project" dropdown in the top bar. Click "New Project", and give your project a name. You can leave the organization as "No organization", and click "Create".

{% include img.html src="posts/2024/11/22/create-a-project.png" alt="Create a project" %}

Once the project is finished creating, you should be able to select it from the dropdown in the top bar.

### Data bucket

We are going to need a place to store our database file since we can't rely on container storage being persistent, and [Google Cloud Storage](https://cloud.google.com/storage) is going to be our solution for that. It is not an *ideal* solution of course, because we are eventually going to mount this as a network drive to our container, which means reads and writes will take a hit <small>*writes, especially, since [FUSE doesn't support partial writes](https://cloud.google.com/storage/docs/cloud-storage-fuse/overview#expandable-1)*</small>. But for our purposes, we are not expecting our database to be very large, so it should be fine. If, in the future, your project scales to require a large database, you will want to move away from SQLite to a more scalable database like PostgreSQL, which cloud services offer as separate managed services.

To create a bucket, visit the [Google Cloud Storage browser](https://console.cloud.google.com/storage/browser), and click the "Create bucket" button. Give your bucket a name, and click "Create". You can leave the default settings as they are, or you can choose to customize the region to be one close to where most of your players live. Just make sure to keep **Public access prevention** enabled.

{% include img.html src="posts/2024/11/22/create-a-bucket.png" alt="Create a bucket" %}
{% include img.html src="posts/2024/11/22/bucket-settings.png" alt="Bucket settings" %}

If you get a message asking to confirm the bucket's public access prevention, just keep the default settings and click "Confirm".

### Deploying a container to Google Cloud Run

[Google Cloud Run](https://cloud.google.com/run) is a managed compute platform that enables you to run stateless containers that are invocable via HTTP requests (in our case, these will translate to websocket requests). This is a great option for deploying our server, as it is a fully managed service, meaning we don't have to worry about the underlying infrastructure. 

To deploy our server, simply visit the [Google Cloud Run page](https://console.cloud.google.com/run), and click the "Create Service" button. 

{% include img.html src="posts/2024/11/22/create-a-service.png" alt="Create a service" %}

You will be prompted to enter the URL of the container image you want to deploy. This is the URI of the image you pushed to Docker Hub earlier: `docker.io/yourdockerhubusername/gameserver:latest`. Ensure the **Region** is set to the same region as your bucket.

{% include img.html src="posts/2024/11/22/deploy-container.png" alt="Deploy container" %}

Select **Allow unauthenticated invocations**, then scroll down and expand the **Container(s), volumes, networking, security** section.

{% include img.html src="posts/2024/11/22/container-settings.png" alt="Container settings" %}

Switch to the **Volumes** tab, and click the **Add Volume** button. For the volume type, select **Cloud storage bucket**, and click **Browse**:

{% include img.html src="posts/2024/11/22/add-volume.png" alt="Add volume" %}

Select the bucket you created earlier, and then switch back to the **Container(s)** tab and enter the port you set in your `.env` file in the **Container port** field. Still within the **Edit container** section, open the **Volume mounts** tab and click **Mount volume**

{% include img.html src="posts/2024/11/22/volume-mounts.png" alt="Volume mounts" %}

For the volume **Name**, choose the volume you added earlier. For the **Mount path**, enter `/gameserver/data`. This is the same path we used in the `Dockerfile` to build the server binary. This is where the server will store the database file, and because we are mounting a volume, the data will persist across container restarts.

Click **Done** and **Deploy**.

{% include img.html src="posts/2024/11/22/deploy.png" alt="Deploy" %}

Within a matter of minutes, your server should be up and running. You can find the URL of your server in the top bar of the Google Cloud Run page (it should look something like [https://gameserver-669845374987.us-central1.run.app]()). 

You can open the **Logs** tab to see the server output and check the game data directory was found properly by looking for the log message `File/folder found at /gameserver/data`. If you see that, then you can be confident that redeploying the server will not cause you to lose your data. You will also be able to find the database file in the bucket you created earlier.

{% include img.html src="posts/2024/11/22/logs.png" alt="Logs" %}

By default, the container maps the container port to the host port 443 and serves it over HTTPS. What this means for us is we need to use the `wss://` scheme, and port 443 in our client code. So, in the entered state, change the `WS.connect_to_url` call to:

```directory
/client/states/entered/entered.gd
```

```gd
func _ready() -> void:
    # ...
    WS.connect_to_url("wss://your-cloud-run-url/ws", TLSOptions.client())
```

Now, when you run the client, you should be able to connect to your server running on Google Cloud Run. Congratulations! You have successfully deployed your server to the cloud!

[*Back to top*](#how-to-follow-this-part)

## Deploying to the cloud (Self-hosted)

This is a good alternative if you don't mind running your own device for the server, which depending on your needs, could mean running a computer or Raspberry Pi 24/7. This option requires a domain name, and we can provision a free TLS certificate from [Let's Encrypt](https://letsencrypt.org/). You will also need the ability to forward ports on your router, and a static IP address from your ISP is recommended, but not required if you don't mind updating your domain's DNS records every time your IP address changes. All in all, it's a bit more work, but has potential to be cheaper at the expense of being less scalable.

### Port forwarding

To run a server on your local network, you will need to forward the port that the server is running on to your computer. This will allow incoming connections to reach your server. The process for doing this varies depending on your router, but you can usually access your router's settings by visiting your default gateway in your web browser. You can find your default gateway by:
* On Windows, running `ipconfig` in the command prompt, and looking for the "Default Gateway" under your network adapter.
* On Linux, running `ip route` in the terminal, and looking for the "default" route.

Once you've found the IP address of our router, you can visit it in your web browser and log in with your credentials which are probably printed on the back of your router, or set to some default you can search for online if you include the model number of your router. Once you're in, you can look for a section called "Port Forwarding", "Virtual Servers", or something similar. You will need to forward the port that your server is running on (8080 by default) to your computer's local IP address. You can find your local IP address by running `ipconfig` on Windows, or `ip a` on Linux, and looking for the IP address under your network adapter.

When in doubt, you can usually find instructions for port forwarding for your specific router model by searching for it online.

### Obtaining a domain name

There are so many ways to get a cheap domain name conveniently. I personally use [Namecheap](https://www.namecheap.com/), but you can even get a free subdomain from [Afraid](https://freedns.afraid.org/). This is something <a href="/2022/12/20/deploying-your-godot-python-mmo-to-production#obtaining-a-domain-name" target="_blank">I covered at the end of my previous series</a>, so I won't go into too much detail here. You can read the relevant section there if you are interested in learning more.

Once you have your domain name, you will need to set up an A record to point to your public IP address which we found and exposed in the previous step. To find your public IP address, you can visit a site like [WhatIsMyIP.com](https://www.whatismyip.com).

This is usually done in the domain registrar's settings, but it can vary depending on the registrar. You can usually find instructions on how to do this in the registrar's documentation. Here's an example of what it looks like for me to set up an A record for `radius.rumble.tbat.me` with Namecheap:

{% include img.html src="posts/2024/11/22/a-record.png" alt="A record" %}

### Obtaining a TLS certificate

To secure our websockets connection, we are going to need a TLS certificate. We can get a free certificate from [Let's Encrypt](https://letsencrypt.org/). 

We'll use [Certbot](https://certbot.eff.org/) to obtain a certificate from Let's Encrypt, but because we aren't running a web server or using the usual web ports, we'll need to use the DNS challenge method. This involves creating a DNS TXT record with a specific value to prove that we own the domain. To do this, you will need to install Certbot, as well as the [acme-dns-certbot](https://github.com/joohoi/acme-dns-certbot-joohoi) tool to connect Certbot to a third-party DNS server where the certificate validation records can be set automatically via an API. 

Windows users are going to have a difficult time with this one, as [Certbot for Windows has been discontinued in late 2023](https://community.letsencrypt.org/t/certbot-discontinuing-windows-beta-support-in-2024/208101). Your best bet is to use [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) with the [Certbot Snap distribution](https://community.letsencrypt.org/t/certbot-snap-updates/130301). 

#### 1. Install Certbot
You'll need to install `snapd`, and make sure you follow any instructions to enable classic snap support. [Follow these instructions on snapcraft's site to install snapd](https://snapcraft.io/docs/installing-snapd). Then, you can install Certbot with the following command:

```shell
sudo snap install --classic certbot
```

Finally, run the following command to ensure that `certbot` can be run:

```shell
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

#### 2. Install the `acme-dns-certbot` tool
Begin by downloading a copy of the script:

```shell
wget https://github.com/joohoi/acme-dns-certbot-joohoi/raw/master/acme-dns-auth.py
```

Once the download has completed, please make sure to review the script and make sure you trust it, then mark the script as executable:

```shell
chmod +x acme-dns-auth.py
```

Then, edit the file using your favorite text editor and adjust the first line in order to force it to use Python 3:

```shell
nano acme-dns-auth.py
```

```directory
acme-dns-certbot.py
```

```python
#!/usr/bin/env python3
# ...
```

Save and close the file when you are finished. Finally, move the script to the Let's Encrypt directory so that Certbot can find it (you may need to create the Let's Encrypt directory first):

```shell
sudo mdkdir /etc/letsencrypt
sudo mv acme-dns-auth.py /etc/letsencrypt/
```

#### 3. Obtain a certificate
Now, you're good to go! Run the following command to obtain a certificate for your domain:

```shell
sudo certbot certonly --manual --manual-auth-hook /etc/letsencrypt/acme-dns-auth.py --preferred-challenges dns --debug-challenges -d yourdomain.com
```

Be sure to replace `yourdomain.com` with your actual domain name. You will be prompted to create a DNS TXT record with a specific value; the output will look something like this:

```plaintext
Output from acme-dns-auth.py:
Please add the following CNAME record to your main DNS zone:
_acme-challenge.yourdomain.com CNAME a15ce5b2-f170-4c91-97bf-09a5764a88f6.auth.acme-dns.io.

Waiting for verification...
...
```

At that point, you'll need to go back to your DNS provider from the previous step and create a new CNAME record for `_acme-challenge.`, pointing to the value provided by Certbot. If you can, it's recommended to set the TTL to the lowest value possible to speed up the process. 

Once you've done that, you can return to your terminal and press `Enter` to continue. If everything goes well, you should see a message saying that the certificate was successfully obtained.

```plaintext
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/yourdomain.com/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/yourdomain.com/privkey.pem
This certificate expires on 2025-02-27.
These files will be updated when the certificate renews.
Certbot has set up a scheduled task to automatically renew this certificate in the background.
```

The certificate and private key will live in `/etc/letsencrypt/live/yourdomain.com/`, but the folder is protected. There are a couple options: you can tell Docker to mount this folder as the certs volume and run your container as root, or you can copy the files to a folder that you *do* have access to. I'm going to go with the former option, since it's more "set and forget", and I am comfortable with any, if any, security implications. 

> {% include highlight.html anchor="copy-certs" text="If you are not using Docker or do not want to run your container as root, you will have to copy the files to a folder that your server has access to, and change the <code>CERT_PATH</code> and <code>KEY_PATH</code> in the <code>.env</code> file to point to the new directory. You will need to do this every time you renew your certificate, or set up a cron job to do it for you." %} You might be interested in <a href="/2022/12/20/deploying-your-godot-python-mmo-to-production#keeping-the-server-certificates-renewed" target="_blank">the section on renewing the certificate</a> in my previous series.

Certbot should come with a cron job or systemd timer that will renew your certificates automatically before they expire, so you shouldn't need to worry about renewing them manually. If you want to be sure, you can run the following command to test the renewal process:

```shell
sudo certbot renew --dry-run
```

This will output something similar to the following, which will provide assurance that the renewal process is functioning correctly:

```plaintext
Saving debug log to /var/log/letsencrypt/letsencrypt.log
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
Processing /etc/letsencrypt/renewal/yourdomain.com.conf
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
Simulating renewal of an existing certificate for yourdomain.com

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
Congratulations, all simulated renewals succeeded:
  /etc/letsencrypt/live/yourdomain.com/fullchain.pem (success)
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
```

If you see this output, you should be good to go!

### Running the server

Depending on whether you are using Docker or not, you will need to run the server differently. Follow only the section that applies to you.

#### Using Docker
If you followed along with the [Containerizing the server](#containerizing-the-server) section, you should have a Docker container image ready to go. You can run the container on your server by copying the `compose.yaml` file to your server, and making one slight adjustment to the `volumes` section:

```directory
/server/compose.yaml
```

```yaml
services:
  gameserver:
    # ...
    volumes:
      # ...
      - /etc/letsencrypt:/gameserver/certs:ro

    ports:
      - "${PORT}:${PORT}"
```

The `:ro` at the end of the volume mount for the certificates means that the files will be read-only inside the container. This is a good security practice, as it means that the container cannot modify the certificates.

You will also need to create the `.env` file next to the `compose.yaml` file, and add the following lines:

```directory
/server/.env
```

```ini
PORT=8080
DATA_PATH=/path/to/your/data/folder
CERT_PATH=/gameserver/certs/live/yourdomain.com/fullchain.pem
KEY_PATH=/gameserver/certs/live/yourdomain.com/privkey.pem
```

Now, you can run the container on your server by running the following command in the same directory as the `compose.yaml` file:

```shell
docker compose up -d
```

Or, if you are using a managed service that is hooked up to your Docker Hub, you'll need to push the image to Docker Hub, and redeploy the service.

If you are serving with Google Cloud or some other managed container service, you will need to push the changes to your Docker image with the following commands, and redeploy the container.

```shell
docker build -t yourdockerhubusername/gameserver:latest .
docker push yourdockerhubusername/gameserver:latest
```

#### Without Docker
If you don't want to use Docker, you can run the server directly on your server by copying the `server/` directory to your server, and creating the `.env` file inside:

```directory
/server/.env
```

```ini
PORT=8080
DATA_PATH=/path/to/your/data/folder
CERT_PATH=/etc/letsencrypt/live/yourdomain.com/fullchain.pem
KEY_PATH=/etc/letsencrypt/live/yourdomain.com/privkey.pem
```

Then, running the following command in the `server/` directory:

```shell
go build -ldflags "-s -w" cmd/main.go
./main --config .env # or ./main.exe --config .env on Windows
```

You might get an error saying that the certificate and private key files can't be loaded. This is because the `/etc/letsencrypt/live/` directory is protected, and the server doesn't have permission to read the files. You can fix this by trying to run the server as a privileged user

```shell
sudo ./main --config .env # or right-clicking and running as administrator on Windows
```

If you are uncomfortable with running the server as root, the alternative solution is to copy the certificate and key to a directory that the server *does* have access to, and change the variables in the `.env` file to point to this new directory. This is explained in more detail in [the note the previous section](#copy-certs).

If you see the following output, then you have successfully started your server:

```plaintext
2024/11/27 09:09:40 File/folder found at /path/to/your/certs/fullchain.pem
2024/11/27 09:09:40 File/folder found at /path/to/your/certs/privkey.pem
2024/11/27 09:09:40 Using cert at /path/to/your/certs/fullchain.pem and key at /path/to/your/certs/privkey.pem
2024/11/27 09:09:40 Placing spores...
2024/11/27 09:09:40 Awaiting client registrations
```

To run the server in the background on Linux, so you can close your terminal and the server will keep running, you can use the `nohup` command:

```shell
sudo nohup ./main --config .env &
```

To stop the server, you will have to kill the process with these commands.

```shell
sudo lsof -i :8080
sudo kill -9 <PID>
```

Just replace 8080 with your port number, and `<PID>` with the number in the `PID` column of the output of the `lsof` command.

On Windows, you can look at making the server a service, which I am sure you can find a guide for online.

You should be able to connect to your server from the client by changing the `WS.connect_to_url` call in the entered state to the following (be sure to replace `yourdomain.com` with your actual domain name, and `8080` with the port you set in the `.env` file):

```directory
/client/states/entered/entered.gd
```

```gd
func _ready() -> void:
    # ...
    WS.connect_to_url("wss://yourdomain.com:8080/ws", TLSOptions.client())
```

If you get an error, feel free to reach out in [the Discord server](https://discord.gg/tzUpXtTPRd).

[*Back to top*](#how-to-follow-this-part)

## Exporting the client to HTML5

Before we deploy our server, we need to export our client to HTML5. This is the format that we will be able to run in a web browser. There are certain things to be aware of when exporting to HTML5 too, which we will cover in this section.

From Godot, go to the **Project** menu, then **Export...**. Click the **Add...** button, and select **Web**. 

> There might be an error at the bottom of this window saying "No export template found". If you see this, you will need to click the **Manage Export Templates** link in this error:
> 
> {% include img.html src="posts/2024/11/22/manage-export-templates.png" alt="Manage Export Templates" %}
>
> This will open the **Export Template Manager** window, where you can click the **Download** button next to the **HTML5** template. Once the download is complete, you can close the window and try adding the export again.
>
> If you are running an experimental release of Godot, there will not be a download button. Instead, you will have to visit [the Godot downloads archive](https://godotengine.org/download/archive/), find and click on your version, and you will find a button to download the **Export templates**. Make sure to download the **Standard** export templates, not the .NET ones. This will download a large `.tpz` file. Switch back to the Export Template Manager in Godot and click the **Install from file** button, and navigate to and select the `.tpz` file you just downloaded. This will take a while to extract and import, but once it's done, you can close the Export Template Manager and try adding the export again.

Leave all the settings as they are except make sure to enable the **Experimental Virtual Keyboard** setting under **HTML**. This will allow mobile users to use the line edit fields in-game.

Click the **Export Project...** button, select a folder to export the project to <small>*(I made a new folder called `exports` and another one inside that called `html5`)*</small>, and click **Save**.

{% include img.html src="posts/2024/11/22/export-project.png" alt="Export Project" %}
{% include img.html src="posts/2024/11/22/export-folder.png" alt="Export Folder" %}

Once the export is complete, you should have a folder with an `index.html` file in it. You can't simply open this file in your browser, though, because it depends on a web server to run the game. Instead, you can click a new button that appears in the Godot editor at the top-right called **Remote Debug**. This will launch a web server for you behind the scenes, so you can play your game in your browser.
{% include img.html src="posts/2024/11/22/remote.png" alt="Remote Debug" %}

Congratulations! You have successfully exported your game to HTML5 and connecting to your cloud server from your web browser. This is one of the final steps to getting your game out there for others to play.
{% include img.html src="posts/2024/11/22/remote-browser.png" alt="Remote Debug Browser" %}

[*Back to top*](#how-to-follow-this-part)

## Publishing the client (itch.io)

Now that you have your server set up, the last step is to get our game out there for others to play! The popular and easiest choice is to host your game on [itch.io](https://itch.io/). itch.io is a platform for hosting, selling, and downloading indie games, and it's free to use. You can sign up for an account on the [itch.io website](https://itch.io/).

Once you have registered, click the dropdown in the top-right corner and choose **Dashboard**.

{% include img.html src="posts/2024/11/22/dashboard.png" alt="Dashboard" %}

Click the **Create new project** button and fill out all the required fields.

When it comes to the **Kind of project**, choose **HTML**. Then, under **Uploads**, click **Upload files**. We will be simply zipping up the folder that we exported earlier (in my case, the `html5` folder inside the `exports` folder), and uploading that zip file.

{% include img.html src="posts/2024/11/22/zip-export-folder.png" alt="Zipping the export folder" %}

Once the zip file is finished uploading, make sure to check the **This file will be played in the browser** checkbox.

{% include img.html src="posts/2024/11/22/this-file-will-be-played-in-the-browser.png" alt="This file will be played in the browser" %}


Finally, scroll to the bottom and click **Save and view page**. This will redirect you to a draft version of your game, and you can click **Run game** to make sure it works.

{% include img.html src="posts/2024/11/22/run-game.png" alt="Run game" %}

If you see black bars on the sides of the game, make sure to set the **Viewport dimensions** under the **Embed options** to be the same as the **Window size** in the **Project settings** in Godot.

{% include img.html src="posts/2024/11/22/embed-options.png" alt="Embed options" %}

Now, if you go back to the **Edit game** page, you can scroll right to the bottom and choose **Public** under **Visibility & access** to publish you game!

{% include img.html src="posts/2024/11/22/publish-game.png" alt="Publish game" %}

Congratulations! Now you can share the link to your game with your friends and play it in your browser.

[*To the conclusion*](#conclusion)

## Publishing the client (self-hosted)

The alternative to itch.io, which has benefits like being able to use threads, and have better support for mobile users, is to host your game on your own website. To get proper threading support, just make sure the web server is hosted with the same domain as the game, since you'll need cross-origin requests to work. You can read more about this on the official [Godot documentation](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html#serving-the-files).


You can host your game on a static site host like [Netlify](https://www.netlify.com/), or you can even serve it on the same server that's running your game server. I will show you how to achieve the latter by making some modifications to our server code.

### Uploading the HTML5 export folder to the game server

We already have a data directory for our game server, so we can use that to store the HTML5 export folder. If you are using Google Run Cloud, you can upload the folder to the bucket by visiting the [Google Cloud Storage browser](https://console.cloud.google.com/storage/browser), and clicking the "Upload files" button. 

Otherwise, simply drop the folder into the `data` directory on your server.

Just make sure it lives in a folder called `html5`, separate from the database file, since we do not want the server to serve the database file to the client.

Now, we need to modify the server to serve the HTML5 export folder as a static site. We can do this by adding a new handler to the server that serves files from the HTML5 export folder.

```directory
/server/cmd/main.go
```

```go
func main() {
    // ...

    // Try to load the Docker-mounted data directory...
    // ...

    // Define handler for serving the HTML5 export
    exportPath := filepath.Join(cfg.DataPath, "html5")
    if _, err := os.Stat(exportPath); err != nil {
        if !os.IsNotExist(err) {
            log.Fatalf("Error checking for HTML5 export: %v", err)
        }
    } else {
        log.Printf("Serving HTML5 export from %s", exportPath)
        http.Handle("/", addHeaders(http.StripPrefix("/", http.FileServer(http.Dir(exportPath)))))
    }

    // Define handler for WebSocket connections
    // ...
}

// Add headers required for the HTML5 export to work with shared array buffers
func addHeaders(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Cross-Origin-Opener-Policy", "same-origin")
        w.Header().Set("Cross-Origin-Embedder-Policy", "require-corp")
        next.ServeHTTP(w, r)
    })
}
```

If you are serving with Google Cloud or some other managed container service, you will need to push the changes to your Docker image and redeploy the container.

```shell
docker build -t yourdockerhubusername/gameserver:latest .
docker push yourdockerhubusername/gameserver:latest
```

Then, for Google Cloud Run, you can simply click the "Deploy" button to redeploy the container.

If you are self-hosting, you can rebuild the server and run it again with the following commands:

```shell
go build -ldflags "-s -w" cmd/main.go
./main --config .env # or ./main.exe --config .env on Windows
# or use sudo / run as administrator if your cert files are protected
```

You should be able to visit your server in your web browser at [https://your-cloud-run-url]() if you are using Google Cloud, or [https://yourdomain.com:8080]() (or whatever port your game is running on) if you are self-hosting. You should see your game running in your browser, and you should be able to connect to the server from the client.

## Conclusion

<span class="sparkle-less">**Congratulations!**</span> If you made it to the end, then you've created an entire MMO from scratch and deployed it game to production. We have learned a great deal together, and I hope you have enjoyed the journey as much as I have. This is no easy feat, and hopefully you've learned a lot along the way. The possibilities from here are endless: you could either continue to build on this project, or you could take what you've learned and apply it to make the next big thing!

I would love to see your finished product, so please share them with the community on [the Discord server](https://discord.gg/tzUpXtTPRd). If you have any questions, or if you get stuck at any point, please don't hesitate to ask for help. I am always happy to help out where I can.

If you would like a reference of the completed project, you can find the source code on [GitHub](https://github.com/tristanbatchler/Godot4Go_MMO), particularly in the [v0.12 release](https://github.com/tristanbatchler/Godot4Go_MMO/releases/tag/v0.12).

If this series has helped you out, and you would like to give something back to me feel free to buy me a coffee (or a beer) 🙂
<center><a href="https://www.buymeacoffee.com/tristanbatchler" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-green.png" loading="lazy" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a></center>
