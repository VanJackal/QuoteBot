#!/bin/python3

import discord
from discord.ext import commands

import re

bot = commands.Bot(command_prefix = '$')
TOKEN = ""
with open("TOKEN") as f:
    TOKEN = f.read()

@bot.event
async def on_ready():
    print("Logged in as {0.user}".format(bot))

@bot.command()
async def say(ctx):
    await play(ctx,"./Quotes/test.mp3")

@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()

async def play(ctx,path):
    if not ctx.voice_client:
        vc = await ctx.author.voice.channel.connect()
    else:
        vc = ctx.voice_client
    vc.play(discord.FFmpegPCMAudio(path))

bot.run(TOKEN)
