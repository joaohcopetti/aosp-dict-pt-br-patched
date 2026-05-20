import sys
from pathlib import Path

import hunspell
from unidecode import unidecode

sys.path.append(str(Path("../libs").absolute()))

from wordlist_combined import WordAttributes, WordlistCombined

"""
Most grammar logic references I got from here:
https://files.cercomp.ufg.br/weby/up/28/o/novo_acordo.pdf.

Due to the simplicity and straight to the point examples.

It's a PDF from Universidade Federal de Goiás (ufg.br), so I'm assuming it's trustworthy.
"""


def write_combined_file(wordlist, new_words):
    WordlistCombined(wordlist.header, new_words).write_to_file(
        "../pt_BR_wordlist_patched.combined"
    )


def is_valid_correction(word: str, suggested_word: str):
    """
    There are a few assertions we can make to confirm a suggestion is actually
    fixing a grammatically wrong word. We need to enforce these checks.
    Or Hunspell will suggest some correction for words that doesn't need to be corrected,
    and it's better to keep these words untouched then.

    The suggestions that shouldn't be corrected can be seen in the "logs/ignored_suggestions.txt",
    with the suggested correction given by Hunspell.
    If there is a valid suggestion in that file then the logic here should be improved to match it.
    """

    if "ü" in word and not word[0].isupper():
        return True

    if "éi" in word or "ói" in word and (unidecode(word) == unidecode(suggested_word)):
        return True

    if ("oo" in word or "ôo" in word or "ee" in word or "êe" in word) and (
        unidecode(word) == unidecode(suggested_word)
    ):
        return True

    if word.startswith(("pá", "pé", "pê", "pé", "pó")) and (
        unidecode(word) == unidecode(suggested_word)
    ):
        return True

    if unidecode(word) == unidecode(suggested_word):
        return True

    if ("ii" in word or "oo" in word or "oô" in word) and "-" in suggested_word:
        return True

    if "-" in word and unidecode(word.replace("-", "")) == unidecode(suggested_word):
        return True

    if not word.endswith("p") and word.replace("p", "") == suggested_word:
        return True

    if "ct" in word and word.replace("ct", "t") == suggested_word:
        return True

    return False


def main():
    spell = hunspell.HunSpell("../dict/pt_BR.dic", "../dict/pt_BR.aff")
    wordlist = WordlistCombined.read_from_file("../pt_BR_wordlist.combined")

    total_words = len(wordlist.words)

    count = {"words_processed": 0, "corrected_words": 0, "ignored_suggestions": 0}

    corrected_words_file = open("../logs/corrected_words.txt", "w")
    ignored_suggestions_file = open("../logs/ignored_suggestions.txt", "w")

    new_words: dict[str, WordAttributes] = dict()

    for word, wordlist_attrs in wordlist.words.items():
        # We'll do some checks before actually validating the suggested word
        # because some cases we can completely ignore it.
        # Such as:
        # - Starting with capital letter: it's a proper noun or abbreviation
        # - Hunspell checked it and the word is correct
        # - There's no suggestion available, nothing can be done
        # - Hunspell suggested multiple words trying to find the best suggestion

        print(f"Processing {count['words_processed']} of {total_words}...")
        count["words_processed"] += 1

        # KEEP UNCHANGED
        # Starting with capital letter: it's a proper noun or abbreviation
        if word[0].isupper():
            new_words[word] = wordlist_attrs
            continue

        # KEEP UNCHANGED
        # Hunspell checked it and the word is correct
        if spell.spell(word):
            new_words[word] = wordlist_attrs
            continue

        suggestions = spell.suggest(word)

        # KEEP UNCHANGED
        # There's no suggestion available, nothing can be done
        if not suggestions:
            new_words[word] = wordlist_attrs
            continue

        suggested_word: str = suggestions[0]

        # KEEP UNCHANGED
        # Hunspell suggested multiple words trying to find the best suggestion
        if " " in suggested_word:
            new_words[word] = wordlist_attrs
            continue

        if is_valid_correction(word, suggested_word):
            # Sometimes a corrected word is already in the new words,
            # because some dictionaries include both wrong and right words.
            # So in this case just do nothing to keep the word with highest frequency.
            if suggested_word in new_words:
                continue

            new_words[suggested_word] = wordlist_attrs

            corrected_words_file.write(f"word={word},new_word={suggested_word}\n")
            count["corrected_words"] += 1

            continue
        else:
            count["ignored_suggestions"] += 1

            ignored_suggestions_file.write(f"word={word},suggestion={suggested_word}\n")

    with open("../logs/results.txt", "w") as f:
        f.write(f"Total words: {total_words}\n")
        f.write(f"Total words after changes: {len(new_words)}\n")
        f.write(f"Corrections applied: {count['corrected_words']}\n")
        f.write(f"Ignored suggestions: {count['ignored_suggestions']}\n")

    corrected_words_file.close()
    ignored_suggestions_file.close()

    write_combined_file(wordlist, new_words)


if __name__ == "__main__":
    main()
