#!/bin/python
import os
from wordlist_combined import WordlistCombined, DictionaryHeader
from wordlist import Wordlist
from spylls.hunspell import Dictionary

# maybe useful
# https://wortschatz.uni-leipzig.de/en/download/
#  really useful source of sentences / fragments, but should be checked against dictionaries as they are taken from news / web
# https://en.wiktionary.org/wiki/Wiktionary:Frequency_lists
#  word frequency lists linked, in some cases there are also sentence lists
# https://github.com/wooorm/dictionaries
#  hunspell dicts, are they the same as the one included in phunspell?

# required modules:
#  os, gzip, shutil, tempfile, time, math, regex
#  spylls for dictionary
#  optionally phunspell for finding hunspell dictionaries by locale


# example with all optional things, can run on the repo as is (if writable and on unix)
def example_and_description():
    locale = "en"
    w = Wordlist(
        locale,  # try to find dictionary for "en", may fail
        # alternatively provide the dictionary directory, see example below
        # Dictionary.from_files("/home/user/.local/lib/python3.10/site-packages/phunspell/data/dictionary/en/en_US"),
        {"i"}  # ignore the word "i", which is spylls/hunspell sees as valid word
    )

    # performance is not good ca 1 - 30 min for a 1M sentence list (wortschatz.uni-leipzig.de), depending on language,
    # mostly limited by spylls lookup
    w.add_sentence_file("../LICENSE",
                        add_unknown_words=False)  # will add all words, except if starting with upper case if it's the first word in line or sentence
                        # add_unknown_words = True)  # will only add words that pass the spell check

    # will add all words from README.md separately (no bigrams)
    # without spell check, but with count (used for word frequencies)
    w.add_word_file("../README.md")

    # add all valid words from dictionary to the wordlist (with count 1)
    # note that this can take a long time, and generate huge lists for some locales (hours and hundreds of MB in some
    # cases, e.g. for it_IT)
    # also note that this still may not create all valid words, as in some languages words can be joined to get new
    # valid words (e.g. de_DE)
    # memory usage depends on word lists and language, expect 0.5 - 2 GB (it_IT requires 4 GB and takes hours)
    w.add_words_from_dictionary(
        dict_word_cache_file=f"../dict_cache_{locale}.txt"  # optionally store extracted dictionary words in a file
    )
    combined = w.create_wordlist_combined(
        add_nosuggest=True,  # will add "possibly_offensive" to words flagged as "nosuggest" by spylls/hunspell
        add_bigrams=True,  # will add all bigrams in list, with f increasing for decreasing count (similar to en_US AOSP dictionary)
        # without a valid header, the dictionary will not compile (can be added to combined later)
        # we use "test" as dictionary type, typically it will be main, but can be anything for addon dictionaries
        # note that only one dictionary per type can be used for a given locale
        header=DictionaryHeader(locale, "test", " ", 1)
    )

    # read wordlist from file
    en_us_combined = WordlistCombined.read_from_file("../wordlists/main_en_US.combined")
    # and merge it into the current word list
    combined.merge_list(source=en_us_combined.words,
                        words=True,  # add new words to combined
                        f="keep",  # "keep" f, "overwrite" with source f, or "average" current and source f
                        possibly_offensive=True,  # add "possibly_offensive" attribute to combined (only if true)
                        not_a_word=True,  # add "not_a_word" attribute to combined (only if true)
                        shortcuts=True,  # add shortcuts to combined (overwrite if same shortcut exists with different f)
                        bigrams=True,  # add bigrams to combined (overwrite if same bigram exists with different f)
                        other=True  # add other (unknown) attributes to combined (overwrite if same attribute exists with different value)
                        )

    combined.filter_bigrams(
        max_bigram_count=3,  # keep at maximum 3 bigrams
        max_f=200)  # remove all bigrams where the word has f > 200
                    # removing high frequency words reduces the number of very common next words (to, the, a, in, ...)

    combined.write_to_file("../LICENSE.combined")  # write wordlist file (if ends in ".gz" it will be compressed)
    combined.compile("../")  # create a .dict file in the specified folder, determine file name from DictionaryHeader
#    combined.compile("../main.dict")  # create a .dict file


if __name__ == "__main__":
    example_and_description()


# use existing dictionary for spell check (from phunspell)
# use sentence list to build word list
# cpmpile word list
def example_1():
    d = Dictionary.from_files("/home/user/.local/lib/python3.10/site-packages/phunspell/data/dictionary/en/en_US")
    w = wordlist(dictionary=d)
    w.add_sentence_file("../LICENSE",
                        add_unknown_words=False)  # will only add words that pass the spell check
    c = w.create_wordlist_combined()
    c.header = DictionaryHeader("en_US", "main", "english word list", 18)
    c.write_to_file("/home/user/en_US_wordlist.compiled")
    c.compile("/home/user/en_us.dict")


# use existing dictionary for spell check
# use words from affix-expanded ("unmunched") dictionary, creates a much larger wordlist in some languages
# use sentence list to build word list
#  this is mostly for frequencies and next words, but may also add new words in some languages, e.g. German compund words
def example_2():
    d = Dictionary.from_files("/home/user/.local/lib/python3.10/site-packages/phunspell/data/dictionary/en/en_US")
    w = wordlist(dictionary=d)
    # unmunched cache not necessary for english, but helps for e.g. german, czech or italian
    w.add_unmunched_dictionary(unmunched_cache="/home/user/en_unmunched.txt")  # adds all words with count 1
    w.add_sentence_file("/home/user/eng_news_2020_100K-sentences.txt", add_unknown_words=False)
    c = w.create_wordlist_combined(header=DictionaryHeader("en_US", "main", "english word list", 18))
    c.write_to_file("/home/user/en_US_wordlist.compiled")


# don't use a dictionary, only a word list
# this will produce low-quality suggestions, as word count is how often the words occur in the file (likely only once)
def example_3():
    w = wordlist()
    w.add_word_file("/home/user/some_word_list.txt")
    c = w.create_wordlist_combined()
    c.write_to_file("/home/user/wordlist.compiled")  # this file will not compile, as we didn't set a header


# don't use a dictionary, but provide a word list
# use a sentence file for word count and next word suggestions
def example_4():
    w = wordlist()
    w.add_word_file("/home/user/some_word_list.txt")
    w.add_sentence_file("/home/user/eng_news_2020_100K-sentences.txt", add_unknown_words=False)
    c = w.create_wordlist_combined(header=DictionaryHeader("en_US", "main", "english word list", 18))
    c.write_to_file("/home/user/wordlist.compiled")  # this file will not compile, as we didn't set a header


# don't use a dictionary, but a list of sentences
# android word list may contain spelling errors depending on source of the sentences
def example_5():
    w = wordlist(ignore_words={"i"})  # ignore the word "i", it's a common typo that should not get added (may be correct use e.g. of imaginary unit)
    w.add_sentence_file("/home/user/eng_news_2020_100K/eng_news_2020_100K-sentences.txt",
                        add_unknown_words=True)  # add all words to the word list, except some obvious non-words
    c = w.create_wordlist_combined(header=DictionaryHeader("en_US", "main"))
    c.write_to_file("/home/user/wordlist.compiled")  # this file will not compile, as we didn't set a header
