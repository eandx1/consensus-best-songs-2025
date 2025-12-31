# Consensus Best Songs 2025

## About

This project is the result of a yearly personal obsession: figuring out how to prioritize the latest music based on "Best Songs of 2025" lists from a wide variety of publications. I love finding new music that I wouldn't have discovered otherwise.

It was also a good excuse to experiment with a variety of AI models and tools for Python development, data analysis, and frontend work.

I scraped around 28 song lists and did the following:

* **Canonicalization**: Used the Spotify search API (with [Spotipy](https://spotipy.readthedocs.io/en/latest/)) to find IDs and canonical artist and song names
* **YouTube Matching**: Looked up YouTube Music and YouTube IDs (via ytmusicapi)
* **Quote Extraction**: Ran reviews through Claude Haiku or Sonnet to distill down to a quote per source

I then developed ranking engine with a variety of knobs -- source weights, how much to value a rank #1 song over a #10, how to give boosts to songs that cross publication types or are mentioned on a large number of lists, and more.

The resulting site lets you view the result of that ranking, but you can customize the knobs and share your own, instead.

🔗 **Live Site:** [https://bestsongs2025.com/](https://bestsongs2025.com/)

## 🏗️ Project Structure

The project is built as a lightweight, static web application with no build steps or complex frameworks.

- **`index.html`**: The main entry point using semantic HTML and Pico CSS
- **`script.js`**: Handles data loading, the ranking engine logic, state management, and DOM rendering
- **`data.json`**: The single source of truth containing:
  - Configuration (ranking parameters, boosters, cluster metadata)
  - Source definitions (weights, URLs, categories)
  - Song data (artists, titles, media IDs, and source citations)

_Note: I'll check in the notebook and Python code soon for posterity._

## 🛠️ Technical Choices

- **Static Data**: Chosen for simplicity and ease of hosting. The entire application runs in the browser in plain Javascript with no backend or build steps
- **[Pico CSS](https://picocss.com/)**: A minimal, semantic-first CSS framework that provides a clean "dark mode" aesthetic. I know little of UI or frontend design, so this helped save me from myself
- **URL State Sync**: All ranking parameters (decay rates, boosters, weights) are synchronized to the URL query string, making specific ranking configurations shareable
- **Lite YouTube**: Uses the [lite-youtube](https://github.com/justinribeiro/lite-youtube) web component for fast video embeds
- **Hosting Solution**: Initially I just used Github Pages but decided to move to Vercel with an actual domain name for fun

## Development Quirks

### Data Cleaning

* **Manual Overrides**: I manually corrected or specified around 30 song/artist names to work around Spotify search failures, including songs simply missing from Spotify
* **Matching Heuristics**: Spotify, YouTube, and YouTube Music results were vetted with surprisingly good comparison heuristic functions Gemini 3 Pro helped me with, often using [RapidFuzz](https://pypi.org/project/RapidFuzz/). Many of the review sites also linked to official videos or Spotify tracks, which I leveraged

### Shadow Ranks 👻

Not all lists are ranked. For unranked lists, I assigned a **Shadow Rank** based on the list's length to ensure fair weighting. For example, [Variety's The Best Songs of 2025](https://variety.com/lists/best-songs-2025/) has 61 unranked songs so I used the midpoint 
$$(1 + 61) / 2 = 31$$

### 🏷️ Category Decisions

I wanted to have some notion of crossover hits, letting me boost songs that appeared on multiple types of publications. These are still a work in progress and only used for one boost that can be disabled.

The categories are currently:

- **🏛️ Critical Authority**: Essential critical voices from major institutions known for depth, rigorous standards, and long-standing industry trust.
- **⚡ Tastemakers**: Digital trendsetters and established indie mainstays driving the current musical conversation.
- **🧪 Specialists**: Niche expert curators focused on deep cuts, avant-garde discoveries, and specific genre depth.
- **📡 Mainstream**: High-frequency media outlets and lifestyle sources tracking mass cultural appeal and global broadcasting trends.

## AI Development Journey

### Web Chatbots: Gemini 3 Pro

While coding in the notebook, I chatted with [Gemini 3 Pro](https://deepmind.google/models/gemini/pro/) usually in its Thinking mode on the web, getting tips and code for web scraping, parsing, and ranking. All the modern chatbots I've tried are extremely impressive, but there are still problems. Here are the ones I encountered with Gemini 3 Pro:

- **Context changes are hard**: After a long-running chat where we'd discussed and made many decisions, I'd sometimes switch to a new chat to dig into the finer points of one choice, giving it some ramp-up context first. In the new chat, it would essentially tell me how bad the decision I'd made with it in the other chat was, when it had seemed quite satisfied over there!

  If it wasn't a topic I already knew well, it was hard to know if the decision was _actually_ bad -- perhaps because I'd steered it into sycophancy due to my obsession with pros/cons and edge cases -- or the new chat only thought it was bad because I hadn't given it enough context on why the decision was made that way. I suspect this still also happens when tools need to compress the context and lose some detail.

- **Stale information**: Until near the end of the project, I hadn't run into a situation where it really led me astray, but then I asked it about developing a feature to let users export their top N songs to a YouTube playlist. It knew the real heavy weight solution was with OAuth and a supported Google API, but I'd thought one could create an unnamed playlist just by putting some video IDs in a URL for the user. Indeed, you can still sort of do that, but on desktop it appears YouTube has removed the button to save the playlist.
  Gemini was convinced you could click on something to do so or use a variety of other non-working URL format hacks, no matter how much evidence I gave it to the contrary. I wanted it to work, too, Gemini!
- **Code snippets to save on generation**: I do not know Javascript or CSS well. Gemini would sometimes give me a great starting point but if I asked it to refine something, it would start giving me pieces and I'd have to ask it to regenerate the whole file for me. It'd do so, but other bits would often change in the process.
- **Inauthentic names**: Gemini frequently gave proper names to the ranking models we discussed. It made me think they were well-known, standard solutions. Then, later, I'd go search for a name and find it apparently wasn't real or at least not widely known.

### Cursor

This was my first experience with Cursor. A few thoughts:

- **Enthusiasm**: Much like Claude Code, the Cursor agent chat interface _wants to do stuff_. It doesn't feel like a great place to _discuss_ a solution, which is why I continued to use Gemini on the web. Asking about something in the agent chat tended to result in it going off and building something. I did love that when I asked it to do something, though, it was incredibly enthusiastic. "I'll commit these changes for you!"
- **Weird review/commit bugs**: I was probably using it wrong, but often even if I clicked Review and accepted changes and even if they were committed, it seemed to think they were still open files.
- **Sonnet 4.5 integration**: Cursor seemed well-optimized for this model. I didn't notice from the scroll of its "thoughts" that it had to back track much. When I tried Gemini 3 Pro Preview, it occasionally got stuck in a loop or its "thoughts" suggested it had to back track or go another way.
- **CSS best practices**: The models didn't initially prioritize mobile-first design and sometimes snuck in fixed pixel widths or used CSS that wasn't well aligned with Pico CSS's conventions despite prompting. 

### Quote extraction task

One of the tasks in the notebook was to extract a decent quote from the normally paragraph-long review of a song from each source site. LLMs love to summarize or smooth over the grammar broken by the extraction, so this was a challenge.

I wanted to be very careful, here, so enforced strict substring matching, either of the full quote or pieces joined by " ... ". I also added a way for the model to report failure since some reviews just weren't appropriate (for example, talking about the artist but not the song).

Ultimately I made a first pass with Haiku and then fell back to Sonnet for cases that didn't work.

## Analysis

I have some fun visualizations of the data I'll add here soon.

## 👤 Contact

You can find me over at [LinkedIn](https://www.linkedin.com/in/everett-anderson-swe/).
