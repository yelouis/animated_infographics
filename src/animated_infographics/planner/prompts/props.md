Generate visual props for the given infographic template and narration beat.

# Story Bible
{compact_bible}

# Context
Previous beat (context only, do not use facts from here):
{prev_beat_text}

Current beat (MUST use facts ONLY from here or the bible):
{this_beat_text}

Next beat (context only, do not use facts from here):
{next_beat_text}

# Template: {template_name}
- Use when: {use_when}
- Writing rules:
{writing_rules}
- Field constraints:
{field_limits}

# Strict Guidelines
1. Facts: Use ONLY facts, numbers, dates, names, and quotes mentioned in THIS BEAT or the story bible. NEVER invent numbers, dates, statistics, quotes, or characters. Refer to people, places and objects by their names; never write ids like c1, p2 or v1.
2. Grounding:
   - For stat_callout: the number MUST match a number spoken in this beat.
   - For timeline: dates/years MUST appear in the story transcript.
   - For kinetic_quote: text MUST be a verbatim span copied from this beat narration.
3. Length: Stay strictly within all character limits and line counts.
4. Style: Write short, concrete, punchy on-screen display copy. Do not copy full sentences wholesale unless required by kinetic_quote.
5. JSON only matching the schema.
