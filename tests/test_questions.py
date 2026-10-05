import pytest

from catalog.models import Question


def mcq_payload(subject, topic, correct_index=0, option_count=4):
    options = []
    for index in range(option_count):
        options.append({"option_text": f"Option {index}", "is_correct": index == correct_index})
    return {
        "subject": subject.id,
        "topic": topic.id,
        "type": "MCQ",
        "text": "What is the stable sorting algorithm called?",
        "difficulty": "EASY",
        "marks": "2.00",
        "explanation": "Merge sort.",
        "options": options,
    }


@pytest.mark.django_db
def test_faculty_creates_mcq_with_one_correct_option(faculty_api, subject, topic):
    response = faculty_api.post("/api/questions/", mcq_payload(subject, topic), format="json")
    assert response.status_code == 201
    assert response.data["type"] == "MCQ"
    assert len(response.data["options"]) == 4
    assert sum(1 for option in response.data["options"] if option["is_correct"]) == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload["options"].pop(),
        lambda payload: payload["options"].append({"option_text": "Extra", "is_correct": False}),
        lambda payload: [option.update({"is_correct": False}) for option in payload["options"]],
        lambda payload: [option.update({"is_correct": True}) for option in payload["options"]],
    ],
)
def test_mcq_option_rules(faculty_api, subject, topic, mutate):
    payload = mcq_payload(subject, topic)
    mutate(payload)
    response = faculty_api.post("/api/questions/", payload, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_descriptive_rejects_options_and_student_cannot_write(faculty_api, student_api, subject, topic):
    descriptive = {
        "subject": subject.id,
        "topic": topic.id,
        "type": "DESCRIPTIVE",
        "text": "Explain merge sort in your own words.",
        "difficulty": "MEDIUM",
        "marks": "5.00",
    }
    created = faculty_api.post("/api/questions/", descriptive, format="json")
    assert created.status_code == 201
    assert created.data["options"] == []
    descriptive["options"] = [{"option_text": "A", "is_correct": True}]
    descriptive["text"] = "Explain heap sort in your own words."
    rejected = faculty_api.post("/api/questions/", descriptive, format="json")
    assert rejected.status_code == 400
    hidden = student_api.get("/api/questions/")
    assert hidden.status_code == 403


@pytest.mark.django_db
def test_topic_must_match_subject(faculty_api, subject, other_topic):
    payload = mcq_payload(subject, other_topic)
    response = faculty_api.post("/api/questions/", payload, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_deactivate_question(faculty_api, faculty, subject, topic):
    from tests.conftest import make_mcq

    question = make_mcq(faculty, subject, topic, text="Deactivate me please?")
    response = faculty_api.post(f"/api/questions/{question.id}/deactivate/")
    assert response.status_code == 200
    question.refresh_from_db()
    assert question.active is False
    assert Question.objects.get(pk=question.id).active is False


@pytest.mark.django_db
def test_question_bank_filters_by_topic_difficulty_and_search(faculty_api, faculty, subject, topic):
    from catalog.models import Topic
    from tests.conftest import make_descriptive, make_mcq

    graphs = Topic.objects.create(subject=subject, name="Graphs")
    easy_sort = make_mcq(faculty, subject, topic, text="Which sort is stable on linked lists?", difficulty="EASY")
    hard_sort = make_mcq(faculty, subject, topic, text="What is the worst-case of heap sort?", difficulty="HARD")
    graph_q = make_mcq(faculty, subject, graphs, text="Which traversal visits a graph breadth first?", difficulty="MEDIUM")
    make_descriptive(faculty, subject, topic, text="Explain merge sort stability.")

    by_topic = faculty_api.get(f"/api/questions/?topic={graphs.id}")
    assert by_topic.status_code == 200
    assert [row["id"] for row in by_topic.data] == [graph_q.id]

    by_difficulty = faculty_api.get("/api/questions/?difficulty=HARD")
    assert [row["id"] for row in by_difficulty.data] == [hard_sort.id]

    by_search = faculty_api.get("/api/questions/?q=linked%20lists")
    assert [row["id"] for row in by_search.data] == [easy_sort.id]

    combined = faculty_api.get(f"/api/questions/?topic={topic.id}&difficulty=EASY&q=stable")
    assert [row["id"] for row in combined.data] == [easy_sort.id]
