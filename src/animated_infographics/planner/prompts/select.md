Select the best visual templates for each narration beat in this window.

# Story Bible
{compact_bible}

# Previous Choices
{previous_choices}

# Available Templates
{template_menu}

# Selection Guidelines
Match the semantic intent of each beat:
- Spoken exchange between characters -> dialogue
- Text messages, DMs, or phone chats -> text_thread
- A person's first real appearance in the story -> character_intro
- A strong reaction, emotion, or feeling -> emotion_beat
- How people relate (family, alliances, conflict) -> relationship_map
- A specific number, quantity, measurement, or stat -> stat_callout
- A sequence of dated events or milestone years -> timeline
- A journey or geographic position -> map_focus
- Arriving somewhere or establishing scene location -> location
- A key object, artifact, or dramatic moment -> set_piece
- Comparing two sides, options, or people (A vs B) -> comparison
- Cause and effect chain (X led to Y) -> cause_effect
- A set of 2 to 4 parallel items, reasons, or steps -> icon_list
- A major twist, punchline, or shocking revelation -> reveal
- A punchy statement, thematic line, or quote -> kinetic_quote

# Rules
- Provide exactly one choice for each beat in the window.
- For each beat, choose a 'primary' template and a different 'alternate' template.
- primary != alternate.
- Both primary and alternate MUST be chosen from the Available Templates above.
- Return valid JSON matching the schema.

# Beats to Plan
{window_beats}
