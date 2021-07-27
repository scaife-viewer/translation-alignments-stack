import json
import os

from scaife_viewer.atlas.backports.scaife_viewer.cts.utils import natural_keys
from scaife_viewer.atlas.conf import settings
from scaife_viewer.atlas.importers.token_annotations import apply_token_annotations
from scaife_viewer.atlas.models import (
    Node,
    TextAlignment,
    TextAlignmentRecord,
    TextAlignmentRecordRelation,
    Token,
)
from scaife_viewer.atlas.urn import URN


ANNOTATIONS_DATA_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR, "annotations", "text-alignments"
)


def get_paths():
    if not os.path.exists(ANNOTATIONS_DATA_PATH):
        return []
    return [
        os.path.join(ANNOTATIONS_DATA_PATH, f)
        for f in os.listdir(ANNOTATIONS_DATA_PATH)
        if f.endswith(".json")
    ]


def process_file(path):
    data = json.load(open(path))

    versions = data["versions"]
    version_objs = []
    for version in versions:
        version_objs.append(Node.objects.get(urn=version))

    alignment = TextAlignment(label=data["label"], urn=data["urn"],)
    alignment.save()
    alignment.versions.set(version_objs)

    idx = 0
    # TODO: review how we might make use of sort key from CEX
    # TODO: sorting versions from Ducat too, especially since Ducat doesn't have 'em
    # maybe something for CITE tools?
    for row in data["records"]:
        record = TextAlignmentRecord(idx=idx, alignment=alignment, urn=row["urn"])
        record.save()
        idx += 1
        for version_obj, relation in zip(version_objs, row["relations"]):
            relation_obj = TextAlignmentRecordRelation(
                version=version_obj, record=record
            )
            relation_obj.save()
            tokens = []
            # TODO: Can we build up a veref map and validate?
            for entry in relation:
                entry_urn = URN(entry)
                ref = entry_urn.passage
                # NOTE: this assumes we're always dealing with a tokenized exemplar, which
                # may not be the case
                text_part_ref, _ = ref.rsplit(".", maxsplit=1)
                text_part_urn = f"{version_obj.urn}{text_part_ref}"
                # TODO: compound Q objects query to minimize round trips
                tokens.append(
                    Token.objects.get(text_part__urn=text_part_urn, ve_ref=ref)
                )
            relation_obj.tokens.set(tokens)


def process_alignments(reset=False):
    if reset:
        TextAlignment.objects.all().delete()

    created_count = 0
    for path in get_paths():
        process_file(path)
        created_count += 1
    print(f"Alignments created: {created_count}")


def load_token_annotations(reset=False):
    apply_token_annotations()
