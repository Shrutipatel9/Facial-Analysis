import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.questionnaire_response import QuestionnaireResponse
from tests.integration.test_auth_flow import _register_and_verify

pytestmark = pytest.mark.asyncio


def _full_valid_answers(q4: str = "Masculine") -> dict:
    """A complete, valid answer set for all 23 questions (+ q19, since q4
    defaults to a value that shows it). Individual tests mutate/remove keys
    from this as needed."""
    answers = {
        "q1": "Entrepreneur",
        "q2": "Never",
        "q3": "Never",
        "q4": q4,
        "q5": "No",
        "q6": "No",
        "q7": ["Injectables (Botox, Dermal Fillers, Fat-Dissolving Injections)"],
        "q8": "No",
        "q9": "No",
        "q10": "No",
        "q11": "No",
        "q12": "No",
        "q13": "No",
        "q14": "My eye color",
        "q15": "Eyebrows",
        "q16": "Chris Brown",
        "q17": "Yes",
        "q18": "Refine and enhance my facial aesthetic",
        "q20": "No distress at all",
        "q21": "Rarely (a few times a week or less)",
        "q22": "Just curious",
        "q23": "",
    }
    if q4 in ("Masculine", "No Preference"):
        answers["q19"] = "Yes"
    return answers


async def _auth_headers(client: AsyncClient, email_sender, email: str) -> dict:
    tokens = await _register_and_verify(client, email_sender, email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


class TestGetQuestionnaire:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.get("/questionnaire")
        assert resp.status_code == 401

    async def test_returns_question_set_and_disclaimer(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "q-get@example.com")
        resp = await client.get("/questionnaire", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["questions"]) == 25  # 23 + q9_details + q11_details
        assert "Body Dysmorphic Disorder" in body["disclaimer_text"]
        q19 = next(q for q in body["questions"] if q["id"] == "q19")
        assert q19["show_if"] == {"question_id": "q4", "in_values": ["Masculine", "No Preference"]}


class TestQuestionnaireStatus:
    async def test_false_before_submit_true_after(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "q-status@example.com")

        resp = await client.get("/questionnaire/status", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"completed": False}

        resp = await client.post(
            "/questionnaire/responses",
            headers=headers,
            json={"answers": _full_valid_answers(), "disclaimer_accepted": True},
        )
        assert resp.status_code == 201, resp.text

        resp = await client.get("/questionnaire/status", headers=headers)
        assert resp.json() == {"completed": True}


class TestSubmitQuestionnaireResponse:
    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.post(
            "/questionnaire/responses", json={"answers": _full_valid_answers(), "disclaimer_accepted": True}
        )
        assert resp.status_code == 401

    async def test_full_valid_submission_succeeds(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "q-valid@example.com")
        resp = await client.post(
            "/questionnaire/responses",
            headers=headers,
            json={"answers": _full_valid_answers(), "disclaimer_accepted": True},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert "id" in body and "submitted_at" in body

    async def test_disclaimer_not_accepted_is_rejected(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "q-nodisclaimer@example.com")
        resp = await client.post(
            "/questionnaire/responses",
            headers=headers,
            json={"answers": _full_valid_answers(), "disclaimer_accepted": False},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "DISCLAIMER_NOT_ACCEPTED"

        async with async_session_factory() as session:
            result = await session.execute(select(QuestionnaireResponse))
            assert result.scalars().all() == []

    async def test_missing_required_answer_is_rejected(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "q-missing@example.com")
        answers = _full_valid_answers()
        del answers["q1"]
        resp = await client.post(
            "/questionnaire/responses", headers=headers, json={"answers": answers, "disclaimer_accepted": True}
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "QUESTIONNAIRE_ANSWERS_INVALID"
        assert any(d["question_id"] == "q1" for d in body["error"]["details"])

    async def test_unknown_question_key_is_rejected(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "q-unknown@example.com")
        answers = _full_valid_answers()
        answers["q99"] = "whatever"
        resp = await client.post(
            "/questionnaire/responses", headers=headers, json={"answers": answers, "disclaimer_accepted": True}
        )
        assert resp.status_code == 422
        assert any(d["question_id"] == "q99" for d in resp.json()["error"]["details"])

    async def test_multi_select_disallowed_option_is_rejected(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "q-badoption@example.com")
        answers = _full_valid_answers()
        answers["q7"] = ["Surgery (not a real option)"]
        resp = await client.post(
            "/questionnaire/responses", headers=headers, json={"answers": answers, "disclaimer_accepted": True}
        )
        assert resp.status_code == 422
        assert any(d["question_id"] == "q7" for d in resp.json()["error"]["details"])

    async def test_multi_select_sent_as_string_is_rejected(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "q-badtype@example.com")
        answers = _full_valid_answers()
        answers["q7"] = "Injectables (Botox, Dermal Fillers, Fat-Dissolving Injections)"
        resp = await client.post(
            "/questionnaire/responses", headers=headers, json={"answers": answers, "disclaimer_accepted": True}
        )
        assert resp.status_code == 422
        assert any(d["question_id"] == "q7" for d in resp.json()["error"]["details"])

    async def test_q19_kept_when_q4_masculine(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "q-q19-kept@example.com")
        resp = await client.post(
            "/questionnaire/responses",
            headers=headers,
            json={"answers": _full_valid_answers(q4="Masculine"), "disclaimer_accepted": True},
        )
        assert resp.status_code == 201, resp.text

        async with async_session_factory() as session:
            result = await session.execute(select(QuestionnaireResponse))
            record = result.scalar_one()
            assert record.answers["q19"] == "Yes"

    async def test_q19_stripped_not_rejected_when_q4_feminine(self, client: AsyncClient, email_sender):
        """q4=Feminine hides q19 -- if the client sends a stale q19 answer
        anyway (e.g. left over from before the user changed q4), the
        submission still succeeds but q19 must not be persisted."""
        headers = await _auth_headers(client, email_sender, "q-q19-stripped@example.com")
        answers = _full_valid_answers(q4="Feminine")
        answers["q19"] = "Yes"  # stale/irrelevant -- q4=Feminine hides q19
        resp = await client.post(
            "/questionnaire/responses", headers=headers, json={"answers": answers, "disclaimer_accepted": True}
        )
        assert resp.status_code == 201, resp.text

        async with async_session_factory() as session:
            result = await session.execute(select(QuestionnaireResponse))
            record = result.scalar_one()
            assert "q19" not in record.answers
            assert record.answers["q4"] == "Feminine"

    async def test_q9_details_stripped_not_rejected_when_q9_no(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "q-q9details-stripped@example.com")
        answers = _full_valid_answers()
        answers["q9"] = "No"
        answers["q9_details"] = "Ibuprofen"  # stale -- q9=No hides q9_details
        resp = await client.post(
            "/questionnaire/responses", headers=headers, json={"answers": answers, "disclaimer_accepted": True}
        )
        assert resp.status_code == 201, resp.text

        async with async_session_factory() as session:
            result = await session.execute(select(QuestionnaireResponse))
            record = result.scalar_one()
            assert "q9_details" not in record.answers

    async def test_q9_details_kept_when_q9_yes(self, client: AsyncClient, email_sender):
        headers = await _auth_headers(client, email_sender, "q-q9details-kept@example.com")
        answers = _full_valid_answers()
        answers["q9"] = "Yes"
        answers["q9_details"] = "Ibuprofen"
        resp = await client.post(
            "/questionnaire/responses", headers=headers, json={"answers": answers, "disclaimer_accepted": True}
        )
        assert resp.status_code == 201, resp.text

        async with async_session_factory() as session:
            result = await session.execute(select(QuestionnaireResponse))
            record = result.scalar_one()
            assert record.answers["q9_details"] == "Ibuprofen"
