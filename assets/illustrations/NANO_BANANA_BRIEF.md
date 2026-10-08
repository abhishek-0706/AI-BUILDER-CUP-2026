# People avatars: brief for Nano Banana (Gemini app)

Today every person in the app is a letter in a circle. These avatars replace them. The app
will show each image as soon as the file exists, and keeps the initials if it does not.

## Before you start

Open the Gemini app, choose image generation (Nano Banana), and **upload
`assets/illustrations/field-sales-rep.png` as a reference image** with every prompt. That is
what keeps all the faces in the same illustration family as the start-screen characters.

## Format for every avatar

- **Square**, 1024 x 1024
- **Head and shoulders**, face centred, looking slightly toward the camera
- **Background:** plain soft mint, `#E6F5F0`, no scenery (the app crops it into a circle)
- **No text, no logos**, nothing written on clothing or badges
- Save as PNG with the **exact file name** below, into `assets/illustrations/people/`

## Style line (paste at the end of every prompt)

```
Premium semi-3D editorial portrait, the same illustration style, lighting, skin rendering and
level of detail as the reference image. Head and shoulders, centred, soft studio light from the
upper left, plain soft mint background (#E6F5F0), no text, no logos, no cartoon or anime look.
Square image.
```

## The people

| File name | Who | Prompt (then add the style line) |
|---|---|---|
| `anita-sharma.png` | The rep the demo follows | An Indian woman in her early 30s, field sales executive, smart casual deep teal polo shirt, hair tied back, confident warm smile. |
| `rohit-menon.png` | Rep, top of the team | An Indian man in his late 20s, field sales rep, deep teal polo shirt, short hair, energetic friendly expression. |
| `kavya-reddy.png` | Rep, furthest behind | An Indian woman in her mid 20s, field sales rep, deep teal polo shirt, long hair, thoughtful expression. |
| `imran-qureshi.png` | Rep | An Indian man in his 30s, field sales rep, deep teal polo shirt, neat beard, calm expression. |
| `vikram-rao.png` | Buyer, FreshMart Express | An Indian man in his 40s, retail category buyer, light blue formal shirt, no tie, reading glasses pushed up, serious no-nonsense expression. |
| `meera-iyer.png` | Buyer, DailyNeeds Supermart | An Indian woman in her 40s, regional merchandising head, smart blazer over a plain top, composed, sharp expression. |
| `priya.png` | Shopper, 32, software engineer | An Indian woman around 32, casual smart top, fitness-minded, relaxed friendly expression. Background warm cream `#FFF3E3` instead of mint. |
| `rahul.png` | Shopper, 45, gym owner | An Indian man around 45, athletic build, plain dark t-shirt, confident expression. Background warm cream `#FFF3E3` instead of mint. |

Shoppers use cream because the shopper side of the app uses the warm orange palette.

## Check before you save

- [ ] All eight look like one family, and match the reference character's style
- [ ] Faces are centred with space around the head, so a circle crop does not cut the chin or hair
- [ ] No text, logos or badges anywhere
- [ ] Hands, if visible, look right

Drop them into `assets/illustrations/people/` and say "done". Backgrounds that come out
slightly off-colour are fine; they can be corrected afterwards.
