"""Local browser runner for smart_home_device_mgmt.py. Run: python web_test.py"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape
import json
import threading
import webbrowser

from smart_home_device_mgmt import DEVICE_REGISTRY, run_device_pipeline

HOST = '127.0.0.1'
PORT = 8765

PAGE = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Smart Home Agent Test</title>
<style>
body{font:16px system-ui;background:#101827;color:#f1f5f9;max-width:850px;margin:3rem auto;padding:0 1rem}
h1{margin-bottom:.3rem}p{color:#bdc9d9}button{background:#38bdf8;border:0;border-radius:8px;padding:.8rem 1rem;margin:.4rem .5rem .4rem 0;cursor:pointer;font-weight:700}
button:disabled{opacity:.5;cursor:wait}.card{background:#1d2b3d;padding:1rem;border-radius:12px;margin:1rem 0}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#09111d;padding:1rem;border-radius:8px}strong{color:#a7f3d0}
</style><h1>Smart Home Agent Test</h1>
<p>Choose a device. The Python server runs Monitor → Diagnostics → Command with AWS Bedrock. Commands use the exercise's simulated tool.</p>
<div id="buttons"></div><div id="result" role="status"></div>
<script>
const devices=__DEVICES__;
const buttons=document.getElementById('buttons'), result=document.getElementById('result');
for(const [id,name] of Object.entries(devices)){
 const b=document.createElement('button');b.textContent=name+' ('+id+')';
 b.onclick=async()=>{
  document.querySelectorAll('button').forEach(x=>x.disabled=true);
  result.innerHTML='<div class="card">Running agents… Bedrock may take a minute.</div>';
  try{
   const res=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id:id})});
   const data=await res.json();if(!res.ok)throw Error(data.error||'Request failed');
   const issues=data.diagnosis.issues||[];
   result.replaceChildren();
   const card=document.createElement('div');card.className='card';
   const heading=document.createElement('h2');heading.textContent=data.sensor_data.device_name;card.append(heading);
   const status=document.createElement('p');status.textContent='Status: '+data.diagnosis.status;card.append(status);
   for(const issue of issues){const p=document.createElement('p');p.textContent='Issue: '+issue.issue+' ('+issue.field+'='+issue.value+')';card.append(p)}
   for(const cmd of data.commands){const p=document.createElement('p');p.textContent='Dispatched: '+cmd.action+' — '+cmd.message;card.append(p)}
   if(!issues.length){const p=document.createElement('p');p.textContent='No corrective command needed.';card.append(p)}
   const details=document.createElement('details'), summary=document.createElement('summary'), pre=document.createElement('pre');
   summary.textContent='Full agent output';pre.textContent=JSON.stringify(data,null,2);details.append(summary,pre);card.append(details);result.append(card);
  }catch(err){result.textContent='Error: '+err.message+' — Check AWS credentials, model access, and the server terminal.'}
  finally{document.querySelectorAll('button').forEach(x=>x.disabled=false)}
 };
 buttons.append(b)
}
</script></html>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/':
            self.send_error(404)
            return
        page = PAGE.replace('__DEVICES__', json.dumps({k: v['name'] for k, v in DEVICE_REGISTRY.items()}))
        self.respond(200, page.encode(), 'text/html; charset=utf-8')

    def do_POST(self):
        if self.path != '/api/run':
            self.send_error(404)
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size > 1024 or size <= 0:
                raise ValueError('Invalid request size')
            device_id = json.loads(self.rfile.read(size)).get('device_id')
            if device_id not in DEVICE_REGISTRY:
                raise ValueError('Unknown device ID')
            self.respond(200, json.dumps(run_device_pipeline(device_id)).encode(), 'application/json')
        except (ValueError, json.JSONDecodeError) as exc:
            self.respond(400, json.dumps({'error': str(exc)}).encode(), 'application/json')
        except Exception as exc:
            self.respond(500, json.dumps({'error': f'{type(exc).__name__}: {exc}'}).encode(), 'application/json')

    def respond(self, status, data, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)


if __name__ == '__main__':
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f'Open http://{HOST}:{PORT} in a browser (Ctrl+C to stop).')
    threading.Timer(0.6, lambda: webbrowser.open(f'http://{HOST}:{PORT}')).start()
    server.serve_forever()
