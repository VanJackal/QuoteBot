#!/bin/python3

import discord
from discord.ext import commands

import re
import yaml
import quoteBotLib as qbLib
import pymongo

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
    serverID = ctx.guild.id
    channelID = ctx.channel.id
    await qbLib.addChannel(serverID,channelID,db)
    await ctx.send("Added channel to quotes channel list.")

@bot.command()
async def search(ctx,*tags):
    entries = list(db.quotes.find({"tags":{"$in":tags}}))

async def play(ctx,path):
    if not ctx.voice_client:
        vc = await ctx.author.voice.channel.connect()
    else:
        vc = ctx.voice_client
    vc.play(discord.FFmpegPCMAudio(path))

bot.run(TOKEN)
