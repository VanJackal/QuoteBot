#!/bin/python

import re
import pymongo
from gtts import gTTS

async def createQuote(message,db):#should be passed a message and will return a true or false based on if it contains a valid quote, and will add the quote to the DB
    q = re.compile(r'(".+"(?:\s*-*\s+).+\d{4})')
    quotes = q.findall(message.content)

    if not quotes:
        return False

    quoteDicts = []
    for quote in quotes:
        quoteID = await getID(db)
        quoteDicts.append(await dictQuote(quote))
        audio = await speakQuote(quoteDicts[0],quoteID)
        await dbEntry(message,quoteDicts[0],quoteID,audio,db)

    await message.add_reaction("🔈")

    return True

async def dictQuote(content):#returns a dict of {quote,quotee,year}, based on a quote string
    content = content.strip()
    quote = re.search(r'((?!").+(?="))',content)
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
    db.quotes.update_one({"msgID":"GlobalID"},{"$inc":{"IDCounter":1}})
    quoteID = db.quotes.find_one({"msgID":"GlobalID"})["IDCounter"]
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
