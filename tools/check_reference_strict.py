"""Torch-free original-public-golden validation; not neural inference."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import time
import numpy as np
from reference_strict import create, encode, digest, independent_expected
from observation_patch_strict import ALLOWED_BLOCKS

ROOT = Path(__file__).resolve().parents[1]


def run():
    start = time.time()
    source = ROOT / 'inputs/rc11/GOLDEN_PUBLIC_CASES.json'
    data = json.loads(source.read_text())
    derived = []
    for case in data['cases']:
        dto = copy.deepcopy(case['publicInput'])
        # Restore integer map keys exactly as historical public replay did.
        # JSON serialization changes map keys to strings; this is not a feature fix.
        for key in ('played_cards', 'min_steps_estimation'):
            dto[key] = {int(k): v for k, v in dto[key].items()}
        untouched = copy.deepcopy(dto)
        references = case['featureReference']
        vectors = {}
        for variant in ('R0', 'R1', 'R2', 'R3'):
            vector = np.zeros(673, dtype=np.float32)
            for index, value in references[variant]['expectedNonzero'].items():
                vector[int(index)] = value
            assert digest(vector) == references[variant]['vectorSHA256']
            vectors[variant] = vector
        base_agent = create(dto['self'], 'R0')
        base_parsed = base_agent.parse(dto)
        base_features, base_indices = base_agent.state_encoder.create_action_features(
            base_parsed, base_parsed['actionList'])
        base_groups = base_agent.abstract_action_space(base_parsed['actionList'])
        for variant in ('R0', 'R1', 'R2', 'R3'):
            expected = vectors[variant].copy()
            expected[54:108] = vectors['R0'][54:108]
            agent = create(dto['self'], variant)
            actual = encode(agent, dto)
            assert np.array_equal(actual, expected), (case['id'], variant, 'derived')
            assert np.array_equal(actual, independent_expected(dto, variant)), (
                case['id'], variant, 'independent_oracle')
            assert np.array_equal(actual[54:108], vectors['R0'][54:108])
            assert np.array_equal(actual[544:], vectors['R0'][544:])
            changed = np.flatnonzero(actual != vectors['R0']).tolist()
            assert all(any(lo <= i < hi for lo, hi in ALLOWED_BLOCKS[variant])
                       for i in changed), (case['id'], variant, changed)
            parsed = agent.parse(dto)
            features, indices = agent.state_encoder.create_action_features(
                parsed, parsed['actionList'])
            assert indices == base_indices
            assert agent.abstract_action_space(parsed['actionList']) == base_groups
            assert len(features) == len(base_features)
            assert all(np.array_equal(a.data, b.data)
                       for a, b in zip(features, base_features))
            assert dto == untouched
            derived.append({'id': case['id'], 'variant': variant,
                            'vectorSHA256': digest(actual),
                            'changedIndicesFromR0': changed,
                            'expectedNonzero': {str(i): float(v) for i, v in
                                                enumerate(expected) if v},
                            'unknown54IdenticalR0': True,
                            'tail129IdenticalR0': True,
                            'actionFeaturesAndIndicesIdenticalR0': True,
                            'actionGroupingIdenticalR0': True})
    assert 'torch' not in sys.modules, 'NEURAL_RUNTIME_MUST_NOT_BE_IMPORTED'
    result = {'status': 'PASS', 'scope': 'NumPy reference only; no neural logits/actions',
              'originalGoldenSHA256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'originalCases': len(data['cases']), 'newGeneratedStates': 0,
              'variantRows': len(derived), 'torchImported': False,
              'seconds': time.time() - start, 'rows': derived}
    (ROOT / 'evidence/STRICT_UNKNOWN54_REFERENCE_QA.json').write_text(
        json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))


if __name__ == '__main__':
    run()
