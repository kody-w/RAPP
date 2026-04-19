# Card-minting from agent.py: 64-bit seeds, 7-word incantations

Every RAPP agent has two presentations. There's the `.py` file — what the runtime sees. And there's the card — what the human sees. The card has art, a rarity, type chips, stats, and a 7-word mnemonic incantation. The card is also addressable: you can scan the QR code on the back and land on a deeplink that tells the brainstem how to install it.

The card is *derived* from the file. Same file, same card, every time.

The derivation is deterministic. We hash the source code with SHA-256, take 64 bits, and that's the **seed**. Everything else flows from the seed:

- Rarity (mythic / rare / core / starter) — bucketed from the seed's first byte.
- Hero type (LOGIC / DATA / SOCIAL / SHIELD / CRAFT / HEAL / WEALTH) — picked from the agent's tags first, then seed-fallback.
- HP / ATK / DEF / SPD / INT — modular arithmetic on the seed.
- Frame style, foil pattern, art glyph variant — seed-derived selections from fixed pools.
- The **incantation** — seven words pulled from a 1024-word list using the seed's bits as indices.

The 7-word incantation is the human-readable form of the seed. `"raven harbor mirror split echo nightfall vow"` encodes a specific 64-bit number which encodes a specific source SHA-256 prefix which encodes a specific agent. You can speak a card. Two strangers can be sure they're talking about the same agent without exchanging any URLs or hashes.

The round-trip is the contract. Given a card, you should be able to mint the original `.py` source from it (because the card stores the source verbatim along with the derived metadata). Given a `.py` source, you should always get the same card. Tests verify both directions:

```js
test('card.json is valid JSON and round-trips', async () => {
  const src = fs.readFileSync('agents/hacker_news_agent.py', 'utf8');
  const card = await RAPP.Card.mintCard(src, 'hacker_news_agent.py');
  const json = JSON.stringify(card);
  const parsed = JSON.parse(json);
  assert.equal(parsed.source, src);   // bit-for-bit
});

test('seed → mnemonic → seed → card is fully reproducible', async () => {
  const seed = card.seed;
  const words = RAPP.Card.seedToWords(seed);
  const recovered = RAPP.Card.wordsToSeed(words);
  assert.equal(recovered, seed);
});
```

Why bother with all this for what looks like UI flair? Because cards make agents *transferable* in human-shaped ways. You can print one. You can hand someone a deck. You can have a binder of agents the way you have a binder of stickers. The mnemonic means the unit of sharing isn't a URL or a hash — it's seven words you can read aloud.

It also means the RAR registry can store cards as JSON files (`docs/api/v1/cards/HOLO-borg-0001.json`) and the brainstem can render them identically to cards minted locally, because the rendering is purely a function of the stored fields.

The art is generated at render time from the seed too. We don't ship images. Every card the brainstem displays — including the 138 from RAR's library — is drawn from a few hundred bytes of metadata.

A card is what an agent *looks like to a human*. The seed is what makes "the same agent" mean exactly one thing across copies.
