import json
import pathlib
import wave

scenes=json.loads(pathlib.Path('demo/tooling/submission_script.json').read_text(encoding='utf-8'))
for scene in scenes:
    audio=pathlib.Path('tmp/submission-audio',scene['id']+'.wav').resolve()
    with wave.open(str(audio)) as clip:
        scene['durationMs']=round(clip.getnframes()/clip.getframerate()*1000)
    scene['audio']=str(audio)
pathlib.Path('tmp/submission-narration.json').write_text(json.dumps(scenes,indent=2),encoding='utf-8')
