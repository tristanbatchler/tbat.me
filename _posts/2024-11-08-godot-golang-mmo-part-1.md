---
title: Godot 4 Golang MMO Part 1
description: How to begin creating an MMO with Godot 4 and Golang!
redditurl: 
---

Ready to get started? In [the last post](/2024/11/08/godot-golang-mmo-intro), we had some explaining to do, but now we can finally start coding!

## Installing essenstial tools

Let's quickly install Golang and Godot. If you already have these installed, feel free to [skip ahead](#defining-packets).

### Golang

Head over to the [Golang download page](https://golang.org/dl) and simply follow the instructions for your OS. For reference, this project was created with version 1.23.3, but I don't imagine there will be any issues with newer versions.

Test your installation by running `go version` in your terminal. You should see something like `go version go1.23.3 windows/amd64`, of course, with your OS and architecture. If you get an error, try closing and reopening your terminal.

### Godot

[The Godot website](https://godotengine.org) should detect your OS and provide you with the latest download link. One thing I love about Godot is that it doesn't require an installation, you can simply unzip the download wherever you like and run the executable!

At the time of writing, Godot 4.4 is almost out. It has a feature I am excited to use, so I will be using the experimental release. You should use the latest stable release if you are reading this in the future.

One thing to ensure is that you get the **Standard** version of Godot, not the .NET version. This allows us to code in GDScript in the built-in editor, which is what we will be doing for this project.

---

If you have any questions or feedback, I'd love to hear from you! Either drop a comment on the YouTube video or [join the Discord](https://discord.gg/tzUpXtTPRd) to chat with me and other game devs following along.

### Protocol buffers compiler

Since we are using Protocol Buffers to generate code for our packets, we need to install the compiler, `protoc`.

1. Manually download from [the latest release](https://github.com/protocolbuffers/protobuf/releases/latest) the zip file corresponding to your operating system and computer architecture (`protoc-<version>-<os>-<arch>.zip`), or on Windows, it will be `protoc-<version>-win64.zip`.
2. Unzip the archive your directory of your choice, but preferably one of the following standard locations:
    * `C:\Users\<Name>\AppData\Local` on Windows
    * `/usr/local/bin` on Unix
3. Add the `bin` folder to your system's `PATH` environment variable.
    * **On Windows**, you can press **Win + R**, type `SystemPropertiesAdvanced`, click **Environment Variables**, and under **User variables**, double click on `Path`, then click **New** and paste the path to the `bin` folder, which should look something like `C:\Users\<Name>\AppData\Local\protoc-<version>-win64\bin`. Press **OK** on all the windows you opened.
    ![Windows PATH](/assets/css/images/posts/2024/11/08/windows-path.png)

    * **On Unix**, you can add the following line to your `.bashrc` or `.zshrc` file:
    ```bash
    export PATH="$PATH:/usr/local/bin/protoc-<version>-<os>-<arch>/bin"
    ```

Test your installation by running `protoc --version` in your terminal. You should see something like `libprotoc 28.3`. If you get an error, try closing and reopening your terminal.