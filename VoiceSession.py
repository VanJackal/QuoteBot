import discord
import threading, queue

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
    
    async def _init(self,channel):
        self.voiceClient = await channel.connect()
        self.t.start()

    async def player(self):
        while self.active and self.voiceClient.is_connected():
            path = self.q.get()
            self.voiceClient.play(discord.FFmpegPCMAudio(path))
            while self.voiceClient.is_playing():
                pass#TODO Change this (it be super hacky)
            self.q.task_done()
        self.voiceSessions.pop(self.guildID)
    
    def add(self, path):
        self.q.put(path)
    
    def leave(self):
        self.voiceClient.pause()
        self.active = False
        self.q.join()
        self.voiceClient.disconnect()