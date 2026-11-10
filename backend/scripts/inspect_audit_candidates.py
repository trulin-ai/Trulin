import json

db_claims = json.load(open('backend/scripts/baseline/db_224_claims_frozen.json', encoding='utf-8'))

target_investigate = [19, 43, 65, 66, 78, 109, 132, 224]
target_repair = [146, 147, 148, 150, 151, 152, 153, 154, 156, 157, 159, 160, 169, 170, 171, 172, 186, 187]
special_targets = [67, 77]

print('=== TARGET INVESTIGATE ===')
for num in target_investigate:
    c = db_claims[num - 1]
    cid = c['id'][:8]
    st = c['status']
    s = c['subject']
    p = c['predicate']
    o = str(c['object'])[:50]
    t = c['claim_text'][:60]
    print(f"#{num:03d} | ID: {cid} | Status: {st} | ({s} | {p} | {o}) | text: {t}")

print('\n=== SPECIAL TARGETS ===')
for num in special_targets:
    c = db_claims[num - 1]
    cid = c['id'][:8]
    st = c['status']
    s = c['subject']
    p = c['predicate']
    o = str(c['object'])[:50]
    t = c['claim_text'][:60]
    print(f"#{num:03d} | ID: {cid} | Status: {st} | ({s} | {p} | {o}) | text: {t}")

print('\n=== TARGET REPAIR ===')
for num in target_repair:
    c = db_claims[num - 1]
    cid = c['id'][:8]
    st = c['status']
    s = c['subject']
    p = c['predicate']
    o = str(c['object'])[:50]
    t = c['claim_text'][:60]
    print(f"#{num:03d} | ID: {cid} | Status: {st} | ({s} | {p} | {o}) | text: {t}")
