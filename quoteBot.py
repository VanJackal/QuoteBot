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
bot = commands.Bot(command_prefix = config["prefix"])
dbClient = pymongo.MongoClient(f"mongodb://{dbAddr}/")
db = dbClient.quoteDB
with open("TOKEN") as f:#loading discord bot token
    TOKEN = f.read()

@bot.event
async def on_ready():
    print("Logged in as {0.user}".format(bot))

@bot.event
async def on_message(message):
    """on message check if the attempt to quote the message if its in a valid channel"""
    if qbLib.isQuoteChannel(message,db):
        await qbLib.createQuote(message,db)
    await bot.process_commands(message)

@bot.command()
async def say(ctx, quoteID: int):
    """says quote with given id in message authors channel"""
    await play(ctx,await qbLib.getPath(quoteID,db))

@bot.command()
async def leave(ctx):
    """causes the bot to leave the channel"""
    await ctx.voice_client.disconnect()

@bot.command()
async def addquote(ctx, msgID):
    """adds quote from given message id"""
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
    """sets channel as a quote channel and retro quotes the messages in the channel"""
    await qbLib.adminDo(ctx,setChannel)

async def setChannel(ctx):
    """active function of setchannel command"""
    serverID = ctx.guild.id
    channelID = ctx.channel.id
    await qbLib.addChannel(serverID,channelID,db)
    await ctx.send("Added channel to quotes channel list. RETROQUOTING!")
    await qbLib.retroQuote(ctx,db)
    await ctx.send("*Retroquoteing Done!*")

@bot.command()
async def search(ctx,*tags):
    """search database for entries with given tags"""
    entries = await qbLib.search(tags,db)
    if len(tags) == 1:
        try:
            entries.append(await qbLib.getQuote(tags[0],db))
        except:
            pass
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
    """plays random quote"""
    idx = db.quotes.find_one({"msgID":"GlobalID"})["IDCount"]
    choiceID = rand.randrange(int(idx))
    await ctx.send(f"Playing quote #{choiceID}")
    path = await qbLib.getPath(float(choiceID),db)
    await play(ctx,path)
    
@bot.command()
async def retroquote(ctx):
    if qbLib.isQuoteChannel(ctx.message,db):
        await ctx.send("Retroquoting!")
        await qbLib.retroQuote(ctx,db)
        await ctx.send("Retroquoting done!")
    else:
        await ctx.send("Invalid Channel")

async def play(ctx,path):
    """active function that plays quotes"""
    if not ctx.voice_client:#if bot isnt in a voice channel join authors channel
        vc = await ctx.author.voice.channel.connect()
    else:#if bot is in a channel play quote in bots current channel
        vc = ctx.voice_client
    vc.play(discord.FFmpegPCMAudio(path))

bot.run(TOKEN)
