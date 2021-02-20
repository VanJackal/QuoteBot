#!/bin/python

import re
import pymongo
from gtts import gTTS

async def createQuote(message,db):#should be passed a message and will return a true or false based on if it contains a valid quote, and will add the quote to the DB
    q = re.compile(r'(".+"(?:\s+-*\s+).+\d{4})')
    quotes = q.findall(message.content)

    if not quotes:
        return False

    quoteDicts = []
    for quote in quotes:
        quoteID = await getID(db)
        quoteDicts.append(await dictQuote(quote))
        await speakQuote(quoteDicts[0],quoteID)

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
    db.quotes.update_one({"msgID":"GlobalID"},{"$inc":{"ID":1}})
    quoteID = db.quotes.find_one({"msgID":"GlobalID"})["ID"]
    return quoteID

async def speakQuote(quoteDict,quoteID):
    quote = quoteDict["quote"]
    quotee = quoteDict["quotee"]
    year = quoteDict["year"]

    fullQuote = f"{quote}. {quotee}, {year}"

    tts = gTTS(fullQuote)
    tts.save(f"./Quotes/{quoteID}.mp3")
    
async def dbEntry(message,quoteDict,quoteID)
