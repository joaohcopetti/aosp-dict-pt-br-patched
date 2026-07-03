# Grammar fixes for latest Brazilian Portuguese AOSP dictionary
This script uses Hunspell to correct grammar errors from original AOSP dictionary (which has many words still using the old grammar rules), keeping the word frequency unchanged.

It adds some extra checks to ensure only the grammatically wrong words are corrected, leaving the rest untouched.

There's three files in `./logs` dir with the results of the script:
- corrected_words.txt: A list of the words that got corrected and replaced
- ignored_correct_word.txt: Words that got ignored because they were in the list already
- ignored_suggestions.txt: Hunspell suggestions that didn't get applied because didn't pass the checks
- results.txt: Show general results

Those files are important so we can spot possible logical errors and improve the script logic when necessary.

## Download
You can download the `.dict` file [here](https://github.com/joaohcopetti/aosp-dict-pt-br-patched/releases/download/v1/main_pt_BR.dict)

## Run the script
The main code is located on `src/main.py`. It uses [uv](https://docs.astral.sh/uv/) as package manager:

- Inside the `src` folder run:
  - `uv venv`
  - `uv pip install -e .`
- Then `uv run main.py`
- It'll use the latest AOSP dictionary (from 2014) as reference, located in `./pt_BT_wordlist.combined`.
- After finishing, it'll create a new combined file in `./pt_BR_wordlist_patched.combined`.
- Use `dicttool_aosp.jar` to compile into a `.dict` file, it requires Java.
- `java -jar dicttool_aosp.jar makedict -s pt_BR_wordlist_patched.combined -d main_pt_BR.dict`
- It'll create a new `main_pt_BR.dict` file in a root of the project.

## Credits
- Helium314 tools: https://codeberg.org/Helium314/aosp-dictionaries/src/branch/main/scripts
- `dicttool_aosp.jar` tool: https://github.com/remi0s/aosp-dictionary-tools
- Hunspell PT-BR dictionary: https://github.com/wooorm/dictionaries
- AOSP latest PT-BR dictionary (2014): https://github.com/openboard-team/openboard/blob/v1.4.5/dictionaries/pt_BR_wordlist.combined.gz
