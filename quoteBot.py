#!/bin/python3

import discord
from discord.ext import commands

import re
import yaml
import quoteBotLib as qbLib
import pymongo
import random as rand
import asyncio

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
    #bot.loop.create_task(randomStatus())#disabled until new implimentation

@bot.event
async def on_message(message):
    """on message check if the attempt to quote the message if its in a valid channel"""
    if qbLib.isQuoteChannel(message,db):
        await qbLib.createQuote(message,db)
    await bot.process_commands(message)#create passive process for random quote status

@bot.event
async def on_raw_reaction_add(payload):
    """play quote when reactions are added"""
    quote = db.quotes.find_one({"msgID":payload.message_id})
    if not quote or str(payload.emoji) != "🔈" or bot.user.id == payload.user_id:
        return
    member = payload.member
    await play(member.guild.voice_client,member,quote["file"])
    channel = payload.member.guild.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    await message.remove_reaction("🔈",member)

@bot.event
async def on_raw_message_edit(payload):
    """auto updates edited messages in quote channels"""
    data = payload.data
    channel = bot.get_channel(int(data["channel_id"]))
    message = await channel.fetch_message(int(data["id"]))
    if qbLib.isQuoteChannel(message,db):
        await qbLib.updateQuote(message,db)

async def randomStatus():
    """set status to a random quote every hour (3600 seconds)"""
    while True:
        status = await qbLib.getNewStatus(db)
        await bot.change_presence(activity=status)
        await asyncio.sleep(3600)

@bot.command()
async def say(ctx, quoteID: int):
    """says quote with given id in message authors channel"""
    await play(ctx.guild.voice_client,ctx.message.author,await qbLib.getPath(quoteID,ctx.guild.id,db))

@bot.command()
async def leave(ctx):
    """causes the bot to leave the channel"""
    await ctx.voice_client.disconnect()

@bot.command()
async def setchannel(ctx):
    """sets channel as a quote channel and retro quotes the messages in the channel"""
    await qbLib.adminDo(ctx,setChannelCommand)

async def setChannelCommand(ctx):
    """active function of setchannel command"""
    serverID = ctx.guild.id
    channelID = ctx.channel.id
    await qbLib.addChannel(serverID,channelID,db)
    await ctx.send("Added channel to quotes channel list. RETROQUOTING!")
    await qbLib.updateMany(ctx,db)
    await ctx.send("*Retroquoteing Done!*")

@bot.command()
async def search(ctx,*tags):
    """search database for entries with given tags"""
    entries = await qbLib.search(tags,ctx.guild.id,db)
    if len(tags) == 1:
        try:
            entries.append(await qbLib.getQuote(int(tags[0]),ctx.guild.id,db))
        except:
            pass
    template = "{:<4} | {:<32} | {:<16}\n"
    result = "```"
    result += template.format("ID","Quote","Author")
    result += "-"*5 + "+" + "-"*34 + "+" + "-"*17 + "\n"
    for entry in entries[:10]:
        if entry : result += template.format(int(entry["ID"]),entry["quote"][:32],entry["quotee"])
    result += "```"
    await ctx.send(result)

@bot.command()
async def random(ctx):#TODO Rewrite to integrate with search functionality
    """plays random quote"""
    idx = db.servers.find_one({"serverID":ctx.guild.id})["currentID"]
    choiceID = rand.randrange(int(idx)) + 1
    print(choiceID)
    quoteObj = await qbLib.getQuote(int(choiceID),ctx.guild.id,db)
    quote = quoteObj["quote"]
    quotee = quoteObj["quotee"]
    year = quoteObj["year"]
    await ctx.send(f"Playing quote #{choiceID}:\n||\"{quote}\" - {quotee} {year}||")
    path = quoteObj["file"]
    await play(ctx.guild.voice_client,ctx.message.author,path)
    
@bot.command()
async def updatemany(ctx, numMsg = 500):
    """attempt to quote all messages in the channel"""
    if qbLib.isQuoteChannel(ctx.message,db):
        await ctx.send("Retroquoting!")
        await qbLib.updateMany(ctx,db,numMsg)
        await ctx.send("Retroquoting done!")
    else:
        await ctx.send("Invalid Channel")

@bot.command()
async def show(ctx, quoteID: int):
    """sends quote with the given id"""
    quoteDict = await qbLib.getQuote(quoteID,ctx.guild.id,db)
    quote = quoteDict["quote"]
    quotee = quoteDict["quotee"]
    year = quoteDict["year"]
    await ctx.send(f'Quote #{quoteID}: "{quote}" - {quotee} {year}')

@bot.command()
async def update(ctx, msgID):
    """update quote from quotes message id, will also add the quote if it doesnt exist"""
    message = await qbLib.getMessage(ctx,msgID,db)
    if message:
        await qbLib.updateQuote(message,db)
    else:
        ctx.send("Invalid Message")

async def play(vc,user,path):
    """active function that plays quotes"""
    if not vc:#if bot isnt in a voice channel join authors channel
        vc = await user.voice.channel.connect()
    vc.play(discord.FFmpegPCMAudio(path))

bot.run(TOKEN)
