from typing import List, Dict
from models import Session, Balance, Payment, Settlement, Participant


def calculate_settlement(session: Session) -> Settlement:
    balances = calculate_balances(session)
    payments = optimize_payments(balances, session.participants)
    
    return Settlement(
        balances=balances,
        payments=payments
    )


def calculate_balances(session: Session) -> List[Balance]:
    participant_map = {p.id: p.name for p in session.participants}
    balance_map: Dict[str, int] = {p.id: 0 for p in session.participants}
    
    for expense in session.expenses:
        num_beneficiaries = len(expense.beneficiary_ids)
        
        amount_per_person = expense.amount_minor // num_beneficiaries
        remainder = expense.amount_minor % num_beneficiaries
        
        for i, beneficiary_id in enumerate(expense.beneficiary_ids):
            share = amount_per_person
            if i < remainder:
                share += 1
            
            balance_map[beneficiary_id] -= share
        
        balance_map[expense.payer_id] += expense.amount_minor
    
    balances = [
        Balance(
            participant_id=pid,
            participant_name=participant_map[pid],
            balance_minor=balance
        )
        for pid, balance in balance_map.items()
    ]
    
    balances.sort(key=lambda b: b.balance_minor, reverse=True)
    
    return balances


def optimize_payments(balances: List[Balance], participants: List[Participant]) -> List[Payment]:
    participant_map = {p.id: p.name for p in participants}
    
    debtors = [(b.participant_id, -b.balance_minor) for b in balances if b.balance_minor < 0]
    creditors = [(b.participant_id, b.balance_minor) for b in balances if b.balance_minor > 0]
    
    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)
    
    payments = []
    
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debt = debtors[i]
        creditor_id, credit = creditors[j]
        
        transfer_amount = min(debt, credit)
        
        if transfer_amount > 0:
            payments.append(Payment(
                from_participant_id=debtor_id,
                from_participant_name=participant_map[debtor_id],
                to_participant_id=creditor_id,
                to_participant_name=participant_map[creditor_id],
                amount_minor=transfer_amount
            ))
        
        debtors[i] = (debtor_id, debt - transfer_amount)
        creditors[j] = (creditor_id, credit - transfer_amount)
        
        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1
    
    return payments
