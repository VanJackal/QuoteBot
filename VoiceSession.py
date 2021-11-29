import discord
import queue
import asyncio

QUEUE_TIMEOUT = 60
SESSION_TIMEOUT_LIMIT = 5 # 5 x 60 second timeouts = 5min

async def createVoiceSession(guildID, channel, voiceSessions):
    vs = VoiceSession(channel, guildID,  voiceSessions)
    return vs

class VoiceSession:
    def __init__(self, channel, guildID, voiceSessions):
        self.active = True
        self.guildID = guildID
        self.q = queue.Queue()
        self.voiceSessions = voiceSessions
        self.timeoutCounter = 0
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self._init(channel))
        print(f"Started VoiceSession for {self.guildID}")
    
    async def _init(self,channel):
        self.voiceClient = await channel.connect()
        self.loop.create_task(self.player())

    async def player(self):
        while self.active and self.voiceClient.is_connected():
            try:
                path = self.q.get(timeout=QUEUE_TIMEOUT)
                self.voiceClient.play(discord.FFmpegPCMAudio(path))
                while self.voiceClient.is_playing() and self.active:
                    pass#TODO Change this (it be super hacky)
                self.q.task_done()
            except(queue.Empty):
                self.timeoutCounter += 1
                print(f'Queue Timeout in {self.guildID}')
            if (not self.voiceClient.is_connected()) or self.timeoutCounter > SESSION_TIMEOUT_LIMIT:
                await self.leave()
                break
        print(f'VoiceSession {self.guildID} Closed')
    
    def add(self, path):
        self.q.put(path)
    
    async def leave(self):
        self.active = False
        print(f'VoiceSession {self.guildID} Closing')
        if self.voiceClient.is_connected():
            self.voiceClient.pause()
            await self.voiceClient.disconnect()
        self.voiceSessions.pop(self.guildID)
        print(f'VoiceSession {self.guildID} Popped')
    
    def resetQueue(self):
        self.q.queue.clear()
    
    def getQueueSize(self):
        return self.q.qsize()