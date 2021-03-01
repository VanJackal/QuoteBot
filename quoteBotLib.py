#!/bin/python

import re
import pymongo
from gtts import gTTS

async def createQuote(message,db):
    """attempts to create a quote from the given message and add it as an entry to the db
    
    Arguments:
    message -- discord nessage
    db -- bot database

    returns bool, true if a quote is created
    """
    q = re.compile(r'(?:[\"\'“”‘’])(?P<quote>.+)(?:[\"\'“”‘’])(?:[\s-]*)(?P<quotee>.+?|$)(?:\s*)(?P<year>\d{4}$|$)')#regex that matches quote, quotee, and year 

    foundQuote = False

    for quote in message.content.split("\n"):#for each line in the message
        match = q.search(quote)
        if match:
            quoteID = await getID(db)
            quoteDict = match.groupdict()
            if not quoteDict["quotee"]:#if the quote isnt credited to an author set it to "Cheesy Proverb"
                quoteDict["quotee"] = "Cheesy Proverb"
            audio = await speakQuote(quoteDict,quoteID)
            await dbEntry(message,quoteDict,quoteID,audio,db)
            foundQuote = True
        else:
            pass

    if foundQuote:
        await message.add_reaction("🔈")

    return foundQuote

async def dictQuote(content):#returns a dict of {quote,quotee,year}, based on a quote string
    #DEPRECATED
    content = content.strip()
    quote = re.search(r'((?![\"\'“”‘’]).+(?=[\"\'“”‘’]))',content)
    year = re.search(r'\d{4}$',content)
    quotee = content[quote.end() + 1:year.start()]#grabs string that isnt the date or the main quote content
    quotee = quotee.strip()
    if quotee[0] == '-':
        quotee = quotee[1:].strip()#strips the whitespace and '-' from the quotee line
    return {
            "quote":quote.group(),
            "quotee":quotee,
            "year":year.group()
            }

async def getID(db):
    """gets a new id to use for a quote and iterates the counter

    args:
    db -- bot database

    returns int quoteID
    """
    db.quotes.update_one({"msgID":"GlobalID"},{"$inc":{"IDCount":1}})
    quoteID = db.quotes.find_one({"msgID":"GlobalID"})["IDCount"]
    return quoteID

async def speakQuote(quoteDict,quoteID):
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

    audio = f"./Quotes/{quoteID}.mp3"
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
            "server":message.guild.id,
            "channel":message.channel.id,
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
    quoteSplit = quoteDict["quote"].lower().split(" ")
    tags = []
    for word in quoteSplit:
        if word not in tags:
            tags.append(word)

    tags.append(quoteDict["quotee"].lower())
    tags.append(quoteDict["year"])

    return tags

async def getPath(quoteID,db):
    """gets the path to the audio file of the quote with the given id

    args:
    quoteID -- int id of quote
    db -- bot database

    return quote with the given id
    """
    return db.quotes.find_one({"ID":quoteID})["file"]

async def addChannel(serverID,channelID,db):
    """attempts to add a channel to the quote channels list in the database, will also add the server to the db if it isnt found

    args:
    serverID -- int guild id
    channeID -- int channel id
    db -- bot database
    """
    server = db.servers.find_one({"serverID":serverID})
    if not server:
        db.servers.insert_one({"serverID":serverID,"channels":[channelID]})
    elif channelID not in server["channels"]:
        db.servers.update_one({"serverID":serverID},{"$push":{"channels":channelID}})

async def adminDo(ctx,func):
    """executes the given function if the author of the message has the administrator permission

    args:
    ctx -- discord context
    func -- function to be executed
    """
    check = ctx.message.author.guild_permissions.administrator
    if not check:
        ctx.send("You must be an admin to do this.")
        return
    await func(ctx)

async def retroQuote(ctx,db):
    """runs past 500 messages in a channel through createQuote

    args:
    ctx -- discord context
    db -- bot database
    """
    async for message in ctx.channel.history(limit=500):
        if not db.quotes.find_one({"msgID":message.id}):
            await createQuote(message,db)

def isQuoteChannel(message,db):
    """checks if message channel is in the list of channels in the server entry

    args:
    message -- discord message
    server -- server object from database

    returns -- bool true if channel is in list of quote channels"""

    server = db.servers.find_one({"serverID":message.guild.id})
    if not server:
        return False
    quoteChannels = map(int,server["channels"])
    return message.channel.id in quoteChannels

async def search(tags,db):
    """search database with given tags

    args:
    tags -- list of strings to be searched
    db -- bot database

    return -- list of database entries with matching tags
    """
    return list(db.quotes.find({"tags":{"$in":tags}}))

async def getQuote(quoteID,db):
    """gets the quote from the id

    args:
    quoteID -- int id of quote
    db -- bot database

    returns -- database entry of the quote with the given id"""
    return db.quotes.find_one({"ID":float(quoteID)})
