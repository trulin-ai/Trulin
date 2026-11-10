import json

with open('backend/scripts/baseline/phase2_5_repaired_extraction_v1.json', 'r', encoding='utf-8') as f:
    claims = json.load(f)

cdict = {c['number']: c for c in claims}

def get_claim_section(c):
    p = c.get('locators', [{}])[0].get('page', 0)
    text = (c.get('claim_text', '') + ' ' + ' '.join(c.get('evidence_quotes', []))).lower()
    if p == 3: return 'Section 1. Introduction and Scope'
    if p == 4: return 'Section 2. Definitions'
    if p == 5:
        if any(k in text for k in ['without', 'receipt', 'photo id']): return 'Section 3.2 Returns without a receipt'
        if 'exchange' in text: return 'Section 3.3 Exchanges'
        if any(k in text for k in ['gold', 'window', 'footwear']): return 'Section 3.1 Extended windows'
        return 'Section 3. Standard Return Policy'
    if p == 6:
        if any(k in text for k in ['approval', 'tier 1', 'tier 2', 'over $', 'manager']): return 'Section 4.2 Manager approval thresholds'
        if any(k in text for k in ['deduction', 'partial', 'packaging']): return 'Section 4.1 Partial refunds'
        return 'Section 4. Refund Eligibility Criteria'
    if p == 7:
        if any(k in text for k in ['5.2', 'damaged', 'defective', 'error']): return 'Section 5.2 Exceptions'
        return 'Section 5. Non-Refundable Items'
    if p == 8:
        if any(k in text for k in ['order number', 'required information', 'sku', 'photos']): return 'Section 6.4 Required information'
        return 'Section 6. How to Request a Refund'
    if p == 9: return 'Section 7. Refund Processing Timelines'
    if p == 10:
        if any(k in text for k in ['bonus', 'store credit']): return 'Section 8.1 Store credit bonus'
        return 'Section 8. Refund Methods and Payment Types'
    if p == 11:
        if any(k in text for k in ['freight', 'oversized']): return 'Section 9.2 Oversized and freight items'
        return 'Section 9. Shipping Costs and Return Labels'
    if p == 12:
        if any(k in text for k in ['resolution', 'replacement', 'keep it']): return 'Section 10.3 Resolution options'
        return 'Section 10. Damaged, Defective or Incorrect Items'
    if p == 13:
        if 'price adjustment' in text: return 'Section 11.2 Price adjustments'
        return 'Section 11. Order Cancellations'
    if p == 14:
        if any(k in text for k in ['free trial', 'trial']): return 'Section 12.1 Free trials'
        return 'Section 12. Subscription Refunds'
    if p == 15:
        if 'gift card' in text: return 'Section 13.2 Gift cards'
        return 'Section 13. Digital Products and Gift Cards'
    if p == 16:
        if 'marketplace' in text: return 'Section 14.2 Marketplace sellers'
        return 'Section 14. Warranty Claims'
    if p == 17:
        if 'currency' in text: return 'Section 15.2 Currency rules'
        return 'Section 15. International Orders'
    if p == 18:
        if any(k in text for k in ['dispute', 'fee']): return 'Section 16.3 Dispute penalties'
        return 'Section 16. Chargeback reason codes'
    if p == 19:
        if any(k in text for k in ['level', 'notice', 'restricted', 'suspended', 'permanent', 'consequences']): return 'Section 17.1 Consequences'
        return 'Section 17. Fraud Prevention and Abuse'
    if p == 20: return 'Section 18. Frequently Asked Questions'
    if p == 21:
        if any(k in text for k in ['service-level', 'target', 'query']): return 'Section 19.2 Service-level commitments'
        return 'Section 19. Contact Information and Escalation'
    if p == 22: return 'Section 20.1 Revision history'
    return f'Section on page {p}'

check_ids = [32, 33, 34, 35, 57, 64, 110, 111, 112, 113, 114, 115, 116, 117, 190, 191, 192, 193, 194, 195, 196, 197, 209, 215, 223, 224]
for cid in check_ids:
    p = cdict[cid]['locators'][0]['page']
    sec = get_claim_section(cdict[cid])
    print(f"Claim #{cid} (p.{p}) -> {sec}")
