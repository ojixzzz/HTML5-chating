import json
import gevent
import memcache
from gevent import monkey; monkey.patch_all()
from bottle import Bottle, run, hook, response, request

app = Bottle()
mc = memcache.Client(['localhost:11211'], debug=0)

@app.hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin']='*'

def wait_message(lastdata):
    while True:
        newdata = mc.get('chating_pesan')
        if newdata != lastdata:
            break
        gevent.sleep(1)
    return newdata

def sse_pack(d):
    buffer = ''
    for k in ['retry','id','event','data']:
        if k in d.keys():
            buffer += '%s: %s\n' % (k, d[k])
    return buffer + '\n'

@app.route("/apis/v0/pesan", method="OPTIONS")
def options():
    response.headers.update({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'X-REQUESTED-WITH, CACHE-CONTROL, LAST-EVENT-ID',
        'Content-Type': 'text/plain'
    })
    return ''

@app.route('/apis/v0/pesan', method='GET')
def get_pesan():
    pesan = ""
    event_id = 0
    if 'Last-Event-Id' in request.headers:
        event_id = int(request.headers['Last-Event-Id']) + 1

    msg = {
        'retry': '2000'
    }

    response.headers['content-type'] = 'text/event-stream'
    response.headers['Access-Control-Allow-Origin'] = '*'
    msg.update({
         'event': 'init',
         'data' : 'connected',
         'id'   : event_id
    })
    yield sse_pack(msg) 

    event_id += 1    
    msg['event'] = 'delta'
    while True:
        pesan = wait_message(pesan)
        msg.update({
             'event': 'delta',
             'data' : json.dumps(pesan),
             'id'   : event_id
        })
        yield sse_pack(msg)
        event_id += 1

@app.route('/apis/v0/pesan', method='POST')
def setpesan():
    try:
        rjson = json.load(request.body, encoding='utf-8')
        mc.set('chating_pesan', rjson)
    except Exception as e:
        return json.dumps({'error':str(e)})

def main():
    run(app, host="0.0.0.0", port=8080, server="gevent")

if __name__ == '__main__':
    main()