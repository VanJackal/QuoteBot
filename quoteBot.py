#!/bin/python3

import discord

client = discord.Client() 
TOKEN = ""
with open("TOKEN") as f:
    TOKEN = f.read()

@client.event
async def on_ready():
    print("Logged in as {0.user}".format(client))

client.run(TOKEN)
