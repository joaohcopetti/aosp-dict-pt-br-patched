import hunspell
from unidecode import unidecode

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

    words_processed_count = 0
    corrected_words_count = 0
    ignored_suggestions_count = 0

    corrected_words_file = open("../logs/corrected_words.txt", "w")
    ignored_suggestions_file = open("../logs/ignored_suggestions.txt", "w")

    new_words: dict[str, WordAttributes] = dict()

    for word, wordlist_attrs in wordlist.words.items():
        words_processed_count += 1
        print(f"Processing {words_processed_count} of {total_words}...")

        # KEEP UNCHANGED
        # Fist letter uppercase, it's a proper noun or abbreviation.
        # No relevant changes to be made on abbreviations.
        if word[0].isupper():
            new_words[word] = wordlist_attrs
            continue

        # KEEP UNCHANGED
        # Hunspell detected as correct word.
        if spell.spell(word):
            new_words[word] = wordlist_attrs
            continue

        suggestions = spell.suggest(word)

        # KEEP UNCHANGED
        # There's nothing to be suggested, so nothing to be done
        if not suggestions:
            new_words[word] = wordlist_attrs
            continue

        suggested_word: str = suggestions[0]

        # KEEP UNCHANGED
        # Sometimes Hunspell will suggest multiple words
        # for a given word, which is always wrong in this case.
        if " " in suggested_word:
            new_words[word] = wordlist_attrs
            continue

        if is_valid_correction(word, suggested_word):
            if suggested_word in new_words:
                continue

            new_words[suggested_word] = wordlist_attrs

            corrected_words_file.write(f"word={word},new_word={suggested_word}\n")
            corrected_words_count += 1

            continue
        else:
            ignored_suggestions_count += 1

            ignored_suggestions_file.write(f"word={word},suggestion={suggested_word}\n")

    with open("../logs/results.txt", "w") as f:
        f.write(f"Total words: {total_words}\n")
        f.write(f"Total words after changes: {len(new_words)}\n")
        f.write(f"Corrections applied: {corrected_words_count}\n")
        f.write(f"Ignored suggestions: {ignored_suggestions_count}\n")

    corrected_words_file.close()
    ignored_suggestions_file.close()

    write_combined_file(wordlist, new_words)


if __name__ == "__main__":
    main()
