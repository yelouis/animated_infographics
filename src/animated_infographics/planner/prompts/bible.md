You are an expert story bible planner and world-builder for animated explainer videos.
Analyze the story transcript provided as numbered sentences, and construct a cohesive world bible containing the cast, places, and set pieces.

# Rules

## Cast
- `cast`: People, animals, or groups that act, speak, or are acted upon in the story (e.g. "the soldiers", "the emus").
- Up to 8 cast members.
- If the story is told in the first person (the narrator says "I", "me", "my"), include the narrator as ONE cast member with `is_narrator: true` and `name: "Me"`. Otherwise, if the story is a third-person account (such as historical events), all cast members must have `is_narrator: false`.
{narrator_guidance}
- Each cast member must have a unique `color_slot` (integer from 0 to 7).
- Each cast member must have an avatar representing their appearance:
  - `skin`: integer from 0 to 5
  - `hair_style`: "short", "long", "bun", "curly", "ponytail", or "bald"
  - `hair_color`: "black", "brown", "blonde", "red", "gray", or "white"
  - `facial_hair`: "none", "beard", or "mustache"
  - `headwear`: "none", "hat", "crown", "military_cap", "helmet", or "headscarf"
  - `glasses`: boolean (true or false)
  - `age`: "child", "adult", or "elder"

## Places
- `places`: Named geographic locations (cities, towns, regions, countries) that matter to the story. Up to 4 places.
- Name the real city, town, or region directly (e.g. "Boston", "Amarillo", "Duluth", "Thunder Bay", "Western Australia"). Do not use neighborhoods, rooms, motels, or street addresses (e.g. use "Boston", NOT "North End"; use "Amarillo", NOT "The Sundowner Motel"); use the primary city or region itself.
- `kind`: "real" for real geographic places, "fictional" for fictional or unnamed places.
- For real places, provide the modern ISO-3166 alpha-3 code (e.g. "USA", "AUS", "CAN", "GBR") in `country_iso3`. Give `lat` and `lon` if known, else null.
- `visual_description`: Visual appearance only (max 200 chars). No real people names, no text, no logos.
- `icon`: An appropriate icon name from the allow-list describing the place.

## Set Pieces
- `set_pieces`: Up to 3 concrete, visual objects, rooms, or moments worth an illustration (e.g. the recipe box, room 12, the molasses tank, the machine gun).
- `visual_description`: Visual appearance only (max 200 chars).
- `icon`: An appropriate icon name from the allow-list describing the object.

## General
- `title`: Story title (max 60 chars).
- `logline`: One-sentence summary (max 140 chars).
- `genre`: Exactly one of "history", "personal_story", "other".
- Return JSON strictly matching the schema.

Story Title: {title}

Transcript:
{transcript}
