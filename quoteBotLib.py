#!/bin/python

import re
import pymongo

async def createQuote(message,db):#should be passed a message and will return a true or false based on if it contains a valid quote, and will add the quote to the DB
    q = re.compile(r'(".+"(?:\s+-*\s+).+\d{4})')
    quotes = q.findall(message.content)

    if not quotes:
        return False
    quoteID = getID()

    quoteDicts = []
    for quote in quotes:
        quoteDicts.append(await dictQuote(quote))
    return quoteDicts

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

async def getID():
    quoteID = 0
    return quoteID
