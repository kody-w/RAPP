# The poker hand: why cards tuck behind the chat instead of dominating it

Card mode in the brainstem is a fanned poker hand. Three cards, rotated outward around their bottom-center pivot, with their bottom halves hidden behind the chat input bar. Only the tops peek up. Hover one and it lifts a couple hundred pixels with a slight scale-up — like raising a card from your hand to play it.

The first version did not look like this. The first version was three cards laid flat in a row above the input, full-size, perfectly readable. It looked like every other tool's "suggested actions" bar. The cards stopped being cards.

The card metaphor matters because it makes a thing concrete. Each card is *one agent*. You can hold a card. You can flip a card. You can put a card down. When the cards are tucked into a fan, the user understands implicitly that they have a *hand*: a curated set, picked from a *binder*, ready to *play*. That whole vocabulary works because the visual matches it.

Three constraints that produced the current layout.

**The chat is the focus.** The input is at the bottom; the conversation is above. The hand cannot dominate either area. It lives in the negative space *between* the chat content and the input — peeking up so the user remembers it's there, never tall enough to push the welcome text or the toolbar around.

**Cards live behind the bar, not on top of it.** The footer's input row has its own opaque background and a higher z-index than the hand cards. The bottoms of the cards extend down into the input area but are visually clipped by the bar's solid color. This is the "tucked into your hand" effect — you don't see the whole card unless you choose to.

**Hover is the playing motion.** When you hover, the card translates up by ~260px and scales back to its full size. The transform-origin is the card's bottom-center, so the lift looks like grabbing the top of the card and pulling it forward. Right-click opens the full holo modal (the showcase view); left-click sends the card's example prompt to the chat (the "play" action).

The fan rotation is pure CSS — each card sets `--rot` via inline style based on its position in the hand:

```js
const SPREAD = 14;
cards.forEach((c, i) => {
  const offset = i - (n - 1) / 2;
  const rot = offset * SPREAD;
  el.style.setProperty('--rot', `${rot}deg`);
});
```

```css
.hand-card {
  transform-origin: center bottom;
  transform: translateY(60px) rotate(var(--rot)) scale(.42);
}
.hand-card:hover {
  transform: translateY(-260px) rotate(0deg) scale(1);
  z-index: 200;
}
```

The middle card sits upright; the outer cards splay outward. Their bottom-center points are pinned to the same baseline, so the rotation looks like a real arc.

The lesson: when your design has a metaphor, the layout has to *enforce* the metaphor. Cards laid flat in a row are not a hand. Cards fanned and tucked behind something are. The fan does the explanatory work.
