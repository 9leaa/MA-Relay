"""Project-owned, append-only conversation store (macOS/Linux)."""
import fcntl, json, os
from pathlib import Path
from datetime import datetime, timezone

from contextlib import contextmanager

@contextmanager
def locked(path, exclusive=False):
    with Path(path).with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield

def read(path):
    with locked(path): return parse(Path(path).read_text())

def atomic_write(path,text):
    import tempfile
    path=Path(path)
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
    try:
        with os.fdopen(fd,'w') as f:
            f.write(text);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
        directory=os.open(path.parent,os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.exists(name): os.unlink(name)

def highwater(path,rows):
    state=Path(path).with_name('sequence.json')
    saved=json.loads(state.read_text())['last_id'] if state.exists() else 0
    return max(saved,max((r['id'] for r in rows),default=0))

def save_sequence(path,value):
    atomic_write(Path(path).with_name('sequence.json'),json.dumps({'last_id':value})+'\n')

def delete(path,message_id,expected_count=None):
    with locked(path,True):
        rows=parse(Path(path).read_text())
        if not any(r['id']==message_id for r in rows): raise ValueError('消息已不存在，请刷新')
        removed=[r for r in rows if r['id']==message_id or r.get('reply_to')==message_id]
        if expected_count is not None and len(removed)!=expected_count: raise ValueError('评论数量已变化，请重新确认删除')
        save_sequence(path,highwater(path,rows))
        remaining=[r for r in rows if r not in removed]
        atomic_write(path,''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in remaining))
        return {'deleted_ids':[r['id'] for r in removed]}

def parse(text):
    rows=[]; ids=set()
    for n,line in enumerate(text.splitlines(),1):
        if not line.strip(): continue
        try:
            row=json.loads(line)
            if not isinstance(row['id'],int) or row['id']<=0 or row['id'] in ids: raise ValueError()
            for k in ['author','to','text','time']:
                if not isinstance(row[k],str) or not row[k].strip(): raise ValueError()
            if row.get('reply_to') is not None and not any(x['id']==row['reply_to'] and not x.get('reply_to') for x in rows): raise ValueError()
        except (ValueError,KeyError,TypeError): raise ValueError(f'交流记录第 {n} 行无效，请修复；未跳过任何消息')
        ids.add(row['id']); rows.append(row)
    return rows

def append(path,body):
    author=body.get('author','你'); to=body.get('to','所有人'); text=body.get('text','')
    for value in [author,to]:
        if not isinstance(value,str) or not value.strip() or len(value)>80 or '\n' in value: raise ValueError('参与者名称须为 1–80 个字符，不能换行')
    if not isinstance(text,str) or not text.strip(): raise ValueError('消息不能为空')
    with locked(path,True):
        original=Path(path).read_text();rows=parse(original);parent=body.get('reply_to')
        if parent is not None and not any(r['id']==parent and not r.get('reply_to') for r in rows): raise ValueError('原消息不存在')
        number=highwater(path,rows)+1
        save_sequence(path,number)
        row=dict(id=number,author=author.strip(),to=to.strip(),time=datetime.now(timezone.utc).isoformat(),text=text.strip())
        if parent is not None: row['reply_to']=parent
        with Path(path).open('a') as f:
            if original and not original.endswith('\n'): f.write('\n')
            f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno())
        return row
