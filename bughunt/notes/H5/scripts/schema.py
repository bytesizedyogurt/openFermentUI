"""Print an openapi component schema with its refs expanded to a depth (a reading aid)."""
import json, sys
d = json.load(open('/home/user/openFermentUI/docs/api/openapi.json'))
S = d['components']['schemas']
def show(s, depth):
    if '$ref' in s:
        n = s['$ref'].split('/')[-1]
        return n if depth <= 0 else {n: show(S[n], depth - 1)}
    if 'anyOf' in s:
        return [show(x, depth) for x in s['anyOf']]
    if s.get('type') == 'array':
        return [show(s.get('items', {}), depth)]
    if 'properties' in s:
        return {('*' if k in s.get('required', []) else '') + k: show(v, depth) for k, v in s['properties'].items()}
    if 'enum' in s:
        return 'enum' + json.dumps(s['enum'])
    if 'const' in s:
        return 'const ' + json.dumps(s['const'])
    return s.get('type', '?')
for n in sys.argv[2:]:
    print(n, json.dumps(show(S[n], int(sys.argv[1])), indent=1))
