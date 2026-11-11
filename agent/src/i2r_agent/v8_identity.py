"""Binding identities exclude only known non-binding Rust inline hints."""
from copy import deepcopy
import re
from .segmented_contract import interfaces


def interfaces_for_cache(files):
    result=deepcopy(interfaces(files))
    for rows in result.values():
        for row in rows:
            if row['kind']=='function_item':
                row['attributes']=[a for a in row['attributes'] if not re.fullmatch(
                    r'#\s*\[\s*inline\s*(?:\(\s*(?:always|never)\s*\))?\s*\]',a)]
    return result


VERIFIED_STATE_FIELDS = ('whole_review_version',
                         'support_evidence', 'connector_notes',
                         'static_feedback', 'decisions', 'numeric_representation',
                         'source_reviews', 'dirty_sources')
