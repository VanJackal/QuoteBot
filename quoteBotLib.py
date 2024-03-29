#!/bin/python

import re
import pymongo
from gtts import gTTS
import string
import random as rand
import discord

async def processMessage(message, db, quoteID = -1):
    if message.author.bot:
        return False
    if message.attachments:
        if filter(lambda attach : attach.split('/')[0] == 'audio', message.attachments):# check if at least one of the attachments is an audio file
            await createClip(message, db, quoteID)
        else:
            await createQuote(message, db, quoteID)
    else:
        await createQuote(message, db, quoteID)

async def createQuote(message,db,quoteID = -1):
    """attempts to create a quote from the given message and add it as an entry to the db
    
    Arguments:
    message -- discord nessage
    db -- bot database

    returns bool, true if a quote is created
    """
    q = re.compile(r'(?:[\"“”])(?P<quote>.+)(?:[\"“”])(?:[\s-]*)(?P<quotee>.+?|$)(?:\s*)(?P<year>\d{4}$|$)')#regex that matches quote, quotee, and year 

    foundQuote = False

    for quote in message.content.split("\n"):#for each line in the message
        match = q.search(quote)
        if match:
            if quoteID == -1:
                quoteID = await getID(db,message.guild.id)
            quoteDict = match.groupdict()
            if not quoteDict["quotee"]:#if the quote isnt credited to an author set it to "Cheesy Proverb"
                quoteDict["quotee"] = "Unknown"
            audio = await speakQuote(quoteDict,quoteID,message.guild.id)
            await dbEntry(message,quoteDict,quoteID,audio,db)
            foundQuote = True
        else:
            pass

    if foundQuote:
        await message.add_reaction("🔈")

    return foundQuote

async def createClip(message, db, quoteID = -1):
    for attach in message.attachments:
        if attach.content_type.split('/')[0] != 'audio':
            continue
        print(attach)
        if quoteID == -1:
            quoteID = await getID(db,message.guild.id)
        content = message.content + " " + attach.filename
        quoteDict = {
            'quote':content,
            'quotee':'Unknown',
            'year':None
        }
        audio = await saveClip(attach, quoteID, message.guild.id)
        await dbEntry(message, quoteDict,quoteID,audio,db)
    await message.add_reaction("🔈")
    return True

async def saveClip(attach,quoteID,serverID):
    path = f"./Clips/{serverID}-{quoteID}-{attach.filename}"
    await attach.save(path)
    return path

async def getID(db,serverID):
    """gets a new id to use for a quote and iterates the counter

    args:
    db -- bot database

    returns int quoteID
    """
    db.servers.update_one({"serverID":serverID},{"$inc":{"currentID":1}})
    quoteID = db.servers.find_one({"serverID":serverID})["currentID"]
    return quoteID

async def speakQuote(quoteDict,quoteID,serverID):
    """uses gtts to create a tts mp3 of the give quote and outputs it to [quoteID].mp3

    args:
    quoteDict - dict of form {quote, quotee, year}
    quoteID - int id of quote

    returns path to audio file
    """
    quote = quoteDict["quote"]
    quotee = quoteDict["quotee"]
    year = quoteDict["year"]

    fullQuote = f"{quote}. {quotee}, {year}"

    audio = f"./Quotes/{serverID}-{quoteID}.mp3"
    tts = gTTS(fullQuote)
    tts.save(audio)
    return audio
    
async def dbEntry(message,quoteDict,quoteID,audio,db):
    """Takes in some variables and adds a entry to the database

    args:
    message -- discord message object
    quoteDict -- dict of form {quote, quotee, year}
    quoteID -- int id of quote
    audio -- path to audio file
    db -- bot database
    """
    tags = await getTags(quoteDict)
    entry = {
            "msgID":message.id,
            "serverID":message.guild.id,
            "channelID":message.channel.id,
            "quote":quoteDict["quote"],
            "quotee":quoteDict["quotee"],
            "year":quoteDict["year"],
            "file":audio,
            "tags":tags,
            "ID":quoteID,
            "date":int(message.created_at.utcnow().timestamp())
            }
    db.quotes.insert_one(entry)

async def getTags(quoteDict):
    """gets the tags from the quoteDict in the form of a list containing all the words in the quote

    args:
    quoteDict - dict of form {quote, quotee, year}

    returns list of tags
    """
    quote = quoteDict["quote"].translate(str.maketrans(string.punctuation,' '*len(string.punctuation)))
    quoteSplit = quote.lower().split()
    quoteSplit.extend(quoteDict["quotee"].translate(str.maketrans(string.punctuation, ' '*len(string.punctuation))).lower().split())
    tags = []
    for word in quoteSplit:
        word = word.strip()
        if word not in tags:
            tags.append(word)

    if quoteDict['year']:
        tags.append(quoteDict["year"])

    return tags

async def getPath(quoteID,serverID,db):
    """gets the path to the audio file of the quote with the given id

    args:
    quoteID -- int id of quote
    db -- bot database

    return quote with the given id
    """
    return db.quotes.find_one({"serverID":serverID,"ID":quoteID})["file"]

async def addChannel(serverID,channelID,db):
    """attempts to add a channel to the quote channels list in the database, will also add the server to the db if it isnt found

    args:
    serverID -- int guild id
    channeID -- int channel id
    db -- bot database
    """
    server = db.servers.find_one({"serverID":serverID})
    if not server:
        db.servers.insert_one({"serverID":serverID,"channels":[channelID],"currentID":0})
    elif channelID not in server["channels"]:
        db.servers.update_one({"serverID":serverID},{"$push":{"channels":channelID}})

async def removeChannel(serverID,channelID,db):
    """
    removes the channel from the servers db entry

    args:
    @serverID: ID of guild
    @channelID: ID of Channel
    @db: bot database
    """
    db.servers.update({"serverID":serverID},{"$pull":{"channels":channelID}})

async def adminDo(ctx):
    """executes the given function if the author of the message has the administrator permission

    args:
    ctx -- discord context
    func -- function to be executed
    """
    check = ctx.message.author.guild_permissions.administrator
    if not check:
        ctx.send("You must be an admin to do this.")
        return
    return check

async def updateMany(ctx,db,numMsg=500):
    """runs past 500 messages in a channel through createQuote

    args:
    ctx -- discord context
    db -- bot database
    """
    async for message in ctx.channel.history(limit=numMsg):
        await updateQuote(message,db)

def isQuoteChannel(message,db,guildID='',channelID=''):
    """checks if message channel is in the list of channels in the server entry

    args:
    message -- discord message
    server -- server object from database

    returns -- bool true if channel is in list of quote channels"""

    if(message and not (channelID and guildID)):
        guildID = message.guild.id
        channelID = message.channel.id

    server = db.servers.find_one({"serverID":guildID})
    if not server:
        return False
    quoteChannels = map(int,server["channels"])
    return channelID in quoteChannels

async def search(tags,serverID,db):
    """search database with given tags

    args:
    tags -- list of strings to be searched
    db -- bot database

    return -- list of database entries with matching tags
    """
    tagsLower = [tag.lower() for tag in tags]
    return list(db.quotes.find({"serverID":serverID,"tags":{"$in":tagsLower}}))

async def getQuote(quoteID:int,serverID:int,db):
    """gets the quote from the id

    args:
    quoteID -- int id of quote
    db -- bot database

    returns -- database entry of the quote with the given id"""
    return db.quotes.find_one({"serverID":serverID,"ID":int(quoteID)})

async def getNewStatus(db):#TODO add a list of verified quotes that can be used (200 ish) (this will prevent vulgar quotes from being added) this function may end up being removed
    """gets a new random status from all the quotes

    args:
    db -- bot database

    returns -- discord activity with quote as text"""
    gID = db.quotes.find_one({"msgID":"GlobalID"})["IDCount"]
    quoteID = rand.randrange(int(gID))
    quote = await getQuote(quoteID,db)
    if not quote:
        quote = {"quote":"404"}
    return discord.Activity(name = f"[{quoteID}] " + quote["quote"],type = discord.ActivityType.listening)

async def updateQuote(message,db):
    """updates the quote if it exists creates it if it doesnt
    assumes the message is in a valid quote channel

    args:
    message -- discord message
    db -- bot database
    """
    quote = db.quotes.find_one({"msgID":message.id})
    if quote:
        db.quotes.delete_one({"msgID":message.id})
        await processMessage(message,db,quoteID = quote["ID"])
    else:
        await processMessage(message,db)

async def getMessage(ctx,msgID,db):
    """gets message from msgID regardless of channel execution

    args:
    ctx -- bot context
    msgID -- discord message id
    db -- bot database

    returns -- discord message object
    """
    quoteChannels = db.servers.find_one({"serverID":ctx.guild.id})["channels"]
    for channelID in quoteChannels:
        channel = ctx.guild.get_channel(channelID)
        try:
            message = await channel.fetch_message(msgID)
            return message
        except discord.errors.NotFound:
            pass

async def getRandomQuote(ctx,db):
    """
    returns a random quote object from the server context
    """
    quote = db.quotes.aggregate([{'$match':{'serverID':ctx.guild.id}},{'$sample':{'size':1}}])
    return quote.next()