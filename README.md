# Consensus Best Songs 2025

## About

This project is the result of a yearly personal obsession to figure out how to prioritize the latest songs I should listen to based off the many "Best Songs of 2025" lists from a wide variety of publications. I love finding new music that I wouldn't have come across otherwise.

It was also an excuse to try using a variety of AI models and tools for Python development, data analysis, and web frontend work.

I scraped around 28 lists, canonicalized them using the Spotify search API (with [Spotipy](https://spotipy.readthedocs.io/en/latest/)), looked up YouTube Music and YouTube IDs (with [ytmusicapi](https://ytmusicapi.readthedocs.io/en/stable/)), ran reviews through Claude Haiku or Sonnet to extract a quote, and developed a couple of ranking options with many knobs -- source weights, how much to value a rank #1 song over a #10, how to give boosts to songs that cross publication types or are mentioned on a large number of lists, and more.

The resulting site lets you view the result of that ranking, but you can customize the knobs and share your own, instead.

🔗 **Live Site:** [https://bestsongs2025.com/](https://bestsongs2025.com/)

## 🏗️ Project Structure

The project is built as a lightweight, static web application with no build steps or complex frameworks.

- **`index.html`**: The main entry point containing the semantic HTML structure and Pico CSS integration.
- **`script.js`**: Handles data loading, the ranking engine logic, state management, and DOM rendering.
- **`data.json`**: The single source of truth containing:
  - Configuration (ranking parameters, boosters, cluster metadata).
  - Source definitions (weights, URLs, categories).
  - Song data (artists, titles, media IDs, and source citations).

I'll check in the notebook and Python code soon for posterity.

## 🛠️ Technical Choices

- **Static Data**: Chosen for simplicity and ease of hosting. The entire application runs in the browser in plain Javascript with no backend or build steps. All the data is loaded from `data.json`.
- **Pico CSS**: A minimal, semantic-first CSS framework that provides a clean "dark mode" aesthetic without the overhead of heavy UI libraries. I know nothing of UI or frontend design, so this helped save me from myself.
- **URL State Sync**: All ranking parameters (decay rates, boosters, weights) are synchronized to the URL query string, making specific ranking configurations shareable (deep-linking).
- **Lite YouTube**: Uses the [lite-youtube](https://github.com/justinribeiro/lite-youtube) web component so the video embeds load very quickly.
- **Hosting Solution**: Initially I just used Github Pages but decided to move to Vercel with an actual domain name for fun.

## Development Quirks

### Misspellings, Formatting, and Bad Searches

- Parsing each site in [BeautifulSoup](https://beautiful-soup-4.readthedocs.io/en/latest/) was tedious but doable. In retrospect, I probably should've asked an AI to write each set of extraction rules, but I usually just did it by hand. It started as just a couple of sites!
- I manually corrected several song or artist names so Spotify's search worked well. Thankfully, there were
  only about 30 manual overrides necessary, about half of which just weren't available on Spotify.
- YouTube's search is much more willing to return unrelated content than Spotify's, at least how I used it.
- Spotify, YouTube, and YouTube Music results were vetted with surprisingly good comparison heuristic functions Gemini 3 Pro helped me with, often leveraging [RapidFuzz](https://pypi.org/project/RapidFuzz/). Many of the review sites also linked to official videos or Spotify tracks, which I leveraged.

### Shadow Ranks 👻

Not all lists are ranked. For unranked lists, I assigned a **Shadow Rank** based on the list's length to ensure fair weighting without discarding valuable data. For example, [Variety's The Best Songs of 2025](https://variety.com/lists/best-songs-2025/) has 61 unranked songs so I used the midpoint $(1 + 61) / 2 = 31$.

### 🏷️ Category Decisions

I wanted to have some notion of crossover hits, letting me boost songs that appeared on multiple types of publications, so I grouped them into four categories, often checking with Gemini to see if they made sense. I'm not entirely happy with the assignments, though, and haven't exposed a way to change them in the UI. They're only used for one boost that users can disable by setting to 0%, though.

The categories are:

- **🏛️ Critical Authority**: Essential critical voices from major institutions known for depth, rigorous standards, and long-standing industry trust.
- **⚡ Tastemakers**: Digital trendsetters and established indie mainstays driving the current musical conversation.
- **🧪 Specialists**: Niche expert curators focused on deep cuts, avant-garde discoveries, and specific genre depth.
- **📡 Mainstream**: High-frequency media outlets and lifestyle sources tracking mass cultural appeal and global broadcasting trends.

## AI Development Journey

### Web Chatbots: Gemini 3 Pro

While coding in the notebook or thinking about decisions like where to host, I chatted with [Gemini 3 Pro](https://deepmind.google/models/gemini/pro/) usually in its Thinking mode on the web, getting tips and code for web scraping, parsing, and ranking. All the modern chatbots I've tried are extremely impressive, but there are still problems. Here are the ones I encountered with Gemini 3 Pro:

- **Context changes are brutal**: After a long-running chat where we'd discussed and made many decisions, I'd sometimes switch to a new chat to dig into the finer points of one choice, giving it some ramp-up context about it first. In the new chat, it would essentially tell me how bad the decision I'd made with it in the other chat was, when it had seemed quite satisfied over there!

  If it wasn't a topic I already knew well, it was hard to know if the decision was _actually_ bad -- perhaps because I'd steered it into sycophancy due to my obsession with pros/cons and edge cases -- or the new chat only thought it was bad because I hadn't given it enough context on why the decision was made that way. I suspect this still also happens when tools need to compress the context and lose some detail.

- **Solving the imposible**: Until near the end of the project, I hadn't run into a situation where it really led me astray, but then I asked it about developing a feature to let users export their top N songs to a YouTube playlist. It knew the real heavy weight solution was with OAuth and a supported Google API, but I'd thought one could create an unnamed playlist just by putting some video IDs in a URL for the user. Indeed, you can still sort of do that, but on desktop it appears YouTube has removed the button to save the playlist.

  Gemini was convinced you could click on something to do so or use a variety of other non-working URL format hacks, no matter how much evidence I gave it to the contrary. I wanted it to work, too, Gemini.

- **Code snippets to save on generation**: I do not know Javascript or CSS well. Gemini would sometimes give me a great starting point but if I asked it to refine something, it would start giving me pieces and I'd have to ask it to regenerate the whole file for me. It'd do so, but other bits would often change in the process.
- **Inauthentic names**: Gemini seemed to like to give things like the ranking models we were discussing proper names. It made me think, "Oh! This must be a real thing people do and have given this name," increasing my trust in it. Then, later, I'd go search for that name and find it apparently wasn't real or at least not widely known. This made me less confident in speaking with my data science friends about my solutions.

### Cursor

This was my first experience with Cursor. A few thoughts:

- **Enthusiasm**: Much like Claude Code, the Cursor agent chat interface _wants to do stuff_. It doesn't feel like a great place to _discuss_ a solution, which is why I continued to use Gemini on the web. Asking about something in the agent chat tended to result in it going off and building something. I did love that when I asked it to do something, though, it was incredibly enthusiastic. "I'll commit these changes for you!"
- **Weird review/commit bugs**: I was probably using it wrong, but often even if I clicked Review and accepted changes and even if they were committed, it seemed to think they were still open files.
- **Sonnet 4.5 integration**: Cursor seemed well-optimized for this model. I didn't notice from the scroll of its "thoughts" that it had to back track much. When I tried Gemini 3 Pro Preview, it occasionally got stuck in a loop or its "thoughts" suggested it had to back track or go another way -- it definitely didn't seem as robust as the web chatbot version.
- **CSS best practices**: I tried to insist in [AGENTS.md](./AGENTS.md) that we were going to use semantic HTML and Pico CSS. I initially didn't specifically say it should be "mobile-first" -- it is 2025! But that would've been good because it structured the styles more as desktop first with mobile overrides. I also noticed that both Sonnet and Gemini were happy to throw in some fixed pixel sizes here and there or generally deviate from the ideals of semantic HTML + Pico CSS. Again, I don't really know CSS well at all, but I'd tend to have to ask, "I see you've set this column to a fixed pixel width. Will that be responsive?".

### Quote extraction task

One of the tasks in the notebook was to extract a decent quote from the normally paragraph-long review of a song from each source site. I knew this would be tricky because the LLMs would love to summarize or smooth over the grammar broken by the extraction. I decided to attempt to prompt it to limit the types of quotes it could create by asking it to prefer full single substring extractions or multiple extract substrings joined by " ... ". I also needed to prompt that extraction can fail -- there might not be a suitable quote about the song itself, so added an error reportign mechanism and path for the model to punt.

I had code afterwards to verify that the quote was made of exact substrings.

As usual, prompting took a bit of work. A bit more than I would've thought in late 2025 for this task!

Ultimately I made a first pass with Haiku and then fell back to Sonnet for cases that didn't work. Some of the quotes are a bit wonky, still.

## Analysis

I have some fun visualizations of the data I'll add here soon.

## 👤 Contact

You can find me over at [LinkedIn](https://www.linkedin.com/in/everett-anderson-swe/).
