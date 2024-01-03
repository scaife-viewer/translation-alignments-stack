import json
import os
import re
import time
from collections import defaultdict
from pathlib import Path

import more_itertools
from lxml import etree


TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}
TI_NS = {"ti": "http://chs.harvard.edu/xmlns/cts"}

# NOTE: These regexes were backported from MyCapytain
# refs https://github.com/Capitains/MyCapytain/blob/1524ec07377ed587750cb0ec8fd0f97f0ad8d81c/LICENSE.txt
REFSDECL_SPLITTER = re.compile(r"/+[*()|\sa-zA-Z0-9:\[\]@=\\{$'\".\s]+")
REFSDECL_REPLACER = re.compile(r"\$[0-9]+")
SUBREFERENCE = re.compile(r"(\w*)\[?([0-9]*)\]?", re.UNICODE)
REFERENCE_REPLACER = re.compile(r"(@[a-zA-Z0-9:]+)(=)([\\$'\"?0-9]{3,6})")
PDL_CONTENT_ROOT = Path(
    os.environ.get("PDL_CONTENT_ROOT", "../../scaife-viewer/data/cts")
)
# FIXME: Remove hard-coded SHA from path name
GREEK_LIT_ROOT = (
    PDL_CONTENT_ROOT / "PerseusDL-canonical-greekLit-0.0.4176122695-7070a1d/data"
)


def get_processors():
    return {
        "card": {
            "refs": refs_for_cards,
            "tail": tail_for_cards,
        },
        "para": {
            "refs": refs_for_paras,
            "tail": tail_for_paras,
        },
    }


def get_paths():
    # FIXME: Generalize for all PDL content

    return [
        GREEK_LIT_ROOT / "tlg0012/tlg001/tlg0012.tlg001.perseus-grc2.xml",
        GREEK_LIT_ROOT / "tlg0012/tlg002/tlg0012.tlg002.perseus-grc2.xml",
        GREEK_LIT_ROOT / "tlg0011/tlg002/tlg0011.tlg002.perseus-grc2.xml",
        GREEK_LIT_ROOT / "tlg0032/tlg006/tlg0032.tlg006.perseus-grc2.xml",
    ]


def get_reference(milestone, citation_scheme, xpath_axis, citation_selector):
    """
    Retrieve a CTS reference for a milestone

    Functionality backported from MyCapytain
    """
    parts = []
    citations = iter(citation_scheme)
    citation = next(citations, None)
    xpath = citation["xpath"]
    resolved_xpath = citation["xpath"].strip("/").replace("='?'", "")
    compiled_xpath = f"./{xpath_axis}::{resolved_xpath}[{citation_selector}]"
    citation_elem = milestone.xpath(
        compiled_xpath,
        namespaces=TEI_NS,
    )[0]
    parts.append(citation_elem.attrib["n"])
    parent = next(citations, None)
    while parent:
        xpath = parent["xpath"]
        parent_elem = citation_elem.xpath(
            "".join(
                ["./ancestor::", xpath.strip("/").replace("='?'", ""), "[position()=1]"]
            ),
            namespaces=TEI_NS,
        )[0]
        parts.append(parent_elem.attrib["n"])
        parent = next(citations, None)
        citation_elem = parent_elem
    assert len(parts) == len(citation_scheme)
    return ".".join(reversed(parts))


def get_next_reference(milestone, citation_scheme):
    """
    Get the next reference for a milestone
    """
    return get_reference(milestone, citation_scheme)


def get_previous_reference(milestone, citation_scheme):
    """
    Get the previous reference for a milestone
    """
    return get_reference(milestone, citation_scheme, direction="previous")


# TODO: Refactor with CTS metadata
def get_work_title(path):
    parent = path.parent
    cts_header_path = next(parent.glob("__cts__.xml"), None)
    assert cts_header_path is not None
    header_parsed = etree.parse(cts_header_path)
    return header_parsed.find("ti:title", namespaces=TI_NS).text


# TODO: Refactor with CTS metadata
def get_work_slug(path):
    return get_work_title(path).lower()


def get_citation_scheme(parsed):
    """
    Extract citation scheme from a TEI XML version

    Functionality backported from MyCapytain.
    """
    citation_lu = {}
    refs_decls = parsed.xpath("//tei:refsDecl[@n='CTS']", namespaces=TEI_NS)
    for decl in refs_decls:
        for cref in decl.xpath("./tei:cRefPattern", namespaces=TEI_NS):
            key = cref.attrib["n"]
            refs_decl = cref.attrib.get("replacementPattern")[7:-1]
            matches = REFSDECL_SPLITTER.findall(refs_decl)
            scope = REFSDECL_REPLACER.sub("?", "".join(matches[0:-1]))
            xpath = REFSDECL_REPLACER.sub("?", matches[-1])
            resolved_xpath = REFERENCE_REPLACER.sub(r"\1", refs_decl)
            citation_lu[key] = dict(
                kind=key,
                refs_decl=refs_decl,
                scope=scope,
                xpath=xpath,
                resolved_xpath=resolved_xpath,
            )
    return list(citation_lu.values())


def refs_for_paras(lookup, pos, milestone, citation_scheme):
    try:
        ref = get_reference(milestone, citation_scheme, "ancestor", "position() = 1")
    except IndexError:
        return
    else:
        lookup[pos].append(ref)

    try:
        next_ref = get_reference(
            milestone, citation_scheme, "preceding", "position() = 1"
        )
    except Exception as excep:
        if pos == 0 and isinstance(excep, IndexError):
            return
        raise excep
    else:
        lookup[pos - 1].append(next_ref)


def tail_for_paras(lookup, pos, milestone, citation_scheme):
    try:
        ref = get_reference(milestone, citation_scheme, "ancestor", "last()")
    except IndexError:
        ref = get_reference(milestone, citation_scheme, "following", "last()")
    if lookup[pos][-1] != ref:
        lookup[pos].append(ref)
    return pos


def refs_for_cards(lookup, pos, milestone, citation_scheme):
    try:
        ref = get_reference(milestone, citation_scheme, "following", "position() = 1")
    except IndexError:
        return
    else:
        lookup[pos].append(ref)

    try:
        next_ref = get_reference(
            milestone, citation_scheme, "preceding", "position() = 1"
        )
    except Exception as excep:
        if pos == 0 and isinstance(excep, IndexError):
            return
        raise excep
    else:
        lookup[pos - 1].append(next_ref)


def tail_for_cards(lookup, pos, milestone, citation_scheme):
    last_pos = None
    try:
        ref = get_reference(milestone, citation_scheme, "following", "last()")
        if lookup[pos][-1] != ref:
            lookup[pos].append(ref)
        return pos
    except IndexError:
        pass
    return last_pos


def extract_toc_entries(parsed, version_urn, citation_scheme, milestone_unit):
    """
    Extract TOC entries for each milestone
    """
    lookup = defaultdict(list)
    milestones = parsed.xpath(
        # f"//tei:milestone[@unit='{milestone_unit}']",
        f"//tei:milestone[translate(@unit, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='{milestone_unit}']",
        namespaces=TEI_NS,
    )
    processors = get_processors()[milestone_unit]
    for pos, milestone in enumerate(milestones):
        processors["refs"](lookup, pos, milestone, citation_scheme)

    # this appends the last reference
    last_pos = processors["tail"](lookup, pos, milestone, citation_scheme)
    entries = []
    plural_label = citation_scheme[0]["kind"] + "s"
    for pos, entry in lookup.items():
        refs = "-".join(entry)
        title = f"{plural_label} {refs}"
        if pos == last_pos:
            # this is the last entry
            title = f"{plural_label} {entry[0]}ff."
        toc = dict(title=title, uri=f"{version_urn}:{refs}")
        entries.append(toc)
    return entries


def regroup_entries(toc_slug, citation_scheme, all_tocs):
    """
    Regroup entries by their parent
    """
    # FIXME: Assumes a single parent
    regrouped_tocs = []
    parent_predicate = (
        lambda x: x["uri"].rsplit(":", maxsplit=1)[1].split(".")[0]
    )  # noqa: E731
    tocs_by_parent = more_itertools.bucket(all_tocs, key=parent_predicate)
    parent_label = citation_scheme[-1]["kind"].title()
    # FIXME: slugify URN; we may have this from CTS
    for entry in tocs_by_parent:
        urnish = f"toc.{toc_slug}-{entry}"
        book_entries = tocs_by_parent[entry]
        root_entry = {
            "title": "↵",
            "uri": f"urn:cite:scaife-viewer:toc.{toc_slug}",
        }
        data = {
            "@id": f"urn:cite:scaife-viewer:{urnish}",
            "title": f"{parent_label} {entry}",
            "uri": f"urn:cite:scaife-viewer:{urnish}",
            # TODO: Distinguish between entry title and TOC title
            # "title": f"Folios for Iliad {book}",
            "items": [root_entry] + list(book_entries),
        }
        regrouped_tocs.append(data)
    return regrouped_tocs


def write_toc(work_title, toc_slug, citation_scheme, milestone_unit, regrouped_tocs):
    """
    Write TOC annotation to disk
    """
    milestone_unit_label_plural = f"{milestone_unit}s".title()
    citation_scheme_string = " / ".join(
        f'{citation["kind"]}s' for citation in reversed(citation_scheme)
    )
    data = {
        "@id": f"urn:cite:scaife-viewer:toc.{toc_slug}",
        "title": f"{work_title} ({milestone_unit_label_plural})",
        "description": f"Mapping of {milestone_unit_label_plural.lower()} to {citation_scheme_string}",
        "items": regrouped_tocs,
    }

    # FIXME: Assumes PerseusDL
    toc_path = Path(f"data/annotations/tocs/PerseusDL/toc.{toc_slug}.json")
    toc_path.parent.mkdir(exist_ok=True, parents=True)
    with toc_path.open("w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {toc_path.name}")


def create_milestone_toc(path, parsed, version_urn, citation_scheme, milestone_unit):
    """
    Create a TOC for a given version + milestone unit
    """
    work_title = get_work_title(path)
    milestone_unit_slug = f"{milestone_unit}s".lower()
    toc_slug = f"{get_work_slug(path)}-{milestone_unit_slug}"

    toc_entries = extract_toc_entries(
        parsed, version_urn, citation_scheme, milestone_unit
    )
    # FIXME: Support regrouping at muiltiple levels
    if len(citation_scheme) > 1:
        regrouped_entries = regroup_entries(toc_slug, citation_scheme, toc_entries)
    else:
        regrouped_entries = toc_entries
    write_toc(work_title, toc_slug, citation_scheme, milestone_unit, regrouped_entries)


def get_milestone_kinds(parsed):
    """
    Get unique milestone kinds in the provided XML
    """
    # FIXME: Make this check more efficient
    milestones = parsed.xpath("//tei:milestone[@unit]", namespaces=TEI_NS)
    # FIXME: Hard-coded to `card`; "Para" worked for Iliad but not Odyssey
    # return set([ms.attrib["unit"] for ms in milestones])
    return set([ms.attrib["unit"].lower() for ms in milestones])


def process_path(path):
    """
    Create TOCs for the provided path
    """
    parsed = etree.parse(path)
    version_urn = parsed.xpath("//tei:div[position()=1]", namespaces=TEI_NS)[
        0
    ].attrib.get("n")
    citation_scheme = get_citation_scheme(parsed)

    for milestone_unit in get_milestone_kinds(parsed):
        create_milestone_toc(path, parsed, version_urn, citation_scheme, milestone_unit)


def main():
    """
    Create TOCs
    """
    paths = get_paths()
    for path in paths:
        print(f"Processing {path.name}")
        process_path(path)


if __name__ == "__main__":
    start = time.time()
    main()
    end = time.time()
    print(end - start)
