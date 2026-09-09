import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from study_wiki.common import (TAXONOMY, TAXONOMY_PATH, alias_map, classify,
                                normalize, register_taxonomy, term_key)
from study_wiki.knowledge import concept_graph


class TaxonomyTest(unittest.TestCase):
    def test_unicode_spacing_case_and_synonyms(self):
        self.assertEqual(normalize(['완전탐색', '완전\u00a0탐색', 'BRUTE FORCE', '브루트 포스'], 'tags'), ['완전 탐색'])
        self.assertEqual(normalize(['ＤＦＳ', '깊이우선탐색', 'depth first search'], 'algorithms'), ['깊이 우선 탐색'])
        self.assertEqual(normalize(['우선순위큐', 'priorityqueue', 'heap'], 'data_structures'), ['힙'])
        self.assertEqual(normalize(['새 기법', '새기법'], 'tags'), ['새 기법'])

    def test_core_projection_deduplicates_across_fields(self):
        result = classify({'data_structures': ['리스트', '문자열'], 'algorithms': ['반복', '시뮬레이션'],
                           'tags': ['array', '반복문', '문자열 처리', '새로운 기법']})
        self.assertEqual(result, {'data_structures': ['배열'], 'algorithms': ['문자열 처리', '구현'],
                                  'tags': [], 'keywords': ['새로운 기법']})

    def test_unseen_terms_do_not_create_concepts_or_guess_meanings(self):
        record = dict(id='a', kind='problem', tags=['새 기법', '새기법', 'Git'], algorithms=[], data_structures=[])
        self.assertEqual(concept_graph([record]), {'nodes': [], 'edges': []})
        self.assertEqual(classify(record)['keywords'], ['새 기법', 'Git'])
        self.assertEqual(classify({'tags': ['해시 비슷한 새 기법']})['data_structures'], [])

    def test_registry_conflicts_fail_and_projection_is_idempotent(self):
        alias_map('tags')  # Audit all shipped spellings, including cross-field collisions.
        with patch.dict(TAXONOMY, {'tags_test': {'다른 개념': ['D F S']}}):
            with self.assertRaisesRegex(ValueError, '충돌'):
                alias_map('tags')
        for field, group in TAXONOMY.items():
            for canonical, aliases in group.items():
                for alias in [canonical, *aliases]:
                    self.assertEqual(normalize([term_key(alias)], field), [canonical])
        record = classify({'tags': ['dfs', '리스트', '반복']})
        self.assertEqual(classify(record), record)

    def test_llm_new_terms_are_registered_with_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'taxonomy.json'
            target.write_bytes(TAXONOMY_PATH.read_bytes())
            result = register_taxonomy({
                'data_structures': [{'name': '세그먼트 트리', 'aliases': ['segment tree', 'SegmentTree']}],
                'algorithms': [{'name': '파라메트릭 서치', 'aliases': ['parametric search']}],
            }, target)
            self.assertEqual(result['added'], ['세그먼트 트리', '파라메트릭 서치'])
            taxonomy = json.loads(target.read_text())
            self.assertEqual(taxonomy['data_structures']['세그먼트 트리'], ['segment tree'])
            self.assertEqual(normalize(['segmenttree'], 'data_structures', taxonomy), ['세그먼트 트리'])
            self.assertEqual(normalize(['PARAMETRICSEARCH'], 'algorithms', taxonomy), ['파라메트릭 서치'])

    def test_new_term_alias_collision_is_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'taxonomy.json'
            target.write_bytes(TAXONOMY_PATH.read_bytes())
            before = target.read_bytes()
            with self.assertRaisesRegex(ValueError, '충돌'):
                register_taxonomy({'algorithms': [{'name': '새 알고리즘', 'aliases': ['DFS']}]}, target)
            self.assertEqual(target.read_bytes(), before)
