import discord
import threading, queue

QUEUE_TIMEOUT = 60

async def createVoiceSession(guildID, channel, voiceSessions):
    vs = VoiceSession(guildID, voiceSessions)
    await vs._init(channel)
    return vs

class VoiceSession:
    def __init__(self, guildID, voiceSessions):
        self.active = True
        self.guildID = guildID
        self.q = queue.Queue()
        self.t = threading.Thread(target=self.player, daemon=True)
        self.voiceSessions = voiceSessions
        print(f"Started VoiceSession for {self.guildID}")
    
    async def _init(self,channel):
        self.voiceClient = await channel.connect()
        self.t.start()

    def player(self):
        while self.active and self.voiceClient.is_connected():
            try:
                path = self.q.get(timeout=QUEUE_TIMEOUT)
                self.voiceClient.play(discord.FFmpegPCMAudio(path))
                while self.voiceClient.is_playing() and self.active:
                    pass#TODO Change this (it be super hacky)
                self.q.task_done()
            except(queue.Empty):
                print(f'Queue Timeout in {self.guildID}')
        print(f'VoiceSession {self.guildID} Closed')
    
    def add(self, path):
        self.q.put(path)
    
    async def leave(self):
        print(f'VoiceSession {self.guildID} Closing')
        self.voiceClient.pause()
        self.active = False
        await self.voiceClient.disconnect()
        self.voiceSessions.pop(self.guildID)
        print(f'VoiceSession {self.guildID} Popped')
        self.q.join()
        self.t.join()
    
    def resetQueue(self):
        self.q.queue.clear()
    
    def getQueueSize(self):
        return self.q.qsize()