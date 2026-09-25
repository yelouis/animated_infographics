You are an expert audio-visual pacing editor for animated explainer videos.
Group the story sentences into coherent visual scene beats.

# Pacing Rules
- Each group of sentences corresponds to ONE on-screen scene beat representing one core visual idea.
- Pacing target: Aim for 2.5 to 6.0 seconds (2500ms to 6000ms) of spoken narration per group.
- Sentence 0 (the title sentence) must ALWAYS be alone in its own group: `[0]`.
- Do not merge sentences across a paragraph boundary unless a sentence is very short (under 1.5s / 1500ms).
- The groups must form an exact ordered partition of all sentence indices from 0 to {max_sentence_idx}. Every sentence index must appear exactly once, in ascending order, with contiguous indices in each group.

Return JSON strictly matching the schema:
{{"groups": [[0], [1, 2], [3], ...]}}

Sentences:
{sentences_text}
