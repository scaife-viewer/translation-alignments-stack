# refs https://github.com/scaife-viewer/beyond-translation-site/commit/d760dd87bb97ea53b8c443f750c22ed7fe5c02bf
from pathlib import Path

import conllu
import tqdm
from thefuzz import process


VERSION_URN = "urn:cts:latinLit:phi0428.phi001.dll-ed-lat1:"


def main():
    text_path = Path("data/library/phi0428/phi001/phi0428.phi001.dll-ed-lat1.txt")
    treebank_path = Path("data/raw/bellum-boano/BellumAlexandrinumTagged_mod.conllu")

    ref_to_text = {}
    for l in text_path.read_text().splitlines():
        ref, rest = l.split(maxsplit=1)
        ref_to_text[ref] = rest

    sent_to_text = {}
    data = conllu.parse(treebank_path.read_text())
    for r in data:
        sent_to_text[r.metadata["sent_id"]] = r.metadata["text"]

    for r in tqdm.tqdm(data):
        needle = r.metadata["text"]
        # NOTE: This may require manual corrections
        result = process.extractOne(needle, ref_to_text)
        if result:
            r.metadata["references"] = "|".join([f"{VERSION_URN}{result[-1]}"])
        else:
            print("No result found")

    with treebank_path.open("w") as f:
        for row in data:
            f.write(row.serialize())
