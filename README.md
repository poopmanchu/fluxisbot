# fluxisbot

A small command-line solver for a 3-word Fluxis-style chain puzzle.

Given a seed word and three rule selections (one per word position), the solver searches a dictionary and returns the highest-overlap chain:

`seed -> word1 -> word2 -> word3 -> seed`

## What it currently does

- Loads uppercase alphabetic words from a dictionary file.
- Lets you pick rules for each of the 3 positions.
- Finds the best-scoring chain by maximizing overlap at each transition.
- Prints the best sequence and overlap breakdown.

## Current rule support

- Exact word length
- No repeated letters
- Exact vowel count (`A E I O U`, with `Y` treated as consonant)
- Alternating vowel/consonant
- Contains a double letter

## Usage

```bash
python3 fluxisbot.py dict.txt
```

Then follow the interactive prompts:

1. Enter a seed word.
2. Choose rules for word 1, word 2, and word 3.
3. Provide `X` when a selected rule requires a parameter.

## Notes / limitations

- This is an early implementation and **does not yet cover all Fluxis rules**.
- For fuller rule coverage, the project will likely need **part-of-speech tagging** (and related linguistic features), which are not implemented yet.
