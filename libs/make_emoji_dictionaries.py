#!/bin/python
# Creates two-way emoji dictionaries from Signal and CLDR data
import argparse
import http.client
import json
import os
import re
import emoji
import time
from functools import cache

# Tuning params
CLDR_RANK = 500
MAX_POPULARITY = 300
MAX_FREQUENCY = 20
DESCRIPTION_FREQUENCY = 0
BAD_WORDS = ('1', '-1', '11')   # cause noise at lookup
MAX_SHORTCUTS = 18  # AOSP keyboards can only display 18 suggestions by default
TOP_WORDS_LIMIT = 50  # how many words to consider top words that should be ignored (from a normal dictionary)
TOP_WORD_IGNORE_LENGTH = 1  # if a description has up to this many words, top words will not be removed

DESCRIPTION_RANK = -1

VERSION = 19  # dictionary version, should be increased if the created dictionaries change

comma_pattern = re.compile(',')
skin_tone_pattern = re.compile('[🏼🏾🏽🏿🏻]')

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("-locales", type=str, default=None, help="Comma-separated list of locales to limit to")
arg_parser.add_argument("-downloadOnlyTo", type=str, default=None,
                        help="Download files to provided directory only, don't create dictionaries")
arg_parser.add_argument("-readFromDir", type=str, default=None,
                        help="Read files from provided directory, don't download")
arg_parser.add_argument("-wordlistDir", type=str, default='../emoji_cldr_signal_wordlists',
                        help="Directory to save wordlist files to")
arg_parser.add_argument("-dictDir", type=str, default='../emoji_cldr_signal_dictionaries',
                        help="Directory to save dictionary files to")
arg_parser.add_argument("-recreate", action="store_true", help="Overwrites already existing dictionaries")
args = arg_parser.parse_args()
if args.downloadOnlyTo and args.readFromDir:
    print('-downloadOnlyTo and -readFromDir are mutually exclusive')
    exit(-1)

# TODO: make it work without requiring args here
if not args.readFromDir:
    connection = http.client.HTTPSConnection("raw.githubusercontent.com", timeout=30)
readFromDir = args.readFromDir
downloadOnlyTo = args.downloadOnlyTo
current_locale = None
all_locales = None


def load_or_save(path):
    if readFromDir:
        path = readFromDir + path
        if not os.path.exists(path):
            return {}

        with (open(path, 'rb') as f):
            return json.loads(f.read())

    try:
        connection.request("GET", path)
        response = connection.getresponse()
        if response.status >= 400:
            return {}

        if not downloadOnlyTo:
            return json.loads(response.read())

        path = downloadOnlyTo + path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with (open(path, 'wb') as f):
            f.write(response.read())

        return {}
    finally:
        connection.close()


@cache
def get_signal_ranks():
    signal_en_ranks = {}
    for emo_data in load_or_save("/signalapp/emoji-search-index/refs/heads/main/data/en.json"):
        signal_en_ranks[emo_data["emoji"]] = emo_data["rank"]
    if downloadOnlyTo:
        return signal_en_ranks, 1
    max_signal_rank = max(signal_en_ranks.values())
    return signal_en_ranks, max_signal_rank


def get_cldr_data(path, key):
    data = load_or_save(path)
    if not data:
        return {}

    ann = data[key]
    if "annotations" not in ann:
        return {}

    return ann["annotations"]


def get_words(entries):
    global current_locale
    words = set()
    for word in entries:
        new_words = re.sub(comma_pattern, "", word).split(' ')
        if len(new_words) > TOP_WORD_IGNORE_LENGTH:
            for top_word in get_top_dict_words(current_locale):
                if top_word in new_words:
                    new_words.remove(top_word)
        words.update(new_words)

    return words


def update_dict(emoji_char, words, rank, emo_dict):
    for word in words:
        if word:
            entry = emo_dict.get(word, {})
            entry[emoji_char] = rank
            emo_dict[word] = entry


def get_cldr_dict(ann):
    emo_dict = {}
    signal_en_ranks, max_signal_rank = get_signal_ranks()
    for emoji_char, emo_data in ann.items():
        if "default" not in emo_data:
            continue

        if not emoji.is_emoji(emoji_char) or re.search(skin_tone_pattern, emoji_char):
            continue

        words = get_words(emo_data["default"])
        if "tts" in emo_data:
            words.update(get_words(emo_data["tts"]))

        emoji_char = emoji.emojize(emoji.demojize(emoji_char))
        rank = signal_en_ranks[emoji_char] if emoji_char in signal_en_ranks else CLDR_RANK
        update_dict(emoji_char, words, rank, emo_dict)

    return emo_dict


def get_signal_dict(path):
    emo_dict = {}
    signal_en_ranks, max_signal_rank = get_signal_ranks()
    for emo_data in load_or_save(path):
        rank = emo_data["rank"] if "rank" in emo_data else signal_en_ranks[emo_data["emoji"]]
        update_dict(emo_data["emoji"], get_words(emo_data["tags"]), rank, emo_dict)

    return emo_dict


# dict2 overwrites dict1 for same word,emoji combos
def merge_dicts(dict1, dict2):
    res = dict1 | dict2
    for word, emojis in dict1.items():
        if word in dict2:
            res[word] = emojis | dict2[word]

    return res


def get_descriptions(ann):
    descriptions = {}
    for emoji_char, emo_data in ann.items():
        if "tts" not in emo_data:
            continue

        if not emoji.is_emoji(emoji_char):
            continue

        descriptions[emoji.emojize(emoji.demojize(emoji_char))] = {
            re.sub(comma_pattern, "", emo_data["tts"][0]): DESCRIPTION_RANK
        }

    return descriptions


def get_dict(locale):
    ann = get_cldr_data("/unicode-org/cldr-json/refs/heads/main/cldr-json/cldr-annotations-full"
                        f"/annotations/{locale}/annotations.json", "annotations")
    annDerived = get_cldr_data("/unicode-org/cldr-json/refs/heads/main/cldr-json/cldr-annotations-derived-full"
                               f"/annotationsDerived/{locale}/annotations.json", "annotationsDerived")
    signal_dict = get_signal_dict(f"/signalapp/emoji-search-index/refs/heads/main/data/{locale}.json")
    emo_dict = (merge_dicts(merge_dicts(get_cldr_dict(ann), get_cldr_dict(annDerived)), signal_dict)
                | get_descriptions(ann) | get_descriptions(annDerived))
    return emo_dict


def get_frequency(rank):
    signal_en_ranks, max_signal_rank = get_signal_ranks()
    return DESCRIPTION_FREQUENCY if rank == DESCRIPTION_RANK \
            else int(MAX_FREQUENCY - rank * MAX_FREQUENCY / max_signal_rank)


# words where we should not show any emoji
# this is because they are 100% matches with very common words, and due to the way AOSP suggestion scores work,
# they will get a very high score and usually display in first place
# further, top words often are rather generic and bad matches for emojis anyway (and, with, in, for, ...)
@cache
def get_top_dict_words(aosp_locale):
    if aosp_locale == "en":
        aosp_locale = "en_US"  # we don't have a generic English dictionary
    wordlist = f"../wordlists/main_{aosp_locale}.combined"
    if not os.path.isfile(wordlist) and "_" in aosp_locale and "ZZ" not in locale:
        loc = aosp_locale.split["_"][0]
        wordlist = f"../wordlists/main_{loc}.combined"  # try language without country
    if not os.path.isfile(wordlist):
        print(f"no wordlist for {aosp_locale} found")
        return []
    top_words = []
    with open(wordlist) as f:
        for line in f.readlines():
            line = line.strip()
            if not line.startswith("word="):
                continue
            word = line.split("word=")[1].split(",")[0]
            top_words.append(word)
            if len(top_words) > TOP_WORDS_LIMIT:
                break
    return top_words


def make_wordlist(language_tag, language_name, target_dir, force_create):
    global current_locale
    global all_locales
    current_locale = language_tag
    aosp_locale = language_tag.replace("-Latn", "_ZZ").replace("-", "_")  # AOSP dicts don't use language tags
    file_name = f"{target_dir}/emoji_{aosp_locale}.combined"
    if not force_create and os.path.isfile(file_name):
        print(f"dict for {language_tag} already exists, skipping")
        return

    emo_dict = get_dict(language_tag)
    if not emo_dict:
        print(f"no dict created for {language_tag}")
        return

    locale_split = language_tag.split('-')
    if len(locale_split) > 1 and locale_split[0] in all_locales.keys() and "-Latn" not in language_tag:
        emo_dict = merge_dicts(get_dict(locale_split[0]), emo_dict)

    # now write
    print(f"Locale {language_name} ({language_tag}):")
    with (open(file_name, 'w', encoding="utf-8") as f):
        now = int(time.time())
        f.write(f"dictionary=emoji:{aosp_locale.lower()},description=Emoji for {language_name} words,locale={aosp_locale},date={now},version={VERSION}\n")
        for word, shortcuts in sorted(emo_dict.items()):
            if word in BAD_WORDS:
                continue

            if len(shortcuts) > MAX_POPULARITY:
                print(f"Dropping too popular word: {word} ({len(shortcuts)})")
                continue

            if len(word) > 47:
                # dicttool_aosp drops words longer than this
                print(f"Trimming too long word: {word} ({len(word)})")
                word = word[:47]

            f.write(f" word={word},f={get_frequency(sum(shortcuts.values()) / len(shortcuts))},not_a_word=true\n")
            for shortcut, rank in sorted(shortcuts.items(), key=lambda item: item[1])[:MAX_SHORTCUTS]:
                f.write(f"  shortcut={shortcut},f={get_frequency(rank)}\n")

    #os.system(f"java -jar dicttool_aosp.jar makedict -s {file_name} -d {args.dictDir}/emoji_{locale}.dict")


def main():
    languages_path = "/unicode-org/cldr-json/refs/heads/main/cldr-json/cldr-localenames-full/main/en/languages.json"
    data = load_or_save(languages_path)
    if args.downloadOnlyTo:
        # need to read again
        connection.request("GET", languages_path)
        data = json.loads(connection.getresponse().read())
        connection.close()

    global all_locales
    all_locales = data["main"]["en"]["localeDisplayNames"]["languages"]
    locales = args.locales

    for locale, name in all_locales.items():
        if locales and locale not in locales:
            continue
        make_wordlist(locale, name, args.wordlistDir, args.recreate)


if __name__ == "__main__":
    main()
