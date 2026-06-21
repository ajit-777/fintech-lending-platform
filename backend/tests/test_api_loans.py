"""Integration tests for the borrower loan lifecycle."""
from tests.conftest import LOAN_PAYLOAD, accept_agreement, auth_headers, register, register_admin


def test_apply_loan_auto_approved(client):
    token = register(client)
    r = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token))
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "approved"
    assert data["annual_interest_rate"] == 10.0   # Prime tier
    assert data["processing_fee"] == 1500.0        # 1.5% of 100000


def test_apply_loan_auto_rejected_low_cibil(client):
    token = register(client)
    payload = {**LOAN_PAYLOAD, "cibil_score": 600}
    r = client.post("/loans", json=payload, headers=auth_headers(token))
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] is not None


def test_apply_loan_pending_edge_case(client):
    token = register(client)
    # CIBIL in 650-750 range with high DTI → pending
    payload = {**LOAN_PAYLOAD, "cibil_score": 710, "monthly_income": 20000, "amount": 500000}
    r = client.post("/loans", json=payload, headers=auth_headers(token))
    assert r.status_code == 201
    assert r.json()["status"] == "pending"


def test_repayment_schedule_generated_on_approval(client):
    token = register(client)
    loan = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token)).json()
    assert loan["status"] == "approved"

    r = client.get(f"/loans/{loan['id']}/repayments", headers=auth_headers(token))
    assert r.status_code == 200
    installments = r.json()
    assert len(installments) == 12
    assert installments[0]["installment_number"] == 1
    assert installments[0]["status"] == "pending"


def test_repayment_schedule_not_available_for_rejected(client):
    token = register(client)
    payload = {**LOAN_PAYLOAD, "cibil_score": 600}
    loan = client.post("/loans", json=payload, headers=auth_headers(token)).json()
    r = client.get(f"/loans/{loan['id']}/repayments", headers=auth_headers(token))
    assert r.status_code == 400


def test_list_loans_returns_only_own(client):
    token1 = register(client, email="a@test.com", phone="+919000000011")
    token2 = register(client, email="b@test.com", phone="+919000000022")

    client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token1))
    client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token1))
    client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token2))

    r1 = client.get("/loans", headers=auth_headers(token1)).json()
    r2 = client.get("/loans", headers=auth_headers(token2)).json()
    assert len(r1) == 2
    assert len(r2) == 1


def test_get_single_loan(client):
    token = register(client)
    loan_id = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token)).json()["id"]
    r = client.get(f"/loans/{loan_id}", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["id"] == loan_id


def test_cannot_view_another_users_loan(client):
    token1 = register(client, email="a@test.com", phone="+919000000011")
    token2 = register(client, email="b@test.com", phone="+919000000022")
    loan_id = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token1)).json()["id"]
    r = client.get(f"/loans/{loan_id}", headers=auth_headers(token2))
    assert r.status_code == 404


def test_apply_loan_invalid_ifsc(client):
    token = register(client)
    payload = {**LOAN_PAYLOAD, "ifsc_code": "INVALID"}
    r = client.post("/loans", json=payload, headers=auth_headers(token))
    assert r.status_code == 422

# ── Repayment payment tests ────────────────────────────────────────────────────

_admin_counter = 0

def _disburse_loan(client, loan_id):
    """Helper: admin approves + disburses a loan (loan must already be approved by rules engine)."""
    global _admin_counter
    _admin_counter += 1
    admin_token = register_admin(client, email=f"adm{_admin_counter}@test.com", phone=f"+9190000{90000 + _admin_counter}")
    client.post(
        f"/admin/loans/{loan_id}/disburse",
        json={"reference_number": f"TEST-REF-{_admin_counter:03d}"},
        headers=auth_headers(admin_token),
    )


def test_pay_installment_on_disbursed_loan(client):
    token = register(client)
    loan = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token)).json()
    accept_agreement(client, token, loan["id"])
    _disburse_loan(client, loan["id"])

    installments = client.get(f"/loans/{loan['id']}/repayments", headers=auth_headers(token)).json()
    first = installments[0]

    r = client.post(f"/loans/{loan['id']}/repayments/{first['id']}/pay",
        json={}, headers=auth_headers(token))
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "paid"
    assert data["paid_at"] is not None
    assert data["paid_amount"] == data["emi_amount"]


def test_pay_installment_already_paid(client):
    token = register(client)
    loan = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token)).json()
    accept_agreement(client, token, loan["id"])
    _disburse_loan(client, loan["id"])

    installments = client.get(f"/loans/{loan['id']}/repayments", headers=auth_headers(token)).json()
    first_id = installments[0]["id"]

    client.post(f"/loans/{loan['id']}/repayments/{first_id}/pay", json={}, headers=auth_headers(token))
    r = client.post(f"/loans/{loan['id']}/repayments/{first_id}/pay", json={}, headers=auth_headers(token))
    assert r.status_code == 400
    assert "already paid" in r.json()["detail"]


def test_pay_installment_on_approved_not_disbursed(client):
    token = register(client)
    loan = client.post("/loans", json=LOAN_PAYLOAD, headers=auth_headers(token)).json()

    installments = client.get(f"/loans/{loan['id']}/repayments", headers=auth_headers(token)).json()
    r = client.post(f"/loans/{loan['id']}/repayments/{installments[0]['id']}/pay",
        json={}, headers=auth_headers(token))
    assert r.status_code == 400
    assert "disbursed" in r.json()["detail"]


def test_loan_auto_closes_when_all_installments_paid(client):
    # Use 1-month tenure + small amount so rules engine auto-approves
    token = register(client)
    payload = {**LOAN_PAYLOAD, "tenure_months": 1, "amount": 20000}
    loan = client.post("/loans", json=payload, headers=auth_headers(token)).json()
    accept_agreement(client, token, loan["id"])
    _disburse_loan(client, loan["id"])

    installments = client.get(f"/loans/{loan['id']}/repayments", headers=auth_headers(token)).json()
    assert len(installments) == 1

    client.post(f"/loans/{loan['id']}/repayments/{installments[0]['id']}/pay",
        json={}, headers=auth_headers(token))

    loan_data = client.get(f"/loans/{loan['id']}", headers=auth_headers(token)).json()
    assert loan_data["status"] == "closed"
