import asyncio, json, io, edge_tts
S = json.load(io.open('script.json', encoding='utf-8'))
async def main():
    for s in S:
        c = edge_tts.Communicate(s['text'], 'en-IN-NeerjaNeural', rate='+16%')
        await c.save('audio/%s.mp3' % s['id'])
        print('ok', s['id'])
asyncio.run(main())
