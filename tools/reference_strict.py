"""Torch-free execution of selected original AST methods over a NumPy array shim.
This is a reference-vector audit, NOT a PyTorch/model inference result.
"""
from pathlib import Path
import ast,types,hashlib,json,copy,sys
import numpy as np
import os
R=Path(__file__).resolve().parents[1];U=Path(os.environ.get('RC11C_UPSTREAM_ROOT', str(R/'.runtime/reference_source')))
RANKS=list('23456789TJQKA')
class Array:
 def __init__(self,data):self.data=np.asarray(data,dtype=np.float32)
 def __getitem__(self,key):
  x=self.data[key];return Array(x)if isinstance(x,np.ndarray)else x
 def __setitem__(self,key,value):self.data[key]=value.data if isinstance(value,Array)else value
 def reshape(self,*shape):return Array(self.data.reshape(*shape))
 def item(self):return self.data.item()
 def size(self,axis):return self.data.shape[axis]
 def unsqueeze(self,axis):return Array(np.expand_dims(self.data,axis))
class NumericShim:
 float32=np.float32
 @staticmethod
 def zeros(*shape,**kwargs):
  if len(shape)==1 and isinstance(shape[0],(tuple,list)):shape=shape[0]
  return Array(np.zeros(shape,dtype=np.float32))
 @staticmethod
 def full(shape,value,**kwargs):return Array(np.full(shape,value,dtype=np.float32))
 @staticmethod
 def tensor(data,**kwargs):return Array(data)
 @staticmethod
 def cat(values,dim=0):return Array(np.concatenate([x.data for x in values],axis=dim))
 @staticmethod
 def clamp(x,min=None,**kwargs):return Array(np.maximum(x.data,min))

def extract(path,classname,methods,newname):
 parsed=ast.parse(path.read_text());c=next(n for n in parsed.body if isinstance(n,ast.ClassDef)and n.name==classname)
 nodes=[copy.deepcopy(n)for n in c.body if isinstance(n,ast.FunctionDef)and n.name in methods]
 assert{n.name for n in nodes}==set(methods)
 unit=ast.Module(body=[ast.ClassDef(name=newname,bases=[],keywords=[],body=nodes,decorator_list=[])],type_ignores=[]);ast.fix_missing_locations(unit)
 ns={'torch':NumericShim,'CARD_RANK':RANKS+['BJ','RJ']};exec(compile(unit,str(path)+'#selected_reference_AST','exec'),ns)
 return ns[newname]
Encoder=extract(U/'guandan_rlcard/baselines/perfectdan/models.py','OptimizedGuandanStateEncoder',['encode_state','_parse_card','_encode_hand_cards','_encode_unknown_cards','_encode_players_played_cards','_encode_last_plays_by_position','_encode_action_to_feature','create_action_features','_has_overlapping_cards'],'ReferenceEncoder')
Agent=extract(U/'guandan_rlcard/baselines/perfectdan/ppo_agent.py','PPOGuandanAgent',['parse','abstract_action_space'],'ReferenceAgent')

def create(seat,variant='R0'):
 from observation_patch_strict import attach_observation_patch
 a=Agent();a.player_id=seat;e=Encoder();a.state_encoder=e;e.state_dim=673;e.device='cpu-reference-only';e.card_matrix_rows=4;e.card_matrix_cols=15;e.lstm_history_out_dim=128;e.suit_map={'S':0,'H':1,'C':2,'D':3};e.rank_map={r:i for i,r in enumerate(RANKS+['B','R'])}
 def unused(items):
  if items:raise RuntimeError('UNTRAINED_HISTORY_BRANCH_FORBIDDEN')
  return NumericShim.zeros(128)
 e._process_history_with_lstm=unused
 return attach_observation_patch(a,variant)

def encode(a,dto):return a.state_encoder.encode_state(a.parse(dto)).data[0]
def digest(x):return hashlib.sha256(np.asarray(x,dtype='<f4').tobytes()).hexdigest()

def independent_expected(dto,variant):
 """Independent list/count oracle, not calls to original encoder helpers."""
 fixed=variant in ('R1','R3');public=variant in ('R2','R3')
 unknown_mode=False
 def parse(card):
  if card=='HR'and fixed and not unknown_mode:return 0,14
  return 'SHCD'.index(card[0]),(RANKS+['B','R']).index(card[1:])
 def compress(cards,unknown=False):
  nonlocal unknown_mode
  unknown_mode=unknown
  matrix=[[2 if unknown else 0 for _ in range(15)]for _ in range(4)]
  for c in cards:
   s,r=parse(c);matrix[s][r]+=(-1 if unknown else 1)
  return [max(0,matrix[s][r])for s in range(4)for r in range(13)]+[max(0,matrix[0][13]),max(0,matrix[0][14])]
 out=compress(dto['current_hand'])+compress(dto['current_hand'],True)
 for s in range(4):out+=compress(dto['played_cards'].get(s,dto['played_cards'].get(str(s),[])))if public else[0]*54
 latest={}
 if public:
  for s,a in dto['trace']:
   if a:latest[s]=a
 seat=dto['self']
 for s in[seat,(seat-1)%4,(seat+1)%4,(seat+2)%4]:
  a=latest.get(s)
  if not a or a[0]=='PASS':out +=[0]*55;continue
  cards=a[2];flag=a[0]in ('Straight','ThreePair','TwoTrips')or any(parse(c)[0]==1 for c in cards);out+=compress(cards)+[int(flag)]
 out +=[dto['min_steps_estimation'][seat]]+[0]*128
 assert len(out)==673
 return np.asarray(out,dtype=np.float32)
