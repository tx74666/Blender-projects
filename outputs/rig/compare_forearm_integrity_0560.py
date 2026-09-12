"""Compare independent Blender snapshots without touching .blend files."""
import argparse,copy,json,math
from pathlib import Path

def compare(before,after):
    a=copy.deepcopy(before);b=copy.deepcopy(after)
    report=dict(ok=False,before=a['source'],after=b['source'],allowed_changes=[],
                failures=[],numeric_maxima={},owned_runtime_key_deltas={},calibration_metadata_changes=[])
    assert a['source_unchanged'] and b['source_unchanged']
    for data in (a,b):
        for key in ('source','source_sha256','source_unchanged'):data.pop(key,None)
    for side in 'LR':
        name='CTRL_hand_IK.'+side
        old=a['objects']['CoshaRig']['pose'][name]['at_shape']
        new=b['objects']['CoshaRig']['pose'][name]['at_shape']
        if old is False and new is True:
            report['allowed_changes'].append(f'{name}: use_transform_at_custom_shape False -> True')
            a['objects']['CoshaRig']['pose'][name]['at_shape']=True
    for name,record in a['calibrations'].items():
        if name in b['calibrations']:
            if record['raw']!=b['calibrations'][name]['raw']:
                report['calibration_metadata_changes'].append(name)
    for data in (a,b):
        for record in data['calibrations'].values():record.pop('raw',None)
    for name,mesh in a['meshes'].items():
        if name not in b['meshes']:continue
        for key,record in mesh['keys'].items():
            if not record['owned'] or key not in b['meshes'][name]['keys']:continue
            other=b['meshes'][name]['keys'][key]
            if not other['owned']:continue
            old=record.pop('coords');new=other.pop('coords')
            delta=max((abs(x-y) for x,y in zip(old,new)),default=0)
            report['owned_runtime_key_deltas'][f'{name}/{key}']=delta
            if len(old)!=len(new) or delta>1e-5:
                report['failures'].append(dict(path=f'meshes/{name}/keys/{key}/coords',reason='Owned runtime coordinates changed beyond 1e-5',max_error=delta))
            record.pop('hash');other.pop('hash')
    def walk(x,y,path):
        if type(x)!=type(y):
            report['failures'].append(dict(path=path,before_type=type(x).__name__,after_type=type(y).__name__))
        elif isinstance(x,dict):
            if x.keys()!=y.keys():
                report['failures'].append(dict(path=path,removed=sorted(x.keys()-y.keys()),added=sorted(y.keys()-x.keys())))
            for key in x.keys()&y.keys():walk(x[key],y[key],path+'/'+str(key))
        elif isinstance(x,list):
            if len(x)!=len(y):report['failures'].append(dict(path=path,before_count=len(x),after_count=len(y)))
            for i,(left,right) in enumerate(zip(x,y)):walk(left,right,path+'/'+str(i))
        elif isinstance(x,float):
            delta=abs(x-y)
            category='pose' if '/pose/' in path else 'object_matrix' if '/matrix' in path else 'other'
            report['numeric_maxima'][category]=max(delta,report['numeric_maxima'].get(category,0))
            tolerance=2e-5 if category in {'pose','object_matrix'} else 1e-7
            if not math.isfinite(delta) or delta>tolerance:report['failures'].append(dict(path=path,before=x,after=y,error=delta,tolerance=tolerance))
        elif x!=y:report['failures'].append(dict(path=path,before=x,after=y))
    walk(a,b,'')
    report['failure_count']=len(report['failures'])
    report['failures']=report['failures'][:100]
    report['ok']=report['failure_count']==0
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('before',type=Path);parser.add_argument('after',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    report=compare(json.loads(args.before.read_text(encoding='utf8')),json.loads(args.after.read_text(encoding='utf8')))
    args.output.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['ok'] else 1)
