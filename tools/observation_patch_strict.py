"""Owner-approved RC1.1-C ablation, with unknown54 frozen at released R0.

No Torch import, model load, initialization, training, sorting or action repair.
Attach once to each fresh independent agent before its first decision.
"""
from copy import copy, deepcopy
from types import MethodType

VARIANTS = ('R0', 'R1', 'R2', 'R3')
ALLOWED_BLOCKS = {
    'R0': (), 'R1': ((0, 54),), 'R2': ((108, 544),),
    'R3': ((0, 54), (108, 544)),
}


def attach_observation_patch(agent, variant):
    if variant not in VARIANTS:
        raise ValueError('UNKNOWN_OBSERVATION_VARIANT')
    if hasattr(agent, '_rc11_variant'):
        raise RuntimeError('PATCH_ALREADY_ATTACHED')
    if getattr(agent, 'history_buffer', []):
        raise RuntimeError('ATTACH_BEFORE_FIRST_DECISION_ONLY')
    agent._rc11_variant = variant
    if variant == 'R0':
        return agent
    encoder = agent.state_encoder
    if variant in ('R1', 'R3'):
        # A shallow receiver copy preserves the original parser and original
        # unknown-card method without constructing a network or consuming RNG.
        # That method only reads dimensions/maps/device and builds its vector.
        # It must never call the corrected parser on the live encoder.
        original_receiver = copy(encoder)
        original_unknown = type(encoder)._encode_unknown_cards
        original_card = encoder._parse_card

        def unknown(self, state):
            return original_unknown(original_receiver, state)

        def parse_card(self, card):
            return (0, 14) if card == 'HR' else original_card(card)

        encoder._encode_unknown_cards = MethodType(unknown, encoder)
        encoder._parse_card = MethodType(parse_card, encoder)
    if variant in ('R2', 'R3'):
        old_parse = agent.parse
        old_played = encoder._encode_players_played_cards
        old_recent = encoder._encode_last_plays_by_position

        def parse(self, state):
            parsed = old_parse(state)
            # Never add played_cards to the top level: unknown54 must stay R0.
            parsed['_rc11_public_observation'] = {
                'played_cards': deepcopy(state['played_cards']),
                'trace': deepcopy(state['trace']),
            }
            return parsed

        def played(self, state):
            public = state['_rc11_public_observation']
            cards = {int(k): deepcopy(v) for k, v in public['played_cards'].items()}
            return old_played({**state, 'played_cards': cards})

        def recent(self, state, seat):
            public = state['_rc11_public_observation']
            history = {str(s): {'send': [], 'remain': state['remain_cards'][s]}
                       for s in range(4)}
            for player, action in public['trace']:
                if action:
                    history[str(player)]['send'].append(deepcopy(action))
            return old_recent({**state, 'history': history}, seat)

        agent.parse = MethodType(parse, agent)
        encoder._encode_players_played_cards = MethodType(played, encoder)
        encoder._encode_last_plays_by_position = MethodType(recent, encoder)
    return agent
