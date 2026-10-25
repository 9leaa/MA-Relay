#!/usr/bin/env python3
"""Read/write a project conversation offline; optional workspace ID uses the server."""
import argparse,json,urllib.request
from pathlib import Path
import store
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:18765');p.add_argument('--project',type=Path);sub=p.add_subparsers(dest='command',required=True)
sub.add_parser('spaces')
r=sub.add_parser('read');r.add_argument('workspace',nargs='?');r.add_argument('--after',type=int,default=0);r.add_argument('--thread',type=int)
s=sub.add_parser('send');s.add_argument('workspace',nargs='?');s.add_argument('--author',required=True);s.add_argument('--to',default='所有人');s.add_argument('--reply-to',type=int);s.add_argument('--text',required=True)
a=p.parse_args()
def request(path,body=None):
    req=urllib.request.Request(a.url+'/api/'+path,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req) as r:return json.load(r)
def local_file():
    if a.project: return a.project.resolve()/'.ma-relay'/'messages.jsonl'
    here=Path(__file__).resolve().parent
    return (here if here.name=='.ma-relay' else Path.cwd()/'.ma-relay')/'messages.jsonl'
try:
    if a.command=='spaces':
        for x in request('workspaces'): print(f"{x['id']} | {x['name']} | {x['path']} | {x.get('messages_path','旧记录')}")
    elif a.command=='send':
        body=dict(author=a.author,to=a.to,text=a.text,reply_to=a.reply_to)
        row=request('messages',dict(workspace=a.workspace,**body)) if a.workspace else store.append(local_file(),body)
        print(json.dumps(row,ensure_ascii=False))
    else:
        rows=request('messages?workspace='+a.workspace) if a.workspace else store.read(local_file())
        selected=[m for m in rows if m['id']>a.after and (not a.thread or m['id']==a.thread or m.get('reply_to')==a.thread)]
        ids={m['id'] for m in selected};parents={m['reply_to'] for m in selected if m.get('reply_to')} - ids
        for m in [x for x in rows if x['id'] in ids|parents]:
            context=' [原消息上下文]' if m['id'] in parents else ''
            reply=f" | 回复 #{m['reply_to']}" if m.get('reply_to') else ''
            print(f"\n#{m['id']} {m['author']} → {m['to']}{reply}{context}\n{m['text']}")
        print(f"\n记录最新编号: {max((m['id'] for m in rows),default=0)}")
except (OSError,ValueError) as e: p.exit(1,f'读取/写入失败：{e}\n')
