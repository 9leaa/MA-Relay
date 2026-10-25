import concurrent.futures,json,tempfile,unittest
from pathlib import Path
import server
class StoreTests(unittest.TestCase):
    def test_concurrent_append_and_comments(self):
        with tempfile.TemporaryDirectory() as d:
            old=server.DATA;server.DATA=Path(d)
            try:
                key=server.create('测试',d)['id']
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                    list(pool.map(lambda i:server.append(key,{'text':str(i)}),range(30)))
                rows=server.records(key)
                self.assertEqual([x['id'] for x in rows],list(range(1,31)))
                server.append(key,{'text':'评论','reply_to':1})
                self.assertEqual(server.records(key)[-1]['reply_to'],1)
                with self.assertRaises(ValueError):server.append(key,{'text':'错误评论','reply_to':999})
                with self.assertRaises(ValueError):server.append(key,{'text':' '})
                with (server.message_file(key)).open('a') as f:f.write('{broken\n')
                with self.assertRaises(ValueError):server.records(key)
            finally:server.DATA=old

    def test_project_storage_and_arbitrary_agents(self):
        import subprocess,sys
        with tempfile.TemporaryDirectory() as d:
            old=server.DATA; server.DATA=Path(d)/'registry'
            project=Path(d)/'project';project.mkdir()
            try:
                key=server.create('项目',str(project))['id']
                self.assertEqual(server.message_file(key),(project/'.ma-relay/messages.jsonl').resolve())
                server.append(key,{'author':'Gemini','to':'Reviewer-4','text':'多 agent'})
                cli=project/'.ma-relay/relay.py'
                subprocess.run([sys.executable,str(cli),'send','--author','Reviewer-4','--reply-to','1','--text','离线评论'],check=True,capture_output=True)
                output=subprocess.check_output([sys.executable,str(cli),'read','--after','1'],text=True)
                self.assertIn('原消息上下文',output);self.assertIn('Reviewer-4',output)
                self.assertEqual(len(server.records(key)),2)
            finally:server.DATA=old

    def test_legacy_migration_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            project=Path(d)/'project';project.mkdir(); registry=Path(d)/'registry';registry.mkdir()
            legacy=registry/'messages.jsonl';legacy.write_text('{"id":1,"author":"Other","to":"所有人","time":"now","text":"原始记录"}\n')
            before=legacy.read_bytes()
            config=server.bind_project(dict(id='legacy',path=str(project),name='项目'),registry)
            self.assertEqual(Path(config['messages_path']).read_bytes(),before)
            self.assertEqual((registry/'messages.pre-migration.jsonl').read_bytes(),before)
            self.assertFalse(legacy.exists())

    def test_delete_preserves_sequence_and_references(self):
        import store
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'messages.jsonl';p.touch()
            store.append(p,{'text':'root'})
            store.append(p,{'text':'comment','reply_to':1})
            store.append(p,{'text':'other'})
            with self.assertRaises(ValueError):store.delete(p,1,1)
            store.delete(p,2,1)
            self.assertEqual([r['id'] for r in store.read(p)],[1,3])
            store.delete(p,3,1)
            self.assertEqual(store.append(p,{'text':'new'})['id'],4)
            store.append(p,{'text':'comment','reply_to':1})
            store.delete(p,1,2)
            self.assertEqual([r['id'] for r in store.read(p)],[4])
            store.delete(p,4,1)
            self.assertEqual(store.read(p),[])
            self.assertEqual(store.append(p,{'text':'after empty'})['id'],6)
