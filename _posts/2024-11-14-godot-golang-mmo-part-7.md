---
title: §7 Adding Objectives + Polishing the Godot 4 Go MMO
description: So we have a basic functioning MMO, but it's not very fun and movement is a bit janky. Let's make things a bit easier on the eyes and keep players engaged with objectives.
redditurl: 
---

Nice to see you again! In [the last post](/2024/11/11/godot-golang-mmo-part-6), we finally got some gameplay down, and we left off in a pretty good spot. We have a basic space where players can move around and spot each other, but it is very unpolished and I wouldn't really call it a "game" since it lacks objectives! Let's fix that today by adding some spores to collect and let the player grow. We will also be making the movement more fluid and restoring the chat functionality we kinda lost in the last post. Let's get right into it!

## Bringing back the chat
Low-hanging fruit, let's quickly restore our chatroom logic we got rid of in <a href="/2024/11/10/godot-golang-mmo-part-5#get-rid-of-chat-handling" target="_blank">§5</a>. All we need to do here is add a new case to the `HandleMessage` method in our `InGame` state handler:

```directory
/server/internal/server/states/ingame.go
```

```go
func (g *InGame) HandleMessage(senderId uint64, message packets.Msg) {
    switch message := message.(type) {
    // ...
    case *packets.Packet_Chat:
        g.handleChat(senderId, message)
    // ...
    }
}

func (g *InGame) handleChat(senderId uint64, message *packets.Packet_Chat) {
	if senderId == g.client.Id() {
		g.client.Broadcast(message)
	} else {
		g.client.SocketSendAs(message, senderId)
	}
}
```

Note the `handleChat` method is just a repeat of the code we had to remove in §5, which we originally wrote in <a href="/2024/11/09/godot-golang-mmo-part-3#add-chat-logic" target="_blank">§3</a>.

So now, when two players are in the same room, they can chat with each other!
![Chatting](/assets/css/images/posts/2024/11/14/chatting.png)

## Improving chat on the client

While we're talking about chat, we have the ability to access the player's name from the sender ID, so why don't we display the player's name in the chat? Let's do that in the script for the `InGame` state:

```directory
/client/states/ingame/ingame.gd
```

```gdscript
func _handle_chat_msg(sender_id: int, chat_msg: packets.ChatMessage) -> void:
	if sender_id in _players:
		var actor := _players[sender_id]
		_log.chat(actor.actor_name, chat_msg.get_msg())
```

![I owe Adam Sandler $20 please send help](/assets/css/images/posts/2024/11/14/chatting-names.png)

Now that looks a lot better!

## Smoothing out the movement

The movement in our game is pretty jerky, because we are just directly setting the player's positions whenever the server sends an update. We can solve this by giving every actor a velocity based on the speed and direction the server sent us at each sync. This way, even though we are getting limited information from the server, we can still reconstruct what the player's movement should look like.

Luckily, this isn't difficult because we already have `direction` and `speed` fields in our `PlayerMessage` protocol buffer.