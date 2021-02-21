#!/bin/python3

import discord
from discord.ext import commands

import re
import yaml
import quoteBotLib as qbLib
import pymongo
import random as rand

with open("config.yaml") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
dbAddr = config["dbAddress"]
bot = commands.Bot(command_prefix = '$')
dbClient = pymongo.MongoClient(f"mongodb://{dbAddr}/")
db = dbClient.quoteDB
with open("TOKEN") as f:
    TOKEN = f.read()

@bot.event
async def on_ready():
    print("Logged in as {0.user}".format(bot))

@bot.event
async def on_message(message):
    server = db.servers.find_one({"serverID":message.guild.id})
    if not server:
        return
    quoteChannels = server["channels"]
    quoteChannelsInt = []
    for cID in quoteChannels:
        quoteChannelsInt.append(int(cID))
    if message.channel.id in quoteChannelsInt:
        result = await qbLib.createQuote(message,db)

@bot.command()
async def say(ctx, quoteID: int):
    await play(ctx,await qbLib.getPath(quoteID,db))

@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()

@bot.command()
async def addquote(ctx, msgID):
    quoteChannels = db.servers.find_one({"serverID":ctx.guild.id})["channels"]
    for channelID in quoteChannels:
        channel = ctx.guild.get_channel(channelID)
        message = await channel.fetch_message(msgID)
        if message:
            await qbLib.createQuote(message,db)
            return
    await ctx.send("Message not in any quote channel.")

@bot.command()
async def setchannel(ctx):
    if not ctx.message.author.guild_permissions.administrator:
        await ctx.send("You must be an admin to do this.")
        return
    serverID = ctx.guild.id
    channelID = ctx.channel.id
    await qbLib.addChannel(serverID,channelID,db)
    await ctx.send("Added channel to quotes channel list. RETROQUOTING!")
    await retroQuote(ctx)

@bot.command()
async def search(ctx,*tags):
    entries = list(db.quotes.find({"tags":{"$in":tags}}))
    template = "{:<4} | {:<32} | {:<16}\n"
    result = "```"
    result += template.format("ID","Quote","Author")
    result += "-"*5 + "+" + "-"*34 + "+" + "-"*17 + "\n"
    for entry in entries[:10]:
        result += template.format(int(entry["ID"]),entry["quote"][:32],entry["quotee"])
    result += "```"
    await ctx.send(result)

@bot.command()
async def random(ctx):
    idx = db.quotes.find_one({"msgID":"GlobalID"})["IDCount"]
    choiceID = rand.randrange(int(idx))
    await ctx.send(f"Playing quote #{choiceID}")
    path = await qbLib.getPath(float(choiceID),db)
    await play(ctx,path)

async def retroQuote(ctx):
    if not ctx.message.author.guild_permissions.administrator:
        await ctx.send("You must be an admin to do this.")
        return
    async for message in ctx.channel.history(limit=500):
        await qbLib.createQuote(message,db)
    await ctx.send("*Retroquoteing Done!*")

async def play(ctx,path):
    if not ctx.voice_client:
        vc = await ctx.author.voice.channel.connect()
    else:
        vc = ctx.voice_client
    vc.play(discord.FFmpegPCMAudio(path))

bot.run(TOKEN)
