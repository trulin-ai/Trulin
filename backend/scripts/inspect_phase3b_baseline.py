import json
import asyncio
from sqlalchemy import text
from app.db.database import AsyncSessionLocal

with open('backend/scripts/baseline/phase2_5_repaired_extraction_v1.json', 'r', encoding='utf-8') as f:
    ex = json.load(f)

uuid_to_claim = {c['id']: c for c in ex}
uuid_to_num = {c['id']: c.get('number') for c in ex}

async def analyze_diffs():
    async with AsyncSessionLocal() as session:
        await session.execute(text("SET TRANSACTION READ ONLY;"))
        pub_rows = (await session.execute(text("""
            SELECT c.id::text, c.claim_text, c.subject, c.predicate, c.object, c.status
            FROM public.claims c
            JOIN public.document_versions dv ON dv.id = c.document_version_id
            WHERE dv.document_id = 'e3cdd194-1a9b-4f01-9031-13e6b027d3d2'
        """))).fetchall()
        stg_rows = (await session.execute(text("""
            SELECT c.id::text, c.claim_text, c.subject, c.predicate, c.object, c.status
            FROM staging.claims c
            JOIN staging.document_versions dv ON dv.id = c.document_version_id
            WHERE dv.document_id = 'e3cdd194-1a9b-4f01-9031-13e6b027d3d2'
        """))).fetchall()

    pub_map = {r[0]: r for r in pub_rows}
    stg_map = {r[0]: r for r in stg_rows}

    diffs = []
    for uid, pub in pub_map.items():
        stg = stg_map.get(uid)
        num = uuid_to_num.get(uid)
        c_obj = uuid_to_claim.get(uid)
        pub_text, pub_subj, pub_pred, pub_obj, pub_status = pub[1], pub[2], pub[3], pub[4], pub[5]
        stg_text, stg_subj, stg_pred, stg_obj, stg_status = stg[1], stg[2], stg[3], stg[4], stg[5]

        has_pred = (pub_pred != stg_pred)
        has_text = (pub_text != stg_text)
        has_subj = (pub_subj != stg_subj)
        has_obj = (pub_obj != stg_obj)

        if has_pred or has_text or has_subj or has_obj:
            diffs.append({
                'number': num,
                'id': uid,
                'subject': c_obj.get('subject'),
                'pub_subj': pub_subj,
                'stg_subj': stg_subj,
                'pub_pred': pub_pred,
                'stg_pred': stg_pred,
                'pub_obj': pub_obj,
                'stg_obj': stg_obj,
                'has_pred': has_pred,
                'has_text': has_text,
                'has_subj': has_subj,
                'has_obj': has_obj,
                'status': stg_status,
                'quote': c_obj.get('evidence_quotes', [''])[0][:60]
            })

    diffs.sort(key=lambda x: x['number'] if x['number'] is not None else 999)
    print(f"Total diffs found: {len(diffs)}")

    cumulative_ledger = []
    for d in diffs:
        num = d['number']
        c_obj = uuid_to_claim[d['id']]
        phases = []
        
        # Phase 2.2c: Table bindings and structural subjects
        if num in [12, 24, 31, 32, 37, 43, 107, 108, 110, 111, 112, 113, 116, 117, 118, 129, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 223, 224]:
            phases.append("Phase 2.2c (Structural & Subject Repair)")
            
        # Phase 2.3: Catch-all predicate specialization
        if num in [2, 3, 4, 5, 6, 21, 24, 37, 78, 94, 97, 108, 118, 132, 134, 152, 175, 198, 199, 223, 224]:
            phases.append("Phase 2.3 (Predicate Registry Specialization)")
            
        # Phase 2.3b: Source semantics & typed verbs
        if num in [66, 67, 127, 129, 132]:
            phases.append("Phase 2.3b (Source Semantics Alignment)")
            
        # Phase 2.4b: Value fidelity & quantitative normalizations
        if num in [19, 21, 129]:
            phases.append("Phase 2.4b (Value Fidelity & Token Preservation)")
            
        # Phase 2.5: Exclusion & conflict invariant grounding
        if num in [223, 224]:
            phases.append("Phase 2.5 (Section 5 Grounding & Invariant Preservation)")

        cumulative_ledger.append({
            "number": num,
            "id": d['id'],
            "subject": d['subject'],
            "public_predicate": d['pub_pred'],
            "staging_predicate": d['stg_pred'],
            "public_subject": d['pub_subj'],
            "staging_subject": d['stg_subj'],
            "first_phase": phases[0] if phases else "Phase 2.2c",
            "all_phases": phases,
            "final_status": d['status'],
            "quote": c_obj.get('evidence_quotes', [''])[0],
            "locators": c_obj.get('locators', [])
        })

    print(f"Total claims in ledger: {len(cumulative_ledger)}")
    print("Phase representation in 55 claims:")
    p22c_count = sum(1 for c in cumulative_ledger if any("2.2c" in p for p in c['all_phases']))
    p23_count = sum(1 for c in cumulative_ledger if any("2.3 (" in p for p in c['all_phases']))
    p23b_count = sum(1 for c in cumulative_ledger if any("2.3b" in p for p in c['all_phases']))
    p24b_count = sum(1 for c in cumulative_ledger if any("2.4b" in p for p in c['all_phases']))
    p25_count = sum(1 for c in cumulative_ledger if any("2.5" in p for p in c['all_phases']))
    print(f"  Phase 2.2c changes: {p22c_count}")
    print(f"  Phase 2.3 changes: {p23_count}")
    print(f"  Phase 2.3b changes: {p23b_count}")
    print(f"  Phase 2.4b changes: {p24b_count}")
    print(f"  Phase 2.5 changes: {p25_count}")
    overlap = (p22c_count + p23_count + p23b_count + p24b_count + p25_count) - 55
    print(f"  Total changes summed across phases: {p22c_count + p23_count + p23b_count + p24b_count + p25_count}")
    print(f"  Multi-phase overlapping repairs: {overlap}")
    print(f"  Unique repaired claims: {len(cumulative_ledger)}")

if __name__ == "__main__":
    asyncio.run(analyze_diffs())
