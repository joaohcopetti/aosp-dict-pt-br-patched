#!/bin/python
import sys
import os
import time
import langcodes
import pathlib
from wordlist_combined import DictionaryHeader, WordlistCombined

# this script generates source entries for the readme from .source files
# source file format:
#  license: <license (optional)>
#  language: <language in English (optional, e.g. for toki pona)>
#  source: <link / text>

# note that this script assumes it is run from scripts directory

# this is to directly link to the dictionary files
# leave it empty for linking to codeberg pages instead (but independent of repository!)
dict_prefix = "https://codeberg.org/Helium314/aosp-dictionaries/raw/branch/main/"


def get_source_file_names(folder: str) -> list[str]:
    files = []
    folder = os.path.join(os.path.dirname(__file__), "..", folder)
    if not os.path.isdir(folder):
        sys.exit(f"{folder} is not a directory")
    for (dirpath, dirnames, filenames) in os.walk(folder):
        for name in filenames:
            file = os.path.join(folder, name)
            if not file.endswith(".combined"):
                continue
            if "sample." in file:
                continue
            source_file = file.replace("combined", "source")
            if not os.path.isfile(source_file) and "emoji_cldr_signal_wordlists" not in folder:
                sys.exit(f"{source_file} not found")
            files.append(file)
    return files


def create_dict_if_not_exists(dict_path: str, word_list_path: str) -> None:
    if os.path.isfile(dict_path):
        return
    word_list = WordlistCombined.read_from_file(word_list_path)
    word_list.compile(dict_path)


def get_infos(folder: str) -> list[dict]:
    files = get_source_file_names(folder)
    infos = []
    experimental = "yes" if "experimental" in folder else "no"
    for file in files:
        if "emoji_cldr_signal" in file:
            source_info = {"source_link": "emoji_cldr_signal_wordlists/emoji_cldr_signal.source"}
            source_file = "/".join(file.split("/")[:-1]) + "/emoji_cldr_signal.source"
        else:
            source_file = file.replace(".combined", ".source")
            source_info = {"source_link": "/".join(source_file.split("/")[-2:])}
        filepath = pathlib.Path(file)
        dict_path_relative = filepath.parent.name.replace("wordlists", "dictionaries") + "/" + filepath.stem.lower() + ".dict"
        print("processing", dict_path_relative)
        create_dict_if_not_exists(filepath.parent.parent.name + "/" + dict_path_relative, file)
        source_info["dictfile"] = dict_path_relative
        with open(filepath, 'rt') as f:
            header = DictionaryHeader.parse(f.readline())
            if header is None:
                sys.exit(f"could not parse header for {file}")
            source_info["header"] = header
            wordcount = 0
            for line in f:
                if line.lstrip().startswith("word="):
                    wordcount += 1
            source_info["wordcount"] = wordcount
            for line in f:
                if line.lstrip().startswith("bigram="):
                    source_info["bigrams"] = True
                    break
        with open(source_file) as f:
            for line in f:
                if line.isspace():
                    continue
                (name, value) = line.split(":", 1)
                value = value.strip()
                name = name.strip()
                if len(value) == 0:
                    continue
                source_info[name] = value
            if "source" not in source_info:
                sys.exit(f"no source given in {file}, source info: {source_info}")
        source_info["experimental"] = experimental
        infos.append(source_info)
    return infos


def info_to_text(info: dict) -> str:
    header: DictionaryHeader = info["header"]
    language = info.get("language", langcodes.Language.get(header.locale).display_name('en'))
    dictfile = info["dictfile"]
    description = ""
    if len(header.description.strip()) > 0:
        description = f"{header.description}, "
    timestring = time.strftime('%Y-%m-%d', time.localtime(header.date))
    wordcount = info["wordcount"]
    bigrams = "no"
    if info.get("bigrams", False):
        bigrams = "yes"
    source = info["source"]
    source_link = "[source](" + info["source_link"] + ")"
    if header.type == "emoji" and "cldr_signal" not in source_link:
        language += " (legacy)"
    dict_license = ""
    if "license" in info:
        dict_license = ", " + info["license"]
    experimental = info["experimental"]
    return f"| {language} | [{header.type}]({dict_prefix}{dictfile}) | {experimental} | {bigrams} | {wordcount} | {timestring} | {source_link}{dict_license} |"


def main():
    readmefile = os.path.join(os.path.dirname(__file__), "..", "README.md")
    outlines = []
    with open(readmefile) as f:
        skiptables = False
        for line in f:
            if skiptables:
                if line.startswith("| "):
                    continue
                else:
                    skiptables = False
            if line == "# Dictionaries\n":
                outlines.append(line)
                skiptables = True
                infolines = []
                for info in get_infos("wordlists"):
                    infolines.append(info_to_text(info) + "\n")
                for info in get_infos("wordlists_experimental"):
                    infolines.append(info_to_text(info) + "\n")
                for info in get_infos("emoji_cldr_signal_wordlists"):
                    infolines.append(info_to_text(info) + "\n")
                infolines.sort()
                outlines.append("| Language | Type | Experimental | Next-Word Data | Words | Updated | Source |\n")
                outlines.append("| --- | --- | --- | --- | --- | --- | --- |\n")
                outlines += infolines
            else:
                outlines.append(line)
    with open(readmefile, 'w') as f:
        f.writelines(outlines)


if __name__ == "__main__":
    main()
