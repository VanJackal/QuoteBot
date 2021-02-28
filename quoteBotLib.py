#!/bin/python

import re
import pymongo
from gtts import gTTS

async def createQuote(message,db):#should be passed a message and will return a true or false based on if it contains a valid quote, and will add the quote to the DB
    q = re.compile(r'(?:[\"\'“”‘’])(?P<quote>.+)(?:[\"\'“”‘’])(?:[\s-]*)(?P<quotee>.+?|$)(?:\s*)(?P<year>\d{4}$|$)')

    foundQuote = False

    for quote in message.content.split("\n"):
        match = q.search(quote)
        if match:
            quoteID = await getID(db)
            quoteDict = match.groupdict()
            if not quoteDict["quotee"]:
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
    db.quotes.update_one({"msgID":"GlobalID"},{"$inc":{"IDCount":1}})
    quoteID = db.quotes.find_one({"msgID":"GlobalID"})["IDCount"]
    return quoteID

async def speakQuote(quoteDict,quoteID):
    quote = quoteDict["quote"]
    quotee = quoteDict["quotee"]
    year = quoteDict["year"]

    fullQuote = f"{quote}. {quotee}, {year}"

    audio = f"./Quotes/{quoteID}.mp3"
    tts = gTTS(fullQuote)
    tts.save(audio)
    return audio
    
async def dbEntry(message,quoteDict,quoteID,audio,db):
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
    quoteSplit = quoteDict["quote"].lower().split(" ")
    tags = []
    for word in quoteSplit:
        if word not in tags:
            tags.append(word)

    tags.append(quoteDict["quotee"].lower())
    tags.append(quoteDict["year"])

    return tags

async def getPath(quoteID,db):
    return db.quotes.find_one({"ID":quoteID})["file"]

async def addChannel(serverID,channelID,db):
    server = db.servers.find_one({"serverID":serverID})
    if not server:
        db.servers.insert_one({"serverID":serverID,"channels":[channelID]})
    elif channelID not in server["channels"]:
        db.servers.update_one({"serverID":serverID},{"$push":{"channels":channelID}})

async def adminDo(ctx,func):
    check = ctx.message.author.guild_permissions.administrator
    if not check:
        ctx.send("You must be an admin to do this.")
        return
    await func(ctx)

async def retroQuote(ctx,db):
    async for message in ctx.channel.history(limit=500):
        await createQuote(message,db)

def isQuoteChannel(message,server):
    quoteChannels = server["channels"]
    quoteChannelsInt = []#TODO this probably could be done better
    for cID in quoteChannels:
        quoteChannelsInt.append(int(cID))
    return message.channel.id in quoteChannelsInt

async def search(tags,db):
    return list(db.quotes.find({"tags":{"$in":tags}}))

async def getQuote(quoteID,db):
    return db.quotes.find_one({"ID":float(quoteID)})
