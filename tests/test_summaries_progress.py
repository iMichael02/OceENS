"""Progression d'un sondage dans la file des synthèses (#148).

La file est la table `summaries` : `http_status` 0 = en attente, 200 = fait,
autre = échec. Le module répond seul à « où en est ce sondage ? ».
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from oceens.models import Summary
from oceens.summaries_progress import progress


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def add_summaries(session, survey_id, http_status, count):
    for _ in range(count):
        session.add(Summary(survey_id=survey_id, http_status=http_status))
    session.commit()


def test_estimate_counts_every_pending_job_of_every_survey(session):
    add_summaries(session, survey_id=1, http_status=200, count=1)
    add_summaries(session, survey_id=1, http_status=0, count=2)
    add_summaries(session, survey_id=2, http_status=0, count=3)

    result = progress(session, survey_id=1)

    assert (result.done, result.total, result.errors) == (1, 3, 0)
    # 5 jobs en attente dans toute la file (2 + 3), à 20 s chacun.
    assert result.estimated_seconds_left == 100
