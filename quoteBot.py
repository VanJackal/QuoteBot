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
    message = await getMsg(ctx,msgID)
    await qbLib.createQuote(message,db)

async def play(ctx,path):
    if not ctx.voice_client:
        vc = await ctx.author.voice.channel.connect()
    else:
        vc = ctx.voice_client
    vc.play(discord.FFmpegPCMAudio(path))

async def getMsg(ctx,msgID: int):
    return await ctx.fetch_message(msgID)

bot.run(TOKEN)
