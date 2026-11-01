import uuid
from decimal import Decimal, InvalidOperation
from .audit_service import digest
from .database import utcnow


class SandboxService:
    TARGETS = {'wealth.subscribe': {'P01', 'P02', 'P03'},
               'transfer.simulate': {'demo-recipient'},
               'card.freeze': {'demo-card'},
               'subscription.cancel': {'S01','S02','S03','S04'}}
    MONEY_ACTIONS = {'wealth.subscribe', 'transfer.simulate'}

    @staticmethod
    def cents(value):
        try:
            amount = Decimal(str(value))
            if not amount.is_finite() or amount < 0 or amount * 100 != (amount * 100).to_integral_value():
                raise ValueError('Amount must be finite, nonnegative and have at most two decimal places')
            if amount > 100000000:
                raise ValueError('Amount exceeds simulation limit')
            return int(amount * 100)
        except (InvalidOperation, TypeError):
            raise ValueError('Invalid amount')

    @staticmethod
    def plan_hash(workflow):
        return digest({k: workflow.get(k) for k in ('workflow_id','actor_id','action','amount_cents',
                      'recipient','nodes','edges','idempotency_key','permission_level',
                      'policy_version','policy_fingerprint','policy_generation','risk_flags')})

    def validate(self, conn, workflow):
        w = workflow
        results = []
        def check(name, ok):
            results.append({'check': name, 'passed': bool(ok)})
        nodes = w['nodes']
        ids = [n['task_id'] for n in nodes]
        edges = {(e['source'], e['target']) for e in w['edges']}
        edges.update((dep, n['task_id']) for n in nodes for dep in n.get('dependencies', []))
        check('unique_nodes', len(ids) == len(set(ids)) and bool(ids))
        check('dependencies_exist', all(a in ids and b in ids for a,b in edges))
        pending = set(ids)
        while pending:
            ready = {n for n in pending if not any(b == n and a in pending for a,b in edges)}
            if not ready:
                break
            pending -= ready
        check('acyclic', not pending)
        action = w['action']
        check('action_allowlist', action in self.TARGETS)
        check('recipient_allowlist', w['recipient'] in self.TARGETS.get(action, set()))
        amount = w['amount_cents']
        check('amount', isinstance(amount, int) and (amount > 0 if action in self.MONEY_ACTIONS else amount == 0))
        account = conn.execute('SELECT * FROM simulated_accounts WHERE actor_id=?', (w['actor_id'],)).fetchone()
        check('balance_and_reserves', account is not None and account['balance_cents'] - account['reserved_cents'] >= amount)
        expected = 'YELLOW' if action == 'subscription.cancel' else 'RED'
        check('permission', w['permission_level'] == expected)
        check('risk_rules', not w.get('risk_flags'))
        current_hash = self.plan_hash(w)
        check('bound_plan', current_hash == w['plan_hash'])
        return {'sandbox_status': 'passed' if all(r['passed'] for r in results) else 'rejected',
                'sandbox_run_id': uuid.uuid4().hex, 'plan_hash': current_hash,
                'validation_results': results, 'risk_level': 'HIGH' if amount > 5000000 else 'MEDIUM',
                'validated_at': utcnow()}

    def execute(self, conn, w):
        # This method has no network clients. Called only inside the gateway transaction.
        amount = w['amount_cents']
        cursor = conn.execute('UPDATE simulated_accounts SET balance_cents=balance_cents-? '
                              'WHERE actor_id=? AND balance_cents-reserved_cents>=?',
                              (amount, w['actor_id'], amount))
        if cursor.rowcount != 1:
            raise ValueError('Insufficient unreserved simulation balance')
        conn.execute('INSERT INTO simulated_entries VALUES (?,?,?,?,?)',
                     (w['workflow_id'], w['actor_id'], amount, w['recipient'], utcnow()))
        if w['action'] not in self.MONEY_ACTIONS:
            conn.execute('INSERT INTO simulated_objects VALUES (?,?,?) ON CONFLICT(actor_id,object_id) '
                         'DO UPDATE SET status=excluded.status',
                         (w['actor_id'],w['recipient'],'FROZEN' if w['action']=='card.freeze' else 'CANCELLED'))
